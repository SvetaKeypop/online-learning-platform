# src/infrastructure/models.py
from __future__ import annotations

from sqlalchemy import String, Text, ForeignKey, Integer
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class CourseORM(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    lessons: Mapped[list["LessonORM"]] = relationship(
        "LessonORM",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"CourseORM(id={self.id!r}, title={self.title!r})"


class LessonORM(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    course: Mapped["CourseORM"] = relationship(
        "CourseORM",
        back_populates="lessons",
    )

    def __repr__(self) -> str:
        return f"LessonORM(id={self.id!r}, course_id={self.course_id!r}, title={self.title!r})"

Course = CourseORM
Lesson = LessonORM

__all__ = [
    "Base",
    "CourseORM",
    "LessonORM",
    "Course",
    "Lesson",
]
