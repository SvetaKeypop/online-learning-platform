from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from ....infrastructure.db import get_db
from ....infrastructure.models import Progress
from ..authz import get_user_email
from ..schemas import ProgressItem, CompleteResp

router = APIRouter(prefix="/api/progress", tags=["progress"])

@router.get("/health")
def health(): return {"status": "ok"}

@router.post("/{lesson_id}/complete", response_model=CompleteResp)
def complete_lesson(
    lesson_id: int,
    user_email: str = Depends(get_user_email),
    db: Session = Depends(get_db),
):
    # идемпотентный UPSERT: если запись уже есть — "ничего не делаем"
    stmt = insert(Progress).values(user_email=user_email, lesson_id=lesson_id)
    stmt = stmt.on_conflict_do_nothing(index_elements=["user_email", "lesson_id"])
    db.execute(stmt)
    db.commit()
    return CompleteResp(ok=True, lesson_id=lesson_id)

@router.get("/my", response_model=list[ProgressItem])
def my_progress(
    user_email: str = Depends(get_user_email),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    q = (select(Progress.lesson_id, Progress.completed_at)
         .where(Progress.user_email == user_email)
         .order_by(Progress.completed_at.desc())
         .limit(limit).offset(offset))
    rows = db.execute(q).all()
    return [ProgressItem(lesson_id=r[0], completed_at=r[1].isoformat()) for r in rows]
