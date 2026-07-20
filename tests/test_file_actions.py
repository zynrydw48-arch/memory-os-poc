import pytest

from memoryos import file_actions
from memoryos.file_actions import delete_file, is_valid_filename, rename_file


@pytest.mark.parametrize(
    "name,expected",
    [
        ("photo.jpg", True),
        ("my report 2024.pdf", True),
        ("קפה.jpg", True),
        ("", False),
        ("   ", False),
        ("a/b.jpg", False),
        ("a\\b.jpg", False),
        ("bad:name.jpg", False),
        ("bad?name.jpg", False),
        ("bad*name.jpg", False),
        ('bad"name.jpg', False),
        ("bad<name>.jpg", False),
        ("bad|name.jpg", False),
    ],
)
def test_is_valid_filename(name, expected):
    assert is_valid_filename(name) is expected


def test_rename_file_moves_real_file_on_disk(tmp_path):
    original = tmp_path / "original.txt"
    original.write_text("hello", encoding="utf-8")

    new_path = rename_file(original, "renamed.txt")

    assert new_path == tmp_path / "renamed.txt"
    assert new_path.exists()
    assert new_path.read_text(encoding="utf-8") == "hello"
    assert not original.exists()


def test_rename_file_rejects_invalid_name_without_touching_disk(tmp_path):
    original = tmp_path / "original.txt"
    original.write_text("hello", encoding="utf-8")

    with pytest.raises(ValueError):
        rename_file(original, "bad/name.txt")

    assert original.exists()  # untouched


def test_rename_file_does_not_overwrite_an_existing_different_file(tmp_path):
    original = tmp_path / "original.txt"
    original.write_text("hello", encoding="utf-8")
    other = tmp_path / "taken.txt"
    other.write_text("do not overwrite me", encoding="utf-8")

    with pytest.raises(FileExistsError):
        rename_file(original, "taken.txt")

    assert other.read_text(encoding="utf-8") == "do not overwrite me"
    assert original.exists()


def test_delete_file_calls_send2trash_not_a_real_permanent_delete(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(file_actions.send2trash, "send2trash", lambda p: calls.append(p))

    target = tmp_path / "to_delete.txt"
    target.write_text("bye", encoding="utf-8")

    delete_file(target)

    assert calls == [target]
    assert target.exists()  # the real file is untouched since send2trash was mocked
