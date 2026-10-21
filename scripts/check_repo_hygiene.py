#!/usr/bin/env python3
"""Repository hygiene checks: commit authorship, commit trailers and private files.

    python3 scripts/check_repo_hygiene.py --commits origin/main..HEAD   # commits in a range
    python3 scripts/check_repo_hygiene.py --message-file .git/COMMIT_EDITMSG  # commit-msg hook
    python3 scripts/check_repo_hygiene.py --files                       # tracked files

Rules
- With --check-authors (pushes to this repository and branches in it): commits are authored and committed by
  the maintainer, GitHub or GitHub Actions. Pull requests from forks skip this rule.
- Commit messages carry no co-author or session trailers and no links to chat sessions.
- Personal working notes never enter the repository: anything under private/ or notes/,
  or named *.private.*, is rejected even if it was force-added.

Exit code 0 when clean, 1 when a rule is broken (each finding is printed).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ALLOWED_IDENTITIES = {
    "mustafarkhan@users.noreply.github.com",  # maintainer
    "noreply@github.com",  # merges and web edits made by GitHub
    "41898282+github-actions[bot]@users.noreply.github.com",  # CI metric commits
}

# Trailers and links that must not appear in a commit message.
MESSAGE_RULES = [
    (re.compile(r"^co-authored-by:", re.I | re.M), "co-author trailer"),
    (re.compile(r"^[\w-]*session[\w-]*:", re.I | re.M), "session trailer"),
    (re.compile(r"https?://\S*/(?:chat|session)[_/]\S*", re.I), "link to a chat or session"),
    (re.compile(r"^generated (?:with|by)\b", re.I | re.M), "generated-by footer"),
]

PRIVATE_PATH = re.compile(r"(^|/)(private|notes)/|\.private\.[^/]+$", re.I)


def check_message(text: str) -> list[str]:
    body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))  # git comment lines
    return [why for rx, why in MESSAGE_RULES if rx.search(body)]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def check_commits(rev_range: str, check_authors: bool = False) -> list[str]:
    out = git("log", "--format=%H%x1f%ae%x1f%ce%x1f%B%x1e", rev_range)
    problems = []
    for rec in filter(None, (r.strip("\n") for r in out.split("\x1e"))):
        sha, author, committer, message = rec.split("\x1f", 3)
        short = sha[:8]
        for who, email in (("author", author), ("committer", committer)):
            if check_authors and email not in ALLOWED_IDENTITIES:
                problems.append(f"{short}: {who} <{email}> is not an allowed identity")
        problems += [f"{short}: commit message has a {why}" for why in check_message(message)]
    return problems


def check_files(paths: list[str]) -> list[str]:
    return [f"{p}: personal notes must not be committed" for p in paths if PRIVATE_PATH.search(p)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--commits", metavar="RANGE", help="git revision range, e.g. origin/main..HEAD")
    ap.add_argument("--message-file", type=Path, help="commit message file (commit-msg hook)")
    ap.add_argument("--check-authors", action="store_true", help="also require allowed author/committer identities")
    ap.add_argument("--files", action="store_true", help="check tracked file paths")
    a = ap.parse_args(argv)
    if not (a.commits or a.message_file or a.files):
        ap.error("nothing to check: pass --commits, --message-file and/or --files")

    problems: list[str] = []
    if a.message_file:
        problems += [f"commit message has a {why}" for why in check_message(a.message_file.read_text())]
    if a.commits:
        problems += check_commits(a.commits, a.check_authors)
    if a.files:
        problems += check_files(git("ls-files").splitlines())

    for p in problems:
        print(f"hygiene: {p}", file=sys.stderr)
    if not problems:
        print("hygiene: ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
