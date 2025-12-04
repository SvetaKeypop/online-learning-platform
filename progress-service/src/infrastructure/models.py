from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, UniqueConstraint, TIMESTAMP, text, func
from datetime import datetime
from .db import Base

class Progress(Base):
    __tablename__ = "progress"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_email: Mapped[str] = mapped_column(String(255), index=True)  # берём из JWT sub
    lesson_id: Mapped[int] = mapped_column(Integer, index=True)
    completed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow
    )
    __table_args__ = (UniqueConstraint("user_email", "lesson_id", name="uq_user_lesson"),)
