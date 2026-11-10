"""Validate and persist one experiment attempt to its approved branch."""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY = 'JsonLord/Horizon'
BRANCH = 'experiment/two-stage-heldout-2026-11-10'
REF = 'refs/heads/' + BRANCH
OUTPUT_ROOT = Path('data/two-stage-experiment')
FILES = ('experiment.json', 'REPORT.md', 'review-labels.json', 'candidate-evidence.json')
BOT_NAME = 'github-actions[bot]'
BOT_EMAIL = '41898282+github-actions[bot]@users.noreply.github.com'
MAX_FILE_BYTES = 10 * 1024 * 1024

SENSITIVE_ENV = re.compile(r'(?:API_KEY|ACCESS_TOKEN|GITHUB_TOKEN|GH_TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTHORIZATION)', re.I)
PROVIDER_ENDPOINT_ENV = {'HORIZON_DECISION_BASE_URL', 'HORIZON_DECISION_CHAT_URL'}
SENSITIVE_PATTERNS = (
    ('private_key', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
    ('github_token', re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b')),
    ('api_key', re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b')),
    ('bearer_token', re.compile(r'\bBearer\s+[A-Za-z0-9._~+/=-]{16,}', re.I)),
    ('url_credentials', re.compile(r'https?://[^\s/@:]+:[^\s/@]+@', re.I)),
)


class PersistenceError(RuntimeError):
    """Safe-to-report persistence failure; never embeds file content or tokens."""


def attempt_dirname(run_id: str, run_attempt: int) -> str:
    if not re.fullmatch(r'[0-9]{1,24}', str(run_id)):
        raise PersistenceError('Invalid workflow run ID')
    if type(run_attempt) is not int or run_attempt < 1:
        raise PersistenceError('Invalid workflow run attempt')
    return f'{run_id}-attempt-{run_attempt}'


def expected_paths(output_root: Path, run_id: str, run_attempt: int) -> tuple[Path, ...]:
    folder = output_root / attempt_dirname(run_id, run_attempt)
    return tuple(folder / filename for filename in FILES)


def _event_repository(event: dict) -> dict:
    repo = event.get('repository')
    if not isinstance(repo, dict):
        raise PersistenceError('Push event is missing repository metadata')
    return repo


def validate_runtime_context(env: dict[str, str], event: dict, run_id: str, run_attempt: int) -> None:
    if env.get('GITHUB_REPOSITORY') != REPOSITORY:
        raise PersistenceError('Refusing persistence outside JsonLord/Horizon')
    if env.get('GITHUB_EVENT_NAME') != 'push':
        raise PersistenceError('Refusing persistence for a non-push event')
    if env.get('GITHUB_REF') != REF or event.get('ref') != REF:
        raise PersistenceError('Refusing persistence outside the exact experiment branch')
    repo = _event_repository(event)
    owner = repo.get('owner')
    owner_name = owner.get('login') if isinstance(owner, dict) else None
    if repo.get('full_name') != REPOSITORY or owner_name != 'JsonLord':
        raise PersistenceError('Refusing persistence outside the owner-controlled JsonLord/Horizon repository')
    if str(env.get('GITHUB_RUN_ID', '')) != str(run_id):
        raise PersistenceError('Output run ID does not match the current workflow run')
    try:
        env_attempt = int(env.get('GITHUB_RUN_ATTEMPT', '0'))
    except ValueError as exc:
        raise PersistenceError('Invalid workflow run attempt in environment') from exc
    if env_attempt != run_attempt:
        raise PersistenceError('Output attempt does not match the current workflow attempt')


def load_event(env: dict[str, str]) -> dict:
    event_path = env.get('GITHUB_EVENT_PATH')
    if not event_path:
        raise PersistenceError('GitHub push event metadata is unavailable')
    try:
        return json.loads(Path(event_path).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise PersistenceError('GitHub push event metadata is invalid') from exc


def _sensitive_hit(text: str, env: dict[str, str]) -> str | None:
    for label, pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            return label
    for name, value in env.items():
        if not value or len(value) < 8:
            continue
        if SENSITIVE_ENV.search(name) or name in PROVIDER_ENDPOINT_ENV:
            if value in text:
                return 'configured_' + name.lower()
    return None


def _reject_json_constant(value: str):
    raise ValueError('Non-standard JSON constant: ' + value)


def validate_outputs(repo_root: Path, run_id: str, run_attempt: int, *, output_root: Path = OUTPUT_ROOT,
                     env: dict[str, str] | None = None) -> tuple[Path, ...]:
    repo_root = repo_root.resolve()
    output_root = (repo_root / output_root).resolve() if not output_root.is_absolute() else output_root.resolve()
    approved_root = (repo_root / OUTPUT_ROOT).resolve()
    if output_root != approved_root:
        raise PersistenceError('Experiment outputs must be persisted from data/two-stage-experiment')
    directory = (output_root / attempt_dirname(run_id, run_attempt)).resolve()
    if not directory.is_relative_to(output_root) or directory.is_symlink():
        raise PersistenceError('Experiment output directory escapes its approved path')
    if not directory.is_dir():
        raise PersistenceError('Expected experiment output directory is missing')
    found = {p.name for p in directory.iterdir() if p.is_file()}
    subdirs = [p for p in directory.iterdir() if p.is_dir()]
    expected = set(FILES)
    if found != expected or subdirs:
        raise PersistenceError('Experiment output directory must contain exactly the four required files')
    paths = expected_paths(output_root, run_id, run_attempt)
    text_by_name = {}
    json_by_name = {}
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise PersistenceError(f'Required output is missing or unsafe: {path.name}')
        size = path.stat().st_size
        if size <= 0 or size > MAX_FILE_BYTES:
            raise PersistenceError(f'Required output is empty or exceeds the size limit: {path.name}')
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError) as exc:
            raise PersistenceError(f'Output is not valid UTF-8: {path.name}') from exc
        text_by_name[path.name] = text
        if path.suffix == '.json':
            try:
                value = json.loads(text, parse_constant=_reject_json_constant)
            except (json.JSONDecodeError, ValueError) as exc:
                raise PersistenceError(f'Output JSON is malformed: {path.name}') from exc
            if not isinstance(value, dict):
                raise PersistenceError(f'Output JSON must be an object: {path.name}')
            json_by_name[path.name] = value
        hit = _sensitive_hit(text, env or {})
        if hit:
            raise PersistenceError(f'Sensitive value detected in {path.name} ({hit}); refusing to commit')
    for name, value in json_by_name.items():
        if str(value.get('run_id', '')) != str(run_id) or value.get('run_attempt') != run_attempt:
            raise PersistenceError(f'Output metadata does not match this run attempt: {name}')
    report = text_by_name['REPORT.md']
    if f'Run ID: `{run_id}`.' not in report or f'Attempt: `{run_attempt}`.' not in report:
        raise PersistenceError('Markdown report does not identify this run attempt')
    experiment = json_by_name['experiment.json']
    labels = json_by_name['review-labels.json']
    evidence = json_by_name['candidate-evidence.json']
    if experiment.get('precision') is not None or experiment.get('recall') is not None:
        raise PersistenceError('Unreviewed experiment cannot publish precision or recall')
    if labels.get('precision') is not None or labels.get('recall') is not None or labels.get('human_labels_available') is not False:
        raise PersistenceError('Human review labels must remain unlabelled')
    if not isinstance(labels.get('labels'), list) or not isinstance(evidence.get('candidates'), list):
        raise PersistenceError('Candidate evidence or review-label structure is invalid')
    label_ids = {row.get('candidate_id') for row in labels['labels'] if isinstance(row, dict)}
    evidence_ids = {row.get('candidate_id') for row in evidence['candidates'] if isinstance(row, dict)}
    if label_ids != evidence_ids:
        raise PersistenceError('Review labels do not cover exactly the saved candidate evidence')
    return paths


def _git(root: Path, *args: str, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    result = subprocess.run(['git', *args], cwd=root, text=True, capture_output=True, env=env)
    if check and result.returncode:
        raise PersistenceError(f'Git command failed ({args[0]}): {result.returncode}')
    return result


def validate_origin_url(url: str) -> None:
    allowed = {
        'https://github.com/JsonLord/Horizon',
        'https://github.com/JsonLord/Horizon.git',
        'git@github.com:JsonLord/Horizon.git',
    }
    if url.rstrip('/') not in allowed:
        raise PersistenceError('Git origin is not JsonLord/Horizon; refusing to push')


def assert_origin_repo(root: Path) -> None:
    url = _git(root, 'remote', 'get-url', 'origin').stdout.strip()
    validate_origin_url(url)


def assert_remote_output_path_not_present(root: Path, run_id: str, run_attempt: int) -> None:
    folder = OUTPUT_ROOT / attempt_dirname(run_id, run_attempt)
    result = _git(root, 'ls-tree', '-r', '--name-only', f'origin/{BRANCH}', '--', str(folder), check=False)
    if result.returncode != 0:
        raise PersistenceError('Could not inspect the current experiment branch')
    if result.stdout.strip():
        raise PersistenceError('This workflow attempt already has committed outputs; refusing to overwrite them')


def assert_output_path_not_present(root: Path, run_id: str, run_attempt: int) -> None:
    assert_remote_output_path_not_present(root, run_id, run_attempt)
    folder = OUTPUT_ROOT / attempt_dirname(run_id, run_attempt)
    directory = root / folder
    if directory.exists():
        raise PersistenceError('This workflow attempt output directory already exists; refusing to overwrite it')


def preflight(root: Path, run_id: str, run_attempt: int, *, env: dict[str, str] | None = None,
              event: dict | None = None) -> None:
    env = env or dict(os.environ)
    event = event or load_event(env)
    validate_runtime_context(env, event, run_id, run_attempt)
    branch = _git(root, 'branch', '--show-current').stdout.strip()
    if branch != BRANCH:
        raise PersistenceError('Checked-out branch is not the exact experiment branch')
    assert_origin_repo(root)
    _git(root, 'fetch', '--no-tags', 'origin', BRANCH)
    assert_output_path_not_present(root, run_id, run_attempt)


def stage_and_commit(root: Path, run_id: str, run_attempt: int, paths: tuple[Path, ...]) -> str | None:
    if _git(root, 'diff', '--quiet', check=False).returncode != 0 or _git(root, 'diff', '--cached', '--quiet', check=False).returncode != 0:
        raise PersistenceError('Worktree contains unrelated tracked changes; refusing to commit')
    relative = tuple(str(path.relative_to(root)) for path in paths)
    untracked = set(_git(root, 'ls-files', '--others', '--exclude-standard').stdout.splitlines())
    if untracked != set(relative):
        raise PersistenceError('Worktree contains unexpected or missing untracked files')
    _git(root, 'add', '--', *relative)
    return commit_staged(root, run_id, run_attempt, relative)


def commit_staged(root: Path, run_id: str, run_attempt: int, relative: tuple[str, ...]) -> str | None:
    staged = set(_git(root, 'diff', '--cached', '--name-only').stdout.splitlines())
    if not staged:
        return None
    if staged != set(relative):
        raise PersistenceError('Staged files exceed the four approved experiment outputs')
    _git(root, '-c', f'user.name={BOT_NAME}', '-c', f'user.email={BOT_EMAIL}',
         'commit', '-m', f'chore(experiment): save held-out results for run {run_id} attempt {run_attempt}')
    committed = set(_git(root, 'show', '--format=', '--name-only', 'HEAD').stdout.splitlines())
    if committed != set(relative):
        raise PersistenceError('Created commit contains unexpected paths')
    return _git(root, 'rev-parse', 'HEAD').stdout.strip()


def _push(root: Path, token: str) -> subprocess.CompletedProcess:
    if not token:
        raise PersistenceError('GITHUB_TOKEN is unavailable for the authorized branch push')
    auth = base64.b64encode(('x-access-token:' + token).encode()).decode()
    return _git(root, '-c', f'http.https://github.com/.extraheader=AUTHORIZATION: basic {auth}',
                'push', 'origin', f'HEAD:{REF}', check=False)


def _push_failure(exit_code: int, stderr: str) -> str:
    message = stderr.lower()
    if 'protected branch' in message or 'hook declined' in message or 'branch protection' in message:
        return 'GitHub branch protection rejected the output commit'
    if 'permission denied' in message or 'write access' in message or 'authentication failed' in message or '403' in message:
        return 'GitHub rejected the token or its contents:write permission'
    return f'GitHub push failed with exit code {exit_code}'


def push_with_retry(root: Path, token: str, run_id: str, run_attempt: int,
                    paths: tuple[Path, ...], *, push_fn=None) -> str:
    push_fn = push_fn or _push
    for attempt in range(3):
        pushed = push_fn(root, token)
        if pushed.returncode == 0:
            return _git(root, 'rev-parse', 'HEAD').stdout.strip()
        message = pushed.stderr[:1000]
        non_fast_forward = any(marker in message.lower() for marker in (
            'non-fast-forward', 'fetch first', 'failed to push some refs'))
        if not non_fast_forward:
            raise PersistenceError(_push_failure(pushed.returncode, message))
        if attempt == 2:
            raise PersistenceError('GitHub push remained non-fast-forward after three safe attempts')
        _git(root, 'fetch', '--no-tags', 'origin', BRANCH)
        assert_remote_output_path_not_present(root, run_id, run_attempt)
        rebased = _git(root, 'rebase', f'origin/{BRANCH}', check=False)
        if rebased.returncode:
            _git(root, 'rebase', '--abort', check=False)
            raise PersistenceError('Could not safely rebase the output commit onto the latest experiment branch')
        expected = {path.relative_to(root).as_posix() for path in paths}
        committed = set(_git(root, 'show', '--format=', '--name-only', 'HEAD').stdout.splitlines())
        if committed != expected:
            raise PersistenceError('Rebased output commit contains unexpected paths')
    raise PersistenceError('Push retry limit exhausted')


def _verify_contents_api(token: str, commit_sha: str, paths: tuple[Path, ...], root: Path) -> None:
    for path in paths:
        relative = path.relative_to(root).as_posix()
        query = urllib.parse.urlencode({'ref': commit_sha})
        url = f'https://api.github.com/repos/{REPOSITORY}/contents/{urllib.parse.quote(relative)}?{query}'
        request = urllib.request.Request(url, headers={
            'Accept': 'application/vnd.github+json', 'Authorization': f'Bearer {token}',
            'X-GitHub-Api-Version': '2022-11-28',
        })
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                metadata = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise PersistenceError(f'GitHub Contents API could not verify {path.name}') from exc
        if metadata.get('path') != relative or not isinstance(metadata.get('sha'), str):
            raise PersistenceError(f'GitHub Contents API returned unexpected metadata for {path.name}')
        if metadata.get('size') != path.stat().st_size:
            raise PersistenceError(f'GitHub Contents API size did not match {path.name}')
        encoded = metadata.get('content')
        if metadata.get('encoding') != 'base64' or not isinstance(encoded, str):
            raise PersistenceError(f'GitHub Contents API did not return file content for {path.name}')
        try:
            remote_bytes = base64.b64decode(encoded, validate=False)
        except ValueError as exc:
            raise PersistenceError(f'GitHub Contents API returned invalid content for {path.name}') from exc
        if remote_bytes != path.read_bytes():
            raise PersistenceError(f'GitHub Contents API content did not match {path.name}')


def persist(root: Path, run_id: str, run_attempt: int, *, env: dict[str, str] | None = None,
            event: dict | None = None, output_root: Path = OUTPUT_ROOT) -> dict:
    env = env or dict(os.environ)
    event = event or load_event(env)
    validate_runtime_context(env, event, run_id, run_attempt)
    if _git(root, 'branch', '--show-current').stdout.strip() != BRANCH:
        raise PersistenceError('Checked-out branch is not the exact experiment branch')
    assert_origin_repo(root)
    paths = validate_outputs(root, run_id, run_attempt, output_root=output_root, env=env)
    _git(root, 'fetch', '--no-tags', 'origin', BRANCH)
    remote_ref = f'origin/{BRANCH}'
    assert_remote_output_path_not_present(root, run_id, run_attempt)
    remote_sha = _git(root, 'rev-parse', remote_ref).stdout.strip()
    local_sha = _git(root, 'rev-parse', 'HEAD').stdout.strip()
    if local_sha != remote_sha:
        ancestor = _git(root, 'merge-base', '--is-ancestor', local_sha, remote_sha, check=False)
        if ancestor.returncode:
            raise PersistenceError('Local branch is not safely behind the experiment branch')
        _git(root, 'merge', '--ff-only', remote_ref)
    commit_sha = stage_and_commit(root, run_id, run_attempt, paths)
    if commit_sha is None:
        raise PersistenceError('No-op commit: the four new attempt outputs were not staged; refusing to report persistence success')
    token = env.get('GH_TOKEN') or env.get('GITHUB_TOKEN', '')
    commit_sha = push_with_retry(root, token, run_id, run_attempt, paths)
    _git(root, 'fetch', '--no-tags', 'origin', BRANCH)
    latest_sha = _git(root, 'rev-parse', f'origin/{BRANCH}').stdout.strip()
    is_ancestor = _git(root, 'merge-base', '--is-ancestor', commit_sha, latest_sha, check=False)
    if is_ancestor.returncode:
        raise PersistenceError('Push returned success but the output commit is not on the remote branch')
    _verify_contents_api(token, commit_sha, paths, root)
    return {'status': 'pushed', 'commit_sha': commit_sha, 'branch_tip_sha': latest_sha,
            'files': [p.relative_to(root).as_posix() for p in paths]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'validate', 'persist'))
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--run-attempt', type=int, required=True)
    parser.add_argument('--repo-root', type=Path, default=Path.cwd())
    parser.add_argument('--output-root', type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    try:
        root = args.repo_root.resolve()
        if args.action == 'preflight':
            preflight(root, args.run_id, args.run_attempt)
            print('Persistence preflight passed for exact experiment branch and attempt.')
        elif args.action == 'validate':
            paths = validate_outputs(root, args.run_id, args.run_attempt, output_root=args.output_root, env=dict(os.environ))
            print(f'Validated all four outputs for run {args.run_id}, attempt {args.run_attempt}.')
        else:
            result = persist(root, args.run_id, args.run_attempt, output_root=args.output_root)
            print(json.dumps(result, sort_keys=True))
        return 0
    except PersistenceError as exc:
        print(f'Experiment output persistence failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
