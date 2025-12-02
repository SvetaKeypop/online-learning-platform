from fastapi import FastAPI
from sqlalchemy import text

from .infrastructure.db import engine, SessionLocal
from .infrastructure.models import Base, CourseORM, LessonORM
from .interfaces.http.routers import courses as courses_router

app = FastAPI(title="Courses Service", version="0.1.0")


#Демо-данные для автоматического заполнения БД
COURSES_DATA = [
    {
        "title": "Основы Python",
        "description": "Базовый курс по Python для тех, кто только начинает программировать.",
        "lessons": [
            {
                "title": "Установка Python и IDE",
                "content": "Устанавливаем Python, выбираем IDE (PyCharm, VS Code).",
            },
            {
                "title": "Первая программа",
                "content": "Пишем 'Hello, world!' и запускаем скрипт из терминала.",
            },
            {
                "title": "Переменные и типы данных",
                "content": "int, float, str, bool, list, tuple, dict.",
            },
        ],
    },
    {
        "title": "FastAPI для бэкенда",
        "description": "Создание REST API на FastAPI: роуты, схемы, работа с БД.",
        "lessons": [
            {
                "title": "Базовое приложение FastAPI",
                "content": "Создаём приложение, разбираем роуты и Swagger UI.",
            },
            {
                "title": "Модели и схемы",
                "content": "Pydantic-схемы, запросы и ответы.",
            },
            {
                "title": "Подключение к базе данных",
                "content": "Настраиваем SQLAlchemy и зависимость get_db.",
            },
        ],
    },
    {
        "title": "Git и GitHub для разработчика",
        "description": "Практический курс по Git и работе с GitHub.",
        "lessons": [
            {
                "title": "Базовые команды Git",
                "content": "git init, status, add, commit.",
            },
            {
                "title": "Удалённые репозитории",
                "content": "git remote, push, pull, работа с GitHub.",
            },
            {
                "title": "Ветки и pull-request’ы",
                "content": "git branch, merge, создание PR.",
            },
        ],
    },
]


def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        if db.query(CourseORM).first():
            return

        for course_spec in COURSES_DATA:
            course = CourseORM(
                title=course_spec["title"],
                description=course_spec["description"],
            )
            db.add(course)
            db.flush()

            for lesson_spec in course_spec["lessons"]:
                lesson = LessonORM(
                    course_id=course.id,
                    title=lesson_spec["title"],
                    content=lesson_spec["content"],
                )
                db.add(lesson)

        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    seed_demo_data()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(courses_router.router)
