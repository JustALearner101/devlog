#!/usr/bin/env python
"""
Git post-commit hook entry-point.
Called by .git/hooks/post-commit with the repo root path as the first argument.

Usage (from the shell hook):
    python /path/to/dev-activity-logger/hooks/post_commit_hook.py /path/to/repo
"""

import sys
import os

# Allow importing project modules regardless of CWD
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from db.database import init_db
from collector.git_collector import log_commit


def main():
    if len(sys.argv) < 2:
        print("[devlog] Error: repo path argument missing.", file=sys.stderr)
        sys.exit(1)

    repo_path = sys.argv[1]

    # Ensure DB exists
    init_db()

    try:
        log_commit(repo_path)
        print(f"[devlog] Commit logged for repo: {repo_path}")
    except Exception as e:
        # Never fail the commit — just warn
        print(f"[devlog] Warning: could not log commit: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()

