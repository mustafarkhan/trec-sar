import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("hygiene", ROOT / "scripts" / "check_repo_hygiene.py")
hygiene = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hygiene)


def test_plain_message_passes():
    msg = "Fix link-recovery deadlock\n\n- MissionCore re-issues recovery goals\n"
    assert hygiene.check_message(msg) == []


def test_trailers_and_session_links_are_rejected():
    msg = (
        "Add feature\n\n"
        "Co-Authored-By: Someone <someone@example.com>\n"
        "Assistant-Session: https://example.com/code/session_abc123\n"
    )
    found = hygiene.check_message(msg)
    assert "co-author trailer" in found
    assert "session trailer" in found
    assert "link to a chat or session" in found


def test_git_comment_lines_are_ignored():
    assert hygiene.check_message("Fix typo\n# Co-authored-by: in a git comment\n") == []


def test_private_paths_are_rejected():
    paths = ["README.md", "private/plan.md", "docs/notes/todo.md", "docs/cv.private.md", "core/notes.py"]
    flagged = [p.split(":")[0] for p in hygiene.check_files(paths)]
    assert flagged == ["private/plan.md", "docs/notes/todo.md", "docs/cv.private.md"]


def test_tracked_files_are_clean():
    tracked = hygiene.git("ls-files").splitlines()
    assert hygiene.check_files(tracked) == []
