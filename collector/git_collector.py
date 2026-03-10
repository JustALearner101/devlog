"""
Git collector — log commit events via GitPython.
Called from the post-commit hook or manually.
"""

import os
import shutil
import stat
import textwrap
from pathlib import Path

try:
    import git as gitpython
    _GIT_AVAILABLE = True
except ImportError:
    _GIT_AVAILABLE = False

from processor.event_processor import process_event


def log_commit(repo_path: str) -> None:
    """
    Read the latest commit from repo_path and persist it as an event.
    Requires GitPython to be installed.
    """
    if not _GIT_AVAILABLE:
        raise RuntimeError("gitpython is not installed. Run: pip install gitpython")

    repo = gitpython.Repo(repo_path, search_parent_directories=True)
    commit = repo.head.commit

    # Gather file stats
    stats = commit.stats
    files_changed = list(stats.files.keys())
    total_stats = stats.total

    metadata = {
        "repo": os.path.basename(repo.working_dir),
        "repo_path": repo.working_dir,
        "branch": repo.active_branch.name if not repo.head.is_detached else "HEAD",
        "message": commit.message.strip(),
        "commit_hash": commit.hexsha[:8],
        "files_changed": files_changed,
        "files_changed_count": len(files_changed),
        "lines_added": total_stats.get("insertions", 0),
        "lines_removed": total_stats.get("deletions", 0),
        "author": str(commit.author),
    }

    process_event("commit", "git", metadata)


def install_git_hook(repo_path: str) -> None:
    """
    Write a post-commit hook into repo_path/.git/hooks/post-commit
    that calls the devlog git collector.
    """
    repo = gitpython.Repo(repo_path, search_parent_directories=True) if _GIT_AVAILABLE else None
    git_dir = Path(repo.git_dir) if repo else Path(repo_path) / ".git"
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_file = hooks_dir / "post-commit"

    # Resolve path to our hook entry-point
    project_root = Path(__file__).parent.parent
    hook_script = project_root / "hooks" / "post_commit_hook.py"

    script_content = textwrap.dedent(f"""\
        #!/bin/sh
        # Dev Activity Logger — post-commit hook
        python "{hook_script}" "$(git rev-parse --show-toplevel)"
    """)

    hook_file.write_text(script_content, encoding="utf-8")

    # Make executable on Unix/macOS
    current_mode = hook_file.stat().st_mode
    hook_file.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"[devlog] Git hook installed at: {hook_file}")
