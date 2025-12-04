import os
import sys
import pytest
from unittest.mock import patch

CURRENT_DIR = os.path.dirname(__file__)
SERVICE_ROOT = os.path.dirname(CURRENT_DIR)
if SERVICE_ROOT not in sys.path:
    sys.path.insert(0, SERVICE_ROOT)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.models import Base, Course, Lesson
from src.infrastructure.db import get_db
from src.interfaces.http.authz import require_admin

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Переопределяем engine в infrastructure.db и main.py для тестов
import src.infrastructure.db
import src.main
src.infrastructure.db.engine = test_engine
src.main.engine = test_engine
src.infrastructure.db.SessionLocal = TestingSessionLocal

# Импортируем app после переопределения engine
from src.main import app

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def client():
    # Создаем таблицы перед каждым тестом
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield TestClient(app)
    # Очищаем после теста
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def admin_override():
    """Фикстура для переопределения require_admin"""
    def mock_require_admin():
        return {"sub": "admin@example.com", "role": "admin"}
    
    app.dependency_overrides[require_admin] = mock_require_admin
    yield
    if require_admin in app.dependency_overrides:
        del app.dependency_overrides[require_admin]

def test_full_course_lifecycle(client, admin_override):
    """Интеграционный тест полного жизненного цикла курса"""
    
    # 1. Создаем курс
    create_response = client.post(
        "/api/courses",
        json={"title": "Python Basics", "description": "Learn Python"},
        headers={"Authorization": "Bearer test"}
    )
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]
    
    # 2. Получаем список курсов
    list_response = client.get("/api/courses")
    assert list_response.status_code == 200
    courses = list_response.json()
    assert len(courses) >= 1
    assert any(c["id"] == course_id for c in courses)
    
    # 3. Создаем уроки
    lesson1_response = client.post(
        f"/api/courses/{course_id}/lessons",
        json={"title": "Introduction", "content": "Welcome to Python", "order": 1},
        headers={"Authorization": "Bearer test"}
    )
    assert lesson1_response.status_code == 201
    lesson1_id = lesson1_response.json()["id"]
    
    lesson2_response = client.post(
        f"/api/courses/{course_id}/lessons",
        json={"title": "Variables", "content": "Learn about variables", "order": 2},
        headers={"Authorization": "Bearer test"}
    )
    assert lesson2_response.status_code == 201
    
    # 4. Получаем уроки курса
    lessons_response = client.get(f"/api/courses/{course_id}/lessons")
    assert lessons_response.status_code == 200
    lessons = lessons_response.json()
    assert len(lessons) == 2
    assert lessons[0]["order"] == 1
    assert lessons[1]["order"] == 2
    
    # 5. Обновляем урок
    update_response = client.put(
        f"/api/courses/{course_id}/lessons/{lesson1_id}",
        json={"title": "Introduction Updated", "content": "Updated content"},
        headers={"Authorization": "Bearer test"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Introduction Updated"
    
    # 6. Обновляем курс
    update_course_response = client.put(
        f"/api/courses/{course_id}",
        json={"title": "Python Basics Updated"},
        headers={"Authorization": "Bearer test"}
    )
    assert update_course_response.status_code == 200
    assert update_course_response.json()["title"] == "Python Basics Updated"
    
    # 7. Удаляем урок
    delete_lesson_response = client.delete(
        f"/api/courses/{course_id}/lessons/{lesson1_id}",
        headers={"Authorization": "Bearer test"}
    )
    assert delete_lesson_response.status_code == 204
    
    # 8. Проверяем, что урок удален
    lessons_after_delete = client.get(f"/api/courses/{course_id}/lessons")
    assert len(lessons_after_delete.json()) == 1
    
    # 9. Удаляем курс
    delete_course_response = client.delete(
        f"/api/courses/{course_id}",
        headers={"Authorization": "Bearer test"}
    )
    assert delete_course_response.status_code == 204
    
    # 10. Проверяем, что курс удален
    final_list = client.get("/api/courses")
    assert not any(c["id"] == course_id for c in final_list.json())

def test_course_with_multiple_lessons(client, admin_override):
    """Тест курса с множеством уроков"""
    
    # Создаем курс
    course_response = client.post(
        "/api/courses",
        json={"title": "Advanced Course", "description": "Many lessons"},
        headers={"Authorization": "Bearer test"}
    )
    assert course_response.status_code == 201
    course_id = course_response.json()["id"]
    
    # Создаем 10 уроков
    lesson_ids = []
    for i in range(10):
        lesson_response = client.post(
            f"/api/courses/{course_id}/lessons",
            json={"title": f"Lesson {i+1}", "content": f"Content {i+1}", "order": i+1},
            headers={"Authorization": "Bearer test"}
        )
        assert lesson_response.status_code == 201
        lesson_ids.append(lesson_response.json()["id"])
    
    # Получаем все уроки
    lessons_response = client.get(f"/api/courses/{course_id}/lessons")
    assert lessons_response.status_code == 200
    lessons = lessons_response.json()
    assert len(lessons) == 10
    
    # Проверяем порядок
    for i, lesson in enumerate(lessons):
        assert lesson["order"] == i + 1

