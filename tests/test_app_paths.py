import sys

from memoryos.utils import app_paths


def test_is_frozen_false_when_running_from_source(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert app_paths.is_frozen() is False


def test_is_frozen_true_when_pyinstaller_flag_set(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert app_paths.is_frozen() is True


def test_get_resource_dir_from_source_is_project_root(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    resource_dir = app_paths.get_resource_dir()
    assert resource_dir == app_paths._PROJECT_ROOT
    assert (resource_dir / "memoryos").is_dir()


def test_get_resource_dir_when_frozen_is_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert app_paths.get_resource_dir() == tmp_path


def test_get_user_data_dir_from_source_is_dot_memoryos(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    data_dir = app_paths.get_user_data_dir()
    assert data_dir == app_paths._PROJECT_ROOT / ".memoryos"
    assert data_dir.is_dir()


def test_get_user_data_dir_when_frozen_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    fake_appdata = tmp_path / "AppData" / "Roaming"
    monkeypatch.setenv("APPDATA", str(fake_appdata))

    data_dir = app_paths.get_user_data_dir()

    assert data_dir == fake_appdata / "MemoryOS"
    assert data_dir.is_dir()
