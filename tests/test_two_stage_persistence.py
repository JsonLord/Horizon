"""Safeguards for writing held-out experiment outputs to the branch."""
import json
from pathlib import Path
import subprocess

import pytest

from scripts.persist_two_stage_experiment import (
    BRANCH, FILES, PersistenceError, attempt_dirname, commit_staged,
    push_with_retry, stage_and_commit, validate_origin_url, validate_outputs, validate_runtime_context,
    _push_failure,
)


def write_outputs(root: Path, run_id='123', attempt=1):
    folder = root / 'data/two-stage-experiment' / attempt_dirname(run_id, attempt)
    folder.mkdir(parents=True)
    (folder / 'experiment.json').write_text(json.dumps({
        'run_id': run_id, 'run_attempt': attempt, 'precision': None, 'recall': None,
    }))
    (folder / 'review-labels.json').write_text(json.dumps({
        'run_id': run_id, 'run_attempt': attempt, 'human_labels_available': False,
        'precision': None, 'recall': None, 'labels': [],
    }))
    (folder / 'candidate-evidence.json').write_text(json.dumps({
        'run_id': run_id, 'run_attempt': attempt, 'candidates': [],
    }))
    (folder / 'REPORT.md').write_text(f'# Held-out experiment\n\nRun ID: `{run_id}`. Attempt: `{attempt}`.\n')
    return folder


def runtime(run_id='123', attempt='1', *, repository='JsonLord/Horizon', ref=None, event_name='push',
            event_ref=None, fork=False):
    ref = ref or f'refs/heads/{BRANCH}'
    return ({'GITHUB_REPOSITORY': repository, 'GITHUB_EVENT_NAME': event_name,
             'GITHUB_REF': ref, 'GITHUB_RUN_ID': run_id, 'GITHUB_RUN_ATTEMPT': attempt},
            {'ref': event_ref or ref, 'repository': {'full_name': repository, 'fork': fork}})


def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, check=True, text=True, capture_output=True)


def init_repo(root):
    root.mkdir(parents=True, exist_ok=True)
    git(root, 'init', '-b', BRANCH)
    git(root, 'config', 'user.name', 'Local Test')
    git(root, 'config', 'user.email', 'test@example.invalid')
    (root / 'README.md').write_text('base\n')
    git(root, 'add', 'README.md')
    git(root, 'commit', '-m', 'initial')


def test_four_outputs_validate_with_matching_run_and_attempt(tmp_path):
    write_outputs(tmp_path, attempt=2)
    paths = validate_outputs(tmp_path, '123', 2)
    assert {p.name for p in paths} == set(FILES)
    assert all(p.stat().st_size > 0 for p in paths)


def test_only_approved_output_root_can_be_persisted(tmp_path):
    write_outputs(tmp_path)
    with pytest.raises(PersistenceError, match='data/two-stage-experiment'):
        validate_outputs(tmp_path, '123', 1, output_root=tmp_path / 'elsewhere')


def test_attempt_directories_are_unique_and_do_not_overwrite(tmp_path):
    first = write_outputs(tmp_path, attempt=1)
    second = write_outputs(tmp_path, attempt=2)
    assert first != second
    assert (first / 'experiment.json').exists() and (second / 'experiment.json').exists()
    with pytest.raises(PersistenceError, match='directory'):
        validate_outputs(tmp_path, '123', 3)


@pytest.mark.parametrize('name,content', [
    ('experiment.json', ''),
    ('review-labels.json', '{ malformed'),
])
def test_empty_or_malformed_outputs_fail_closed(tmp_path, name, content):
    folder = write_outputs(tmp_path)
    (folder / name).write_text(content)
    with pytest.raises(PersistenceError):
        validate_outputs(tmp_path, '123', 1)


def test_sensitive_values_stop_persistence_without_echoing_them(tmp_path):
    folder = write_outputs(tmp_path)
    secret = 'sk-test-secret-value-very-long-123456789'
    (folder / 'candidate-evidence.json').write_text(json.dumps({
        'run_id': '123', 'run_attempt': 1, 'candidates': [], 'leak': secret,
    }))
    with pytest.raises(PersistenceError, match='Sensitive value detected') as exc:
        validate_outputs(tmp_path, '123', 1, env={'HORIZON_DECISION_API_KEY': secret})
    assert secret not in str(exc.value)


def test_runtime_context_allows_only_exact_repo_push_branch_and_attempt():
    env, event = runtime()
    validate_runtime_context(env, event, '123', 1)
    bad_contexts = [
        runtime(repository='attacker/Horizon'),
        runtime(ref='refs/heads/main'),
        runtime(event_name='pull_request'),
        runtime(fork=True),
        runtime(event_ref='refs/heads/main'),
        runtime(attempt='2'),
    ]
    for env, event in bad_contexts:
        with pytest.raises(PersistenceError):
            validate_runtime_context(env, event, '123', 1)


