from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from ....infrastructure.db import get_db
from ....infrastructure.models import Course, Lesson
from ....infrastructure.cache import get_cache, set_cache, delete_cache_pattern
from ....infrastructure.metrics import cache_hits_total, cache_misses_total, db_queries_total
from ..schemas import CourseOut, CourseCreate, CourseUpdate, LessonCreate, LessonUpdate, LessonOut
from ..authz import require_admin

router = APIRouter(prefix="/api/courses", tags=["courses"])

@router.get("/health")
def health(): return {"status":"ok"}

@router.get("", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db),
                 limit: int = Query(10, ge=1, le=100),
                 offset: int = Query(0, ge=0)):
    # Кэширование списка курсов
    cache_key = f"courses:list:{limit}:{offset}"
    cached = get_cache(cache_key)
    if cached:
        cache_hits_total.inc()
        return cached
    
    cache_misses_total.inc()
    db_queries_total.inc()
    rows = db.query(Course).order_by(Course.id).limit(limit).offset(offset).all()
    result = [CourseOut.model_validate(row) for row in rows]
    set_cache(cache_key, [r.model_dump() for r in result])
    return result

@router.get("/{course_id}/lessons", response_model=list[LessonOut])
def course_lessons(course_id: int, db: Session = Depends(get_db)):
    # Кэширование уроков курса
    cache_key = f"course:{course_id}:lessons"
    cached = get_cache(cache_key)
    if cached:
        cache_hits_total.inc()
        return cached
    
    cache_misses_total.inc()
    db_queries_total.inc()
    exists = db.query(Course.id).filter(Course.id==course_id).first()
    if not exists: raise HTTPException(404, "course not found")
    rows = db.query(Lesson).filter(Lesson.course_id==course_id).order_by(Lesson.order).all()
    result = [LessonOut.model_validate(row) for row in rows]
    set_cache(cache_key, [r.model_dump() for r in result])
    return result

# --- Admin-only CRUD:

@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_course(payload: CourseCreate, db: Session = Depends(get_db)):
    row = Course(title=payload.title, description=payload.description)
    db.add(row); db.commit(); db.refresh(row)
    # Инвалидируем кэш списка курсов
    delete_cache_pattern("courses:list:*")
    return row

@router.put("/{course_id}", response_model=CourseOut, dependencies=[Depends(require_admin)])
def update_course(course_id: int, payload: CourseUpdate, db: Session = Depends(get_db)):
    row = db.query(Course).filter(Course.id==course_id).first()
    if not row: raise HTTPException(404, "course not found")
    if payload.title is not None: row.title = payload.title
    if payload.description is not None: row.description = payload.description
    db.commit(); db.refresh(row)
    # Инвалидируем кэш
    delete_cache_pattern("courses:list:*")
    delete_cache_pattern(f"course:{course_id}:*")
    return row

@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_course(course_id: int, db: Session = Depends(get_db)):
    row = db.query(Course).filter(Course.id==course_id).first()
    if not row: raise HTTPException(404, "course not found")
    db.delete(row); db.commit()
    # Инвалидируем кэш
    delete_cache_pattern("courses:list:*")
    delete_cache_pattern(f"course:{course_id}:*")
    return {"ok": True}

# --- Lesson CRUD:

@router.post("/{course_id}/lessons", response_model=LessonOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_lesson(course_id: int, payload: LessonCreate, db: Session = Depends(get_db)):
    exists = db.query(Course.id).filter(Course.id==course_id).first()
    if not exists: raise HTTPException(404, "course not found")
    row = Lesson(course_id=course_id, title=payload.title, content=payload.content, order=payload.order)
    db.add(row); db.commit(); db.refresh(row)
    # Инвалидируем кэш уроков курса
    delete_cache_pattern(f"course:{course_id}:lessons")
    return row

@router.put("/{course_id}/lessons/{lesson_id}", response_model=LessonOut, dependencies=[Depends(require_admin)])
def update_lesson(course_id: int, lesson_id: int, payload: LessonUpdate, db: Session = Depends(get_db)):
    row = db.query(Lesson).filter(Lesson.id==lesson_id, Lesson.course_id==course_id).first()
    if not row: raise HTTPException(404, "lesson not found")
    if payload.title is not None: row.title = payload.title
    if payload.content is not None: row.content = payload.content
    if payload.order is not None: row.order = payload.order
    db.commit(); db.refresh(row)
    # Инвалидируем кэш уроков курса
    delete_cache_pattern(f"course:{course_id}:lessons")
    return row

@router.delete("/{course_id}/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_lesson(course_id: int, lesson_id: int, db: Session = Depends(get_db)):
    row = db.query(Lesson).filter(Lesson.id==lesson_id, Lesson.course_id==course_id).first()
    if not row: raise HTTPException(404, "lesson not found")
    db.delete(row); db.commit()
    # Инвалидируем кэш уроков курса
    delete_cache_pattern(f"course:{course_id}:lessons")
    return {"ok": True}
