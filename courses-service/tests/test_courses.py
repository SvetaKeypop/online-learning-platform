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
from src.infrastructure.models import Base
from src.infrastructure.db import get_db
from src.interfaces.http.authz import require_admin

# Тестовая БД в памяти
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

# Переопределяем on_startup чтобы использовать тестовый engine
@app.on_event("startup")
def test_on_startup():
    # Используем тестовый engine
    Base.metadata.create_all(bind=test_engine)

@pytest.fixture(scope="function")
def client():
    # Создаем таблицы перед каждым тестом на тестовом engine
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
    db = TestingSessionLocal()
    try:
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
    finally:
        db.close()

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

def test_get_course_lessons_empty(client):
    """Тест получения пустого списка уроков"""
    # Создаем курс
    from src.infrastructure.models import Course
    db = TestingSessionLocal()
    try:
        course = Course(title="Test Course", description="Test Description")
        db.add(course)
        db.commit()
        course_id = course.id
        db.close()
    except:
        db.close()
        raise
    
    response = client.get(f"/api/courses/{course_id}/lessons")
    assert response.status_code == 200
    assert response.json() == []

def test_create_course_unauthorized(client):
    """Тест создания курса без авторизации"""
    response = client.post(
        "/api/courses",
        json={"title": "Test Course", "description": "Test Description"}
    )
    # HTTPBearer возвращает 403 если нет заголовка Authorization
    assert response.status_code == 403

def test_create_course(client, admin_override):
    """Тест создания курса"""
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

def test_update_course_not_found(client, admin_override):
    """Тест обновления несуществующего курса"""
    response = client.put(
        "/api/courses/999",
        json={"title": "Updated Title"},
        headers={"Authorization": "Bearer test"}
    )
    assert response.status_code == 404

def test_delete_course_not_found(client, admin_override):
    """Тест удаления несуществующего курса"""
    response = client.delete(
        "/api/courses/999",
        headers={"Authorization": "Bearer test"}
    )
    assert response.status_code == 404

def test_create_lesson_unauthorized(client):
    """Тест создания урока без авторизации"""
    response = client.post(
        "/api/courses/1/lessons",
        json={"title": "Test Lesson", "content": "Test Content", "order": 1}
    )
    # HTTPBearer возвращает 403 если нет заголовка Authorization
    assert response.status_code == 403

def test_metrics_endpoint(client):
    """Тест endpoint метрик"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text

