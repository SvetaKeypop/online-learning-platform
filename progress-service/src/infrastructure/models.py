from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, UniqueConstraint, TIMESTAMP, text
from .db import Base

class Progress(Base):
    __tablename__ = "progress"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_email: Mapped[str] = mapped_column(String(255), index=True)  # берём из JWT sub
    lesson_id: Mapped[int] = mapped_column(Integer, index=True)
    completed_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True),
                                              server_default=text("NOW()"))
    __table_args__ = (UniqueConstraint("user_email", "lesson_id", name="uq_user_lesson"),)
