import os
import sys
import pytest

CURRENT_DIR = os.path.dirname(__file__)
SERVICE_ROOT = os.path.dirname(CURRENT_DIR)
if SERVICE_ROOT not in sys.path:
    sys.path.insert(0, SERVICE_ROOT)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.models import Base
from src.infrastructure.db import get_db
from src.interfaces.http.authz import get_user_email

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

@pytest.fixture(scope="function")
def client():
    # Создаем таблицы перед каждым тестом на тестовом engine
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield TestClient(app)
    # Очищаем после теста
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def user_email_override():
    """Фикстура для переопределения get_user_email"""
    def mock_get_user_email():
        return "test@example.com"
    
    app.dependency_overrides[get_user_email] = mock_get_user_email
    yield
    if get_user_email in app.dependency_overrides:
        del app.dependency_overrides[get_user_email]

def test_complete_lesson_success(client, user_email_override):
    """Тест успешного завершения урока"""
    response = client.post(
        f"/api/progress/1/complete",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["lesson_id"] == 1

def test_complete_lesson_idempotent(client, user_email_override):
    """Тест идемпотентности завершения урока"""
    
    # Первое завершение
    response1 = client.post(
        f"/api/progress/1/complete",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response1.status_code == 200
    
    # Второе завершение (должно быть идемпотентным)
    response2 = client.post(
        f"/api/progress/1/complete",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response2.status_code == 200
    assert response1.json() == response2.json()

def test_complete_multiple_lessons(client, user_email_override):
    """Тест завершения нескольких уроков"""
    
    # Завершаем несколько уроков
    for lesson_id in [1, 2, 3]:
        response = client.post(
            f"/api/progress/{lesson_id}/complete",
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 200

def test_my_progress_empty(client, user_email_override):
    """Тест получения пустого прогресса"""
    
    response = client.get(
        "/api/progress/my",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_my_progress_with_completed(client, user_email_override):
    """Тест получения прогресса с завершенными уроками"""
    
    # Завершаем несколько уроков
    for lesson_id in [1, 2, 3]:
        client.post(
            f"/api/progress/{lesson_id}/complete",
            headers={"Authorization": "Bearer test_token"}
        )
    
    # Получаем прогресс
    response = client.get(
        "/api/progress/my",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3

def test_my_progress_pagination(client, user_email_override):
    """Тест пагинации прогресса"""
    
    # Завершаем много уроков
    for lesson_id in range(1, 15):
        client.post(
            f"/api/progress/{lesson_id}/complete",
            headers={"Authorization": "Bearer test_token"}
        )
    
    # Получаем первую страницу
    response = client.get(
        "/api/progress/my?limit=10&offset=0",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 10
    
    # Получаем вторую страницу
    response = client.get(
        "/api/progress/my?limit=10&offset=10",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 4

def test_complete_lesson_unauthorized(client):
    """Тест завершения урока без авторизации"""
    response = client.post("/api/progress/1/complete")
    assert response.status_code == 403

def test_my_progress_unauthorized(client):
    """Тест получения прогресса без авторизации"""
    response = client.get("/api/progress/my")
    assert response.status_code == 403

