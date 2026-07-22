"""
db.py
─────
SQLModel-backed persistence layer for chat history and loaded projects.

SQLite locally by default (zero setup, single file). Swapping to Postgres
in production only means changing DATABASE_URL — every model/query below
is dialect-agnostic and needs no changes.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Field, Session, SQLModel, create_engine, select

DATA_DIR = Path(os.environ.get("SAP_CHAT_DATA_DIR", "data"))
IMAGE_DIR = DATA_DIR / "images"

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)


class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    loaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    file_summary_json: str = "{}"


class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    role: str
    content: str
    image_path: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def create_db_and_tables() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_or_create_project(name: str, file_summary: dict[str, int]) -> Project:
    """Reuse the most recent project row with this name — loading the same
    project again (including after a restart) resumes its history instead
    of starting a new, blank one."""
    summary_json = json.dumps(file_summary)
    with Session(engine) as session:
        existing = session.exec(
            select(Project).where(Project.name == name).order_by(Project.loaded_at.desc())
        ).first()
        if existing:
            existing.loaded_at = datetime.now(timezone.utc)
            existing.file_summary_json = summary_json
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

        project = Project(name=name, file_summary_json=summary_json)
        session.add(project)
        session.commit()
        session.refresh(project)
        return project


def add_message(project_id: int, role: str, content: str, image_path: str | None = None) -> Message:
    with Session(engine) as session:
        message = Message(project_id=project_id, role=role, content=content, image_path=image_path)
        session.add(message)
        session.commit()
        session.refresh(message)
        return message


def get_messages(project_id: int) -> list[Message]:
    with Session(engine) as session:
        return list(
            session.exec(
                select(Message).where(Message.project_id == project_id).order_by(Message.created_at)
            )
        )


def clear_messages(project_id: int) -> None:
    """Delete persisted messages for a project, including their on-disk images."""
    with Session(engine) as session:
        messages = session.exec(select(Message).where(Message.project_id == project_id)).all()
        for message in messages:
            if message.image_path:
                Path(message.image_path).unlink(missing_ok=True)
            session.delete(message)
        session.commit()


def save_image(image_bytes: bytes, project_id: int, suffix: str = ".png") -> str:
    """Persist an attached image to disk and return its path (stored on the
    Message row instead of the raw bytes)."""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    if not suffix.startswith("."):
        suffix = f".{suffix}"
    path = IMAGE_DIR / f"{project_id}_{uuid.uuid4().hex}{suffix}"
    path.write_bytes(image_bytes)
    return str(path)
