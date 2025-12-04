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
from src.main import app
from src.infrastructure.models import Base, Course, Lesson
from src.infrastructure.db import get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_integration.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def admin_token():
    """Мок токена администратора"""
    return "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkBleGFtcGxlLmNvbSIsInJvbGUiOiJhZG1pbiJ9.test"

@patch('src.interfaces.http.routers.courses.require_admin')
def test_full_course_lifecycle(mock_admin, client, admin_token):
    """Интеграционный тест полного жизненного цикла курса"""
    mock_admin.return_value = {"sub": "admin@example.com", "role": "admin"}
    
    # 1. Создаем курс
    create_response = client.post(
        "/api/courses",
        json={"title": "Python Basics", "description": "Learn Python"},
        headers={"Authorization": admin_token}
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
        headers={"Authorization": admin_token}
    )
    assert lesson1_response.status_code == 201
    lesson1_id = lesson1_response.json()["id"]
    
    lesson2_response = client.post(
        f"/api/courses/{course_id}/lessons",
        json={"title": "Variables", "content": "Learn about variables", "order": 2},
        headers={"Authorization": admin_token}
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
        headers={"Authorization": admin_token}
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Introduction Updated"
    
    # 6. Обновляем курс
    update_course_response = client.put(
        f"/api/courses/{course_id}",
        json={"title": "Python Basics Updated"},
        headers={"Authorization": admin_token}
    )
    assert update_course_response.status_code == 200
    assert update_course_response.json()["title"] == "Python Basics Updated"
    
    # 7. Удаляем урок
    delete_lesson_response = client.delete(
        f"/api/courses/{course_id}/lessons/{lesson1_id}",
        headers={"Authorization": admin_token}
    )
    assert delete_lesson_response.status_code == 204
    
    # 8. Проверяем, что урок удален
    lessons_after_delete = client.get(f"/api/courses/{course_id}/lessons")
    assert len(lessons_after_delete.json()) == 1
    
    # 9. Удаляем курс
    delete_course_response = client.delete(
        f"/api/courses/{course_id}",
        headers={"Authorization": admin_token}
    )
    assert delete_course_response.status_code == 204
    
    # 10. Проверяем, что курс удален
    final_list = client.get("/api/courses")
    assert not any(c["id"] == course_id for c in final_list.json())

@patch('src.interfaces.http.routers.courses.require_admin')
def test_course_with_multiple_lessons(mock_admin, client, admin_token):
    """Тест курса с множеством уроков"""
    mock_admin.return_value = {"sub": "admin@example.com", "role": "admin"}
    
    # Создаем курс
    course_response = client.post(
        "/api/courses",
        json={"title": "Advanced Course", "description": "Many lessons"},
        headers={"Authorization": admin_token}
    )
    course_id = course_response.json()["id"]
    
    # Создаем 10 уроков
    lesson_ids = []
    for i in range(10):
        lesson_response = client.post(
            f"/api/courses/{course_id}/lessons",
            json={"title": f"Lesson {i+1}", "content": f"Content {i+1}", "order": i+1},
            headers={"Authorization": admin_token}
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

