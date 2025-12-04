import os
import sys
import pytest
from unittest.mock import MagicMock, Mock
from datetime import datetime

CURRENT_DIR = os.path.dirname(__file__)
SERVICE_ROOT = os.path.dirname(CURRENT_DIR)
if SERVICE_ROOT not in sys.path:
    sys.path.insert(0, SERVICE_ROOT)

from fastapi.testclient import TestClient
from src.infrastructure.db import get_db
from src.interfaces.http.authz import get_user_email

# Импортируем app
from src.main import app

# Мокируем get_db
@pytest.fixture
def mock_db():
    """Мок сессии БД"""
    db = MagicMock()
    db.execute = MagicMock()
    db.commit = MagicMock()
    return db

def create_override_get_db(mock_db):
    """Создает функцию переопределения get_db для тестов"""
    def _get_db():
        yield mock_db
    return _get_db

@pytest.fixture
def user_email_override():
    """Фикстура для переопределения get_user_email"""
    def mock_get_user_email():
        return "test@example.com"
    
    app.dependency_overrides[get_user_email] = mock_get_user_email
    yield
    if get_user_email in app.dependency_overrides:
        del app.dependency_overrides[get_user_email]

@pytest.fixture
def client(mock_db):
    """Фикстура для тестового клиента"""
    # Переопределяем get_db для каждого теста
    app.dependency_overrides[get_db] = create_override_get_db(mock_db)
    yield TestClient(app)
    # Очищаем после теста
    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]

def test_complete_lesson_success(client, user_email_override, mock_db):
    """Тест успешного завершения урока"""
    # Мокируем execute и commit
    mock_db.execute.return_value = None
    mock_db.commit.return_value = None
    
    response = client.post(
        "/api/progress/1/complete",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["lesson_id"] == 1
    # Проверяем, что методы были вызваны
    assert mock_db.execute.called
    assert mock_db.commit.called

def test_complete_lesson_idempotent(client, user_email_override, mock_db):
    """Тест идемпотентности завершения урока"""
    mock_db.execute.return_value = None
    mock_db.commit.return_value = None
    
    # Первое завершение
    response1 = client.post(
        "/api/progress/1/complete",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response1.status_code == 200
    
    # Второе завершение (должно быть идемпотентным)
    response2 = client.post(
        "/api/progress/1/complete",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response2.status_code == 200
    assert response1.json() == response2.json()

def test_complete_multiple_lessons(client, user_email_override, mock_db):
    """Тест завершения нескольких уроков"""
    mock_db.execute.return_value = None
    mock_db.commit.return_value = None
    
    # Завершаем несколько уроков
    for lesson_id in [1, 2, 3]:
        response = client.post(
            f"/api/progress/{lesson_id}/complete",
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 200

def test_my_progress_empty(client, user_email_override, mock_db):
    """Тест получения пустого прогресса"""
    # Мокируем результат запроса - пустой список
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db.execute.return_value = mock_result
    
    response = client.get(
        "/api/progress/my",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_my_progress_with_completed(client, user_email_override, mock_db):
    """Тест получения прогресса с завершенными уроками"""
    # Мокируем результат запроса - 3 записи как кортежи (lesson_id, completed_at)
    mock_rows = [
        (3, datetime(2025, 12, 4, 23, 30, 0)),
        (2, datetime(2025, 12, 4, 23, 29, 0)),
        (1, datetime(2025, 12, 4, 23, 28, 0)),
    ]
    mock_result = MagicMock()
    mock_result.all.return_value = mock_rows
    mock_db.execute.return_value = mock_result
    
    response = client.get(
        "/api/progress/my",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3

def test_my_progress_pagination(client, user_email_override, mock_db):
    """Тест пагинации прогресса"""
    # Мокируем результат для первой страницы - 10 записей как кортежи
    mock_rows_page1 = [
        (i, datetime(2025, 12, 4, 23, 30 - i, 0))
        for i in range(14, 4, -1)
    ]
    mock_result_page1 = MagicMock()
    mock_result_page1.all.return_value = mock_rows_page1
    mock_db.execute.return_value = mock_result_page1
    
    response = client.get(
        "/api/progress/my?limit=10&offset=0",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 10
    
    # Мокируем результат для второй страницы - 4 записи как кортежи
    mock_rows_page2 = [
        (i, datetime(2025, 12, 4, 23, 30 - i, 0))
        for i in range(4, 0, -1)
    ]
    mock_result_page2 = MagicMock()
    mock_result_page2.all.return_value = mock_rows_page2
    mock_db.execute.return_value = mock_result_page2
    
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
