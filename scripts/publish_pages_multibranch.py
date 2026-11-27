#!/usr/bin/env python3
"""
Multi-Branch Pages Publisher for Horizon Daily.
Pushes multi-branch weekly intelligence digests to gh-pages additively,
preserving historical posts and displaying active 7-day reports on:
https://jsonlord.github.io/Horizon/
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_cmd(cmd, cwd=None):
    res = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Command failed: {cmd}\nStdout: {res.stdout}\nStderr: {res.stderr}", file=sys.stderr)
        raise RuntimeError(f"Command failed with exit code {res.returncode}")
    return res.stdout.strip()


def publish():
    print("=== Publishing Multi-Branch Intelligence to gh-pages ===")
    
    # 1. Ensure latest gh-pages is fetched
    print("Fetching remote gh-pages branch...")
    run_cmd("git fetch origin gh-pages:refs/remotes/origin/gh-pages", cwd=ROOT)
    
    # 2. Create temporary directory for gh-pages worktree
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        print(f"Creating git worktree at {tmp_path}...")
        
        # Add worktree pointing to origin/gh-pages
        run_cmd(f"git worktree add -B gh-pages '{tmp_path}' origin/gh-pages", cwd=ROOT)
        
        try:
            # 3. Copy docs/_posts to tmp_path/_posts (additive!)
            posts_src = ROOT / "docs/_posts"
            posts_dest = tmp_path / "_posts"
            posts_dest.mkdir(parents=True, exist_ok=True)
            
            existing_posts = list(posts_dest.glob("*.md"))
            print(f"Existing posts in gh-pages: {len(existing_posts)}")
            
            new_posts = list(posts_src.glob("*.md"))
            print(f"Adding {len(new_posts)} new branch intelligence posts...")
            for post_file in new_posts:
                dest_file = posts_dest / post_file.name
                shutil.copy2(post_file, dest_file)
                print(f"  + Added: {post_file.name}")
            
            # 4. Copy updated index.md and docs files (excluding _posts which was handled additively)
            shutil.copy2(ROOT / "docs/index.md", tmp_path / "index.md")
            shutil.copy2(ROOT / "docs/_config.yml", tmp_path / "_config.yml")
            if (ROOT / "docs/_includes").exists():
                shutil.copytree(ROOT / "docs/_includes", tmp_path / "_includes", dirs_exist_ok=True)
            
            # 5. Check git status in worktree
            status = run_cmd("git status --porcelain", cwd=tmp_path)
            if not status:
                print("No changes to commit. gh-pages is already up to date.")
                return True
            
            print("Changes detected:\n" + status)
            
            # 6. Commit and Push
            run_cmd("git add -A", cwd=tmp_path)
            commit_msg = "feat(pages): update Horizon Daily with multi-branch weekly intelligence (funding, news, programs, research)"
            run_cmd(f'git commit -m "{commit_msg}"', cwd=tmp_path)
            print("Pushing to origin gh-pages...")
            push_out = run_cmd("git push origin gh-pages", cwd=tmp_path)
            print("Push output:\n" + push_out)
            print("Successfully published to gh-pages!")
            return True
            
        finally:
            print("Cleaning up git worktree...")
            subprocess.run(f"git worktree remove --force '{tmp_path}'", cwd=ROOT, shell=True)


if __name__ == "__main__":
    publish()
