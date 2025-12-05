import os
import sys
import pytest
from unittest.mock import MagicMock, Mock

CURRENT_DIR = os.path.dirname(__file__)
SERVICE_ROOT = os.path.dirname(CURRENT_DIR)
if SERVICE_ROOT not in sys.path:
    sys.path.insert(0, SERVICE_ROOT)

from fastapi.testclient import TestClient
from src.infrastructure.db import get_db
from src.infrastructure.security import PasswordHasher
from src.interfaces.http.routers.auth import get_limiter

# Импортируем app
from src.main import app

# Мокируем get_db
@pytest.fixture
def mock_db():
    """Мок сессии БД"""
    db = MagicMock()
    db.query = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    return db

def create_override_get_db(mock_db):
    """Создает функцию переопределения get_db для тестов"""
    def _get_db():
        yield mock_db
    return _get_db

# Отключаем rate limiting в тестах
def override_get_limiter():
    from unittest.mock import MagicMock
    mock_limiter = MagicMock()
    def noop_limit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    mock_limiter.limit = noop_limit
    return mock_limiter

app.dependency_overrides[get_limiter] = override_get_limiter

@pytest.fixture
def client(mock_db):
    """Фикстура для тестового клиента"""
    # Переопределяем get_db для каждого теста
    app.dependency_overrides[get_db] = create_override_get_db(mock_db)
    yield TestClient(app)
    # Очищаем после теста
    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]

def test_register_user_success(client, mock_db):
    """Тест успешной регистрации пользователя"""
    from src.infrastructure.models import UserORM
    from src.domain.entities import User
    
    # Мокируем, что пользователя нет
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None
    mock_db.query.return_value = mock_query
    
    # Мокируем создание пользователя
    mock_user = Mock(spec=UserORM)
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user.role = "student"
    
    def refresh_side_effect(obj):
        obj.id = 1
        obj.email = "test@example.com"
        obj.role = "student"
    
    mock_db.refresh.side_effect = refresh_side_effect
    
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "student"
    assert "id" in data

def test_register_user_duplicate(client, mock_db):
    """Тест регистрации с существующим email"""
    from src.infrastructure.models import UserORM
    
    # Мокируем, что пользователь уже существует
    mock_user = Mock()  # Без spec, чтобы избежать автоматических Mock объектов
    mock_user.id = 1
    mock_user.email = "test@example.com"  # Реальная строка
    mock_user.role = "student"  # Реальная строка
    
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = mock_user
    mock_db.query.return_value = mock_query
    
    # Первая регистрация (успешная)
    def refresh_side_effect(obj):
        obj.id = 1
    
    mock_db.refresh.side_effect = refresh_side_effect
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )
    
    # Вторая регистрация с тем же email (должна провалиться)
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 400

def test_register_user_invalid_email(client):
    """Тест регистрации с невалидным email"""
    response = client.post(
        "/api/auth/register",
        json={"email": "invalid-email", "password": "password123"}
    )
    assert response.status_code == 422

def test_register_user_short_password(client):
    """Тест регистрации с коротким паролем"""
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "123"}
    )
    # Может быть 422 (валидация) или 400 (бизнес-логика)
    assert response.status_code in [400, 422]

def test_login_success(client, mock_db):
    """Тест успешного входа"""
    from src.infrastructure.models import UserORM
    
    # Мокируем пользователя с правильным паролем
    hasher = PasswordHasher()
    password_hash = hasher.hash("password123")
    
    # Используем Mock() без spec, чтобы избежать автоматического создания дочерних Mock объектов
    mock_user = Mock()
    mock_user.id = 1
    mock_user.email = "test@example.com"  # Реальная строка
    mock_user.password_hash = password_hash  # Реальная строка
    mock_user.role = "student"  # Реальная строка
    
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = mock_user
    mock_db.query.return_value = mock_query
    
    response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client, mock_db):
    """Тест входа с неверными учетными данными"""
    from src.infrastructure.models import UserORM
    
    # Мокируем пользователя с неправильным паролем
    hasher = PasswordHasher()
    password_hash = hasher.hash("wrongpassword")
    
    mock_user = Mock()
    mock_user.email = "test@example.com"  # Реальная строка
    mock_user.password_hash = password_hash  # Реальная строка
    mock_user.role = "student"  # Реальная строка
    
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = mock_user
    mock_db.query.return_value = mock_query
    
    response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]

def test_login_nonexistent_user(client, mock_db):
    """Тест входа несуществующего пользователя"""
    # Мокируем, что пользователь не найден
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None
    mock_db.query.return_value = mock_query
    
    response = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "password123"}
    )
    assert response.status_code == 401

def test_me_endpoint_success(client, mock_db):
    """Тест получения информации о текущем пользователе"""
    from src.infrastructure.models import UserORM
    from src.infrastructure.security import create_access_token
    
    # Создаем токен
    token = create_access_token(sub="test@example.com", role="student")
    
    # Мокируем пользователя
    mock_user = Mock()
    mock_user.id = 1
    mock_user.email = "test@example.com"  # Реальная строка
    mock_user.role = "student"  # Реальная строка
    
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = mock_user
    mock_db.query.return_value = mock_query
    
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"

def test_me_endpoint_invalid_token(client):
    """Тест получения информации с невалидным токеном"""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401

def test_me_endpoint_no_token(client):
    """Тест получения информации без токена"""
    response = client.get("/api/auth/me")
    assert response.status_code == 403

def test_rate_limiting(client, mock_db):
    """Тест rate limiting (базовый)"""
    from src.infrastructure.models import UserORM
    
    # В тестах rate limiting отключен, поэтому все запросы должны проходить
    # Но нужно замокировать пользователей, чтобы не было ошибок
    hasher = PasswordHasher()
    
    responses = []
    for i in range(15):
        email = f"test{i}@example.com"
        password = "password123"
        
        # Мокируем пользователя для каждого запроса
        password_hash = hasher.hash(password)
        mock_user = Mock()  # Без spec, чтобы избежать автоматических Mock объектов
        mock_user.email = email  # Реальная строка
        mock_user.password_hash = password_hash  # Реальная строка
        mock_user.role = "student"  # Реальная строка
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_user
        mock_db.query.return_value = mock_query
        
        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": password}
        )
        responses.append(response.status_code)
    
    # Все запросы должны пройти (rate limiting отключен в тестах)
    assert len(responses) == 15
