"""Unit tests for db.py — the SQLModel persistence layer. Pure logic, no
Streamlit dependency: each test points the module at an isolated temp
SQLite file + image directory so nothing touches the real ./data folder."""

from __future__ import annotations

import pytest
from sqlmodel import create_engine

import db as db_module


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    """Redirect db.engine and db.IMAGE_DIR to a per-test temp location."""
    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "IMAGE_DIR", tmp_path / "images")
    monkeypatch.setattr(db_module, "DATA_DIR", tmp_path)
    db_module.create_db_and_tables()
    return test_engine


# ─────────────────────────────────────────────────────────────────
# get_or_create_project
# ─────────────────────────────────────────────────────────────────


def test_get_or_create_project_creates_new_project(isolated_db):
    project = db_module.get_or_create_project("MyProject.zip", {".py": 3})

    assert project.id is not None
    assert project.name == "MyProject.zip"
    assert project.file_summary_json == '{".py": 3}'


def test_get_or_create_project_reuses_existing_by_name(isolated_db):
    first = db_module.get_or_create_project("MyProject.zip", {".py": 3})
    second = db_module.get_or_create_project("MyProject.zip", {".py": 5})

    assert second.id == first.id
    assert second.file_summary_json == '{".py": 5}'  # refreshed on reload


def test_get_or_create_project_different_names_are_different_projects(isolated_db):
    first = db_module.get_or_create_project("ProjectA", {})
    second = db_module.get_or_create_project("ProjectB", {})

    assert first.id != second.id


# ─────────────────────────────────────────────────────────────────
# add_message / get_messages
# ─────────────────────────────────────────────────────────────────


def test_add_message_and_get_messages_round_trip(isolated_db):
    project = db_module.get_or_create_project("Proj", {})

    db_module.add_message(project.id, "user", "hello")
    db_module.add_message(project.id, "assistant", "hi there")

    messages = db_module.get_messages(project.id)

    assert [m.role for m in messages] == ["user", "assistant"]
    assert [m.content for m in messages] == ["hello", "hi there"]


def test_get_messages_are_ordered_by_creation(isolated_db):
    project = db_module.get_or_create_project("Proj", {})
    for i in range(5):
        db_module.add_message(project.id, "user", f"msg {i}")

    messages = db_module.get_messages(project.id)

    assert [m.content for m in messages] == [f"msg {i}" for i in range(5)]


def test_get_messages_isolated_per_project(isolated_db):
    project_a = db_module.get_or_create_project("ProjectA", {})
    project_b = db_module.get_or_create_project("ProjectB", {})

    db_module.add_message(project_a.id, "user", "for A")
    db_module.add_message(project_b.id, "user", "for B")

    assert [m.content for m in db_module.get_messages(project_a.id)] == ["for A"]
    assert [m.content for m in db_module.get_messages(project_b.id)] == ["for B"]


def test_get_messages_empty_for_unknown_project(isolated_db):
    assert db_module.get_messages(999) == []


# ─────────────────────────────────────────────────────────────────
# clear_messages
# ─────────────────────────────────────────────────────────────────


def test_clear_messages_deletes_rows(isolated_db):
    project = db_module.get_or_create_project("Proj", {})
    db_module.add_message(project.id, "user", "hello")

    db_module.clear_messages(project.id)

    assert db_module.get_messages(project.id) == []


def test_clear_messages_removes_on_disk_images(isolated_db):
    project = db_module.get_or_create_project("Proj", {})
    image_path = db_module.save_image(b"\x89PNG\r\n\x1a\n", project.id)
    db_module.add_message(project.id, "user", "see attached", image_path)

    assert db_module.Path(image_path).exists()

    db_module.clear_messages(project.id)

    assert not db_module.Path(image_path).exists()


def test_clear_messages_only_affects_its_own_project(isolated_db):
    project_a = db_module.get_or_create_project("ProjectA", {})
    project_b = db_module.get_or_create_project("ProjectB", {})
    db_module.add_message(project_a.id, "user", "for A")
    db_module.add_message(project_b.id, "user", "for B")

    db_module.clear_messages(project_a.id)

    assert db_module.get_messages(project_a.id) == []
    assert [m.content for m in db_module.get_messages(project_b.id)] == ["for B"]


# ─────────────────────────────────────────────────────────────────
# save_image
# ─────────────────────────────────────────────────────────────────


def test_save_image_writes_bytes_to_disk(isolated_db):
    image_bytes = b"\x89PNG\r\n\x1a\n"

    path = db_module.save_image(image_bytes, project_id=1)

    assert db_module.Path(path).read_bytes() == image_bytes


def test_save_image_normalizes_suffix_without_dot(isolated_db):
    path = db_module.save_image(b"data", project_id=1, suffix="jpg")

    assert path.endswith(".jpg")


def test_save_image_unique_per_call(isolated_db):
    path1 = db_module.save_image(b"data", project_id=1)
    path2 = db_module.save_image(b"data", project_id=1)

    assert path1 != path2
