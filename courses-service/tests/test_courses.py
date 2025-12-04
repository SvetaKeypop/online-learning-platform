import os
import sys
import pytest
from unittest.mock import Mock, patch

CURRENT_DIR = os.path.dirname(__file__)
SERVICE_ROOT = os.path.dirname(CURRENT_DIR)
if SERVICE_ROOT not in sys.path:
    sys.path.insert(0, SERVICE_ROOT)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.main import app
from src.infrastructure.models import Base
from src.infrastructure.db import get_db

# Тестовая БД в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
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

def test_list_courses_empty(client):
    """Тест получения пустого списка курсов"""
    response = client.get("/api/courses")
    assert response.status_code == 200
    assert response.json() == []

def test_list_courses_with_pagination(client):
    """Тест пагинации курсов"""
    # Создаем тестовые данные через прямой доступ к БД
    from src.infrastructure.models import Course
    db = next(override_get_db())
    for i in range(15):
        course = Course(title=f"Course {i}", description=f"Description {i}")
        db.add(course)
    db.commit()
    db.close()
    
    # Тест первой страницы
    response = client.get("/api/courses?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 10
    
    # Тест второй страницы
    response = client.get("/api/courses?limit=10&offset=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5

def test_list_courses_invalid_pagination(client):
    """Тест невалидной пагинации"""
    response = client.get("/api/courses?limit=0")
    assert response.status_code == 422
    
    response = client.get("/api/courses?limit=101")
    assert response.status_code == 422
    
    response = client.get("/api/courses?offset=-1")
    assert response.status_code == 422

def test_get_course_lessons_not_found(client):
    """Тест получения уроков несуществующего курса"""
    response = client.get("/api/courses/999/lessons")
    assert response.status_code == 404

def test_get_course_lessons_empty(client, admin_token):
    """Тест получения пустого списка уроков"""
    # Создаем курс
    from src.infrastructure.models import Course
    db = next(override_get_db())
    course = Course(title="Test Course", description="Test Description")
    db.add(course)
    db.commit()
    course_id = course.id
    db.close()
    
    response = client.get(f"/api/courses/{course_id}/lessons")
    assert response.status_code == 200
    assert response.json() == []

def test_create_course_unauthorized(client):
    """Тест создания курса без авторизации"""
    response = client.post(
        "/api/courses",
        json={"title": "Test Course", "description": "Test Description"}
    )
    assert response.status_code == 401

@patch('src.interfaces.http.routers.courses.require_admin')
def test_create_course(mock_admin, client):
    """Тест создания курса"""
    mock_admin.return_value = {"sub": "admin@example.com", "role": "admin"}
    
    response = client.post(
        "/api/courses",
        json={"title": "Test Course", "description": "Test Description"},
        headers={"Authorization": "Bearer test"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Course"
    assert data["description"] == "Test Description"
    assert "id" in data

def test_update_course_not_found(client, admin_token):
    """Тест обновления несуществующего курса"""
    with patch('src.interfaces.http.routers.courses.require_admin') as mock_admin:
        mock_admin.return_value = {"sub": "admin@example.com", "role": "admin"}
        response = client.put(
            "/api/courses/999",
            json={"title": "Updated Title"},
            headers={"Authorization": admin_token}
        )
        assert response.status_code == 404

def test_delete_course_not_found(client, admin_token):
    """Тест удаления несуществующего курса"""
    with patch('src.interfaces.http.routers.courses.require_admin') as mock_admin:
        mock_admin.return_value = {"sub": "admin@example.com", "role": "admin"}
        response = client.delete(
            "/api/courses/999",
            headers={"Authorization": admin_token}
        )
        assert response.status_code == 404

def test_create_lesson_unauthorized(client):
    """Тест создания урока без авторизации"""
    response = client.post(
        "/api/courses/1/lessons",
        json={"title": "Test Lesson", "content": "Test Content", "order": 1}
    )
    assert response.status_code == 401

def test_metrics_endpoint(client):
    """Тест endpoint метрик"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text

