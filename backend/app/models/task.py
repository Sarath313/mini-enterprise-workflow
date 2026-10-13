from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="todo",
    )

    priority: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="medium",
    )

    due_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    assigned_to: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    assignee = relationship(
        "User",
        foreign_keys=[assigned_to],
    )

    creator = relationship(
        "User",
        foreign_keys=[created_by],
    )


Index(
    "ix_tasks_assigned_recent",
    Task.assigned_to,
    Task.created_at.desc(),
    Task.id.desc(),
)
Index(
    "ix_tasks_created_by_recent",
    Task.created_by,
    Task.created_at.desc(),
    Task.id.desc(),
)
Index(
    "ix_tasks_created_recent",
    Task.created_at.desc(),
    Task.id.desc(),
)