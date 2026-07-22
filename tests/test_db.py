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


@pytest.fixture()
def owner_id(isolated_db):
    """A ready-made owner for tests that only care about project/message
    behavior, not the identity of the owner itself."""
    return db_module.create_guest_user().id


# ─────────────────────────────────────────────────────────────────
# get_or_create_user / create_guest_user
# ─────────────────────────────────────────────────────────────────


def test_get_or_create_user_creates_new_user(isolated_db):
    user = db_module.get_or_create_user("alice@example.com", display_name="Alice")

    assert user.id is not None
    assert user.email == "alice@example.com"
    assert user.display_name == "Alice"
    assert user.is_guest is False


def test_get_or_create_user_reuses_existing_by_email(isolated_db):
    first = db_module.get_or_create_user("alice@example.com")
    second = db_module.get_or_create_user("alice@example.com")

    assert second.id == first.id


def test_create_guest_user_is_unique_each_call(isolated_db):
    guest1 = db_module.create_guest_user()
    guest2 = db_module.create_guest_user()

    assert guest1.id != guest2.id
    assert guest1.is_guest is True
    assert guest1.email is None


# ─────────────────────────────────────────────────────────────────
# get_or_create_project
# ─────────────────────────────────────────────────────────────────


def test_get_or_create_project_creates_new_project(owner_id):
    project = db_module.get_or_create_project(owner_id, "MyProject.zip", {".py": 3})

    assert project.id is not None
    assert project.owner_id == owner_id
    assert project.name == "MyProject.zip"
    assert project.file_summary_json == '{".py": 3}'


def test_get_or_create_project_reuses_existing_by_name(owner_id):
    first = db_module.get_or_create_project(owner_id, "MyProject.zip", {".py": 3})
    second = db_module.get_or_create_project(owner_id, "MyProject.zip", {".py": 5})

    assert second.id == first.id
    assert second.file_summary_json == '{".py": 5}'  # refreshed on reload


def test_get_or_create_project_different_names_are_different_projects(owner_id):
    first = db_module.get_or_create_project(owner_id, "ProjectA", {})
    second = db_module.get_or_create_project(owner_id, "ProjectB", {})

    assert first.id != second.id


def test_get_or_create_project_same_name_different_owners_do_not_collide(isolated_db):
    alice = db_module.get_or_create_user("alice@example.com")
    bob = db_module.get_or_create_user("bob@example.com")

    alice_project = db_module.get_or_create_project(alice.id, "SharedName", {})
    bob_project = db_module.get_or_create_project(bob.id, "SharedName", {})

    assert alice_project.id != bob_project.id


# ─────────────────────────────────────────────────────────────────
# add_message / get_messages
# ─────────────────────────────────────────────────────────────────


def test_add_message_and_get_messages_round_trip(owner_id):
    project = db_module.get_or_create_project(owner_id, "Proj", {})

    db_module.add_message(project.id, "user", "hello")
    db_module.add_message(project.id, "assistant", "hi there")

    messages = db_module.get_messages(project.id)

    assert [m.role for m in messages] == ["user", "assistant"]
    assert [m.content for m in messages] == ["hello", "hi there"]


def test_get_messages_are_ordered_by_creation(owner_id):
    project = db_module.get_or_create_project(owner_id, "Proj", {})
    for i in range(5):
        db_module.add_message(project.id, "user", f"msg {i}")

    messages = db_module.get_messages(project.id)

    assert [m.content for m in messages] == [f"msg {i}" for i in range(5)]


def test_get_messages_isolated_per_project(owner_id):
    project_a = db_module.get_or_create_project(owner_id, "ProjectA", {})
    project_b = db_module.get_or_create_project(owner_id, "ProjectB", {})

    db_module.add_message(project_a.id, "user", "for A")
    db_module.add_message(project_b.id, "user", "for B")

    assert [m.content for m in db_module.get_messages(project_a.id)] == ["for A"]
    assert [m.content for m in db_module.get_messages(project_b.id)] == ["for B"]


def test_get_messages_empty_for_unknown_project(isolated_db):
    assert db_module.get_messages(999) == []


# ─────────────────────────────────────────────────────────────────
# clear_messages
# ─────────────────────────────────────────────────────────────────


def test_clear_messages_deletes_rows(owner_id):
    project = db_module.get_or_create_project(owner_id, "Proj", {})
    db_module.add_message(project.id, "user", "hello")

    db_module.clear_messages(project.id)

    assert db_module.get_messages(project.id) == []


def test_clear_messages_removes_on_disk_images(owner_id):
    project = db_module.get_or_create_project(owner_id, "Proj", {})
    image_path = db_module.save_image(b"\x89PNG\r\n\x1a\n", project.id)
    db_module.add_message(project.id, "user", "see attached", image_path)

    assert db_module.Path(image_path).exists()

    db_module.clear_messages(project.id)

    assert not db_module.Path(image_path).exists()


def test_clear_messages_only_affects_its_own_project(owner_id):
    project_a = db_module.get_or_create_project(owner_id, "ProjectA", {})
    project_b = db_module.get_or_create_project(owner_id, "ProjectB", {})
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