def test_only_canonical_repository_origin_is_allowed():
    validate_origin_url('https://github.com/JsonLord/Horizon.git')
    validate_origin_url('git@github.com:JsonLord/Horizon.git')
    with pytest.raises(PersistenceError, match='Git origin'):
        validate_origin_url('https://attacker.invalid/JsonLord/Horizon.git')


def test_commit_stages_only_four_run_files_and_sets_bot_identity(tmp_path):
    init_repo(tmp_path)
    write_outputs(tmp_path)
    paths = validate_outputs(tmp_path, '123', 1)
    commit_sha = stage_and_commit(tmp_path, '123', 1, paths)
    assert commit_sha
    committed = set(git(tmp_path, 'show', '--format=', '--name-only', 'HEAD').stdout.splitlines())
    assert committed == {p.relative_to(tmp_path).as_posix() for p in paths}
    identity = git(tmp_path, 'show', '-s', '--format=%an <%ae>', 'HEAD').stdout.strip()
    assert identity == 'github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>'


def test_unrelated_files_are_never_committed(tmp_path):
    init_repo(tmp_path)
    write_outputs(tmp_path)
    (tmp_path / 'unrelated.txt').write_text('keep out\n')
    paths = validate_outputs(tmp_path, '123', 1)
    with pytest.raises(PersistenceError, match='unexpected or missing untracked'):
        stage_and_commit(tmp_path, '123', 1, paths)
    assert git(tmp_path, 'rev-parse', 'HEAD').stdout.strip() != ''


def test_no_op_commit_is_handled_without_creating_a_commit(tmp_path):
    init_repo(tmp_path)
    before = git(tmp_path, 'rev-parse', 'HEAD').stdout.strip()
    assert commit_staged(tmp_path, '123', 1, ('data/two-stage-experiment/123-attempt-1/experiment.json',)) is None
    assert git(tmp_path, 'rev-parse', 'HEAD').stdout.strip() == before


def test_push_failures_distinguish_protection_and_permissions():
    assert 'branch protection' in _push_failure(1, 'GH006: Protected branch update failed')
    assert 'contents:write' in _push_failure(128, 'remote: Write access to repository not granted')
    assert 'exit code 1' in _push_failure(1, 'network unavailable')


def test_non_fast_forward_push_rebases_safely_without_overwriting(tmp_path):
    bare = tmp_path / 'origin.git'
    subprocess.run(['git', 'init', '--bare', '-b', BRANCH, str(bare)], check=True, capture_output=True)
    work = tmp_path / 'work'
    init_repo(work)
    git(work, 'remote', 'add', 'origin', str(bare))
    git(work, 'push', '-u', 'origin', BRANCH)
    write_outputs(work)
    paths = validate_outputs(work, '123', 1)
    stage_and_commit(work, '123', 1, paths)

    other = tmp_path / 'other'
    subprocess.run(['git', 'clone', str(bare), str(other)], check=True, capture_output=True)
    git(other, 'config', 'user.name', 'Concurrent Writer')
    git(other, 'config', 'user.email', 'concurrent@example.invalid')
    (other / 'concurrent.txt').write_text('preserve this concurrent update\n')
    git(other, 'add', 'concurrent.txt')
    git(other, 'commit', '-m', 'concurrent branch update')
    git(other, 'push', 'origin', BRANCH)

    calls = []
    def fake_push(root, token):
        calls.append(True)
        return subprocess.run(['git', 'push', 'origin', f'HEAD:refs/heads/{BRANCH}'],
            cwd=root, check=False, text=True, capture_output=True)

    pushed_sha = push_with_retry(work, '', '123', 1, paths, push_fn=fake_push)
    assert len(calls) == 2
    git(other, 'fetch', 'origin', BRANCH)
    names = set(git(other, 'ls-tree', '-r', '--name-only', f'origin/{BRANCH}').stdout.splitlines())
    assert 'concurrent.txt' in names
    assert {p.relative_to(work).as_posix() for p in paths} <= names
    assert git(work, 'merge-base', '--is-ancestor', pushed_sha, f'origin/{BRANCH}').returncode == 0


def test_workflow_ignores_output_commits_and_has_narrow_write_job():
    workflow = Path('.github/workflows/two-stage-heldout-experiment.yml').read_text()
    assert 'paths-ignore:' in workflow and "'data/two-stage-experiment/**'" in workflow
    assert 'contents: write' in workflow
    assert 'cancel-in-progress: false' in workflow
    assert "github.event_name == 'push'" in workflow
    assert "github.repository == 'JsonLord/Horizon'" in workflow
    assert 'pull_request_target' not in workflow
    assert 'actions/download-artifact@v6' in workflow
    assert '${{ github.token }}' in workflow
