from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from ....infrastructure.db import get_db
from ....infrastructure.models import Course, Lesson
from ..schemas import CourseOut, CourseCreate, CourseUpdate
from ..authz import require_admin

router = APIRouter(prefix="/api/courses", tags=["courses"])

@router.get("/health")
def health(): return {"status":"ok"}

@router.get("", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db),
                 limit: int = Query(10, ge=1, le=100),
                 offset: int = Query(0, ge=0)):
    rows = db.query(Course).order_by(Course.id).limit(limit).offset(offset).all()
    return rows

@router.get("/{course_id}/lessons", response_model=list)
def course_lessons(course_id: int, db: Session = Depends(get_db)):
    exists = db.query(Course.id).filter(Course.id==course_id).first()
    if not exists: raise HTTPException(404, "course not found")
    rows = db.query(Lesson).filter(Lesson.course_id==course_id).order_by(Lesson.order).all()
    return [{"id":l.id,"course_id":l.course_id,"title":l.title,"order":l.order} for l in rows]

# --- Admin-only CRUD:

@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_course(payload: CourseCreate, db: Session = Depends(get_db)):
    row = Course(title=payload.title, description=payload.description)
    db.add(row); db.commit(); db.refresh(row)
    return row

@router.put("/{course_id}", response_model=CourseOut, dependencies=[Depends(require_admin)])
def update_course(course_id: int, payload: CourseUpdate, db: Session = Depends(get_db)):
    row = db.query(Course).filter(Course.id==course_id).first()
    if not row: raise HTTPException(404, "course not found")
    if payload.title is not None: row.title = payload.title
    if payload.description is not None: row.description = payload.description
    db.commit(); db.refresh(row)
    return row

@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_course(course_id: int, db: Session = Depends(get_db)):
    row = db.query(Course).filter(Course.id==course_id).first()
    if not row: raise HTTPException(404, "course not found")
    db.delete(row); db.commit()
    return {"ok": True}
