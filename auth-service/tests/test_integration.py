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
from src.infrastructure.security import PasswordHasher, create_access_token
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

def test_full_auth_flow(client, mock_db):
    """Интеграционный тест полного потока аутентификации"""
    from src.infrastructure.models import UserORM
    
    email = "integration@example.com"
    password = "securepassword123"
    hasher = PasswordHasher()
    
    # Настройка моков для регистрации
    mock_query_register = MagicMock()
    mock_query_register.filter.return_value = mock_query_register
    mock_query_register.first.return_value = None  # Пользователя нет
    
    def refresh_register_side_effect(obj):
        obj.id = 1
        obj.email = email
        obj.role = "student"
    
    mock_db.refresh.side_effect = refresh_register_side_effect
    mock_db.query.return_value = mock_query_register
    
    # 1. Регистрация
    register_response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password}
    )
    assert register_response.status_code == 201
    user_data = register_response.json()
    assert user_data["email"] == email
    assert user_data["role"] == "student"
    user_id = user_data["id"]
    
    # Настройка моков для повторной регистрации
    mock_user = Mock(spec=UserORM)
    mock_user.id = user_id
    mock_user.email = email
    mock_user.role = "student"
    
    mock_query_duplicate = MagicMock()
    mock_query_duplicate.filter.return_value = mock_query_duplicate
    mock_query_duplicate.first.return_value = mock_user  # Пользователь уже есть
    mock_db.query.return_value = mock_query_duplicate
    
    # 2. Попытка повторной регистрации (должна провалиться)
    duplicate_response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password}
    )
    assert duplicate_response.status_code == 400
    
    # Настройка моков для логина
    password_hash = hasher.hash(password)
    mock_user_login = Mock(spec=UserORM)
    mock_user_login.id = user_id
    mock_user_login.email = email
    mock_user_login.password_hash = password_hash
    mock_user_login.role = "student"
    
    mock_query_login = MagicMock()
    mock_query_login.filter.return_value = mock_query_login
    mock_query_login.first.return_value = mock_user_login
    mock_db.query.return_value = mock_query_login
    
    # 3. Логин с правильными данными
    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    token = token_data["access_token"]
    
    # 4. Логин с неправильным паролем
    mock_user_wrong = Mock(spec=UserORM)
    mock_user_wrong.email = email
    mock_user_wrong.password_hash = hasher.hash("wrongpassword")
    
    mock_query_wrong = MagicMock()
    mock_query_wrong.filter.return_value = mock_query_wrong
    mock_query_wrong.first.return_value = mock_user_wrong
    mock_db.query.return_value = mock_query_wrong
    
    wrong_password_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "wrongpassword"}
    )
    assert wrong_password_response.status_code == 401
    
    # 5. Получение информации о себе с валидным токеном
    mock_query_me = MagicMock()
    mock_query_me.filter.return_value = mock_query_me
    mock_query_me.first.return_value = mock_user_login
    mock_db.query.return_value = mock_query_me
    
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == email
    assert me_data["id"] == user_id
    
    # 6. Получение информации с невалидным токеном
    invalid_token_response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token_here"}
    )
    assert invalid_token_response.status_code == 401
    
    # 7. Получение информации без токена
    no_token_response = client.get("/api/auth/me")
    assert no_token_response.status_code == 403

def test_multiple_users(client, mock_db):
    """Тест работы с несколькими пользователями"""
    from src.infrastructure.models import UserORM
    
    hasher = PasswordHasher()
    users = []
    
    # Создаем несколько пользователей
    for i in range(5):
        email = f"user{i}@example.com"
        password = f"password{i}"
        
        # Настройка моков для регистрации
        mock_query_register = MagicMock()
        mock_query_register.filter.return_value = mock_query_register
        mock_query_register.first.return_value = None
        
        def refresh_side_effect(obj, user_id=i+1):
            obj.id = user_id
            obj.email = email
            obj.role = "student"
        
        mock_db.refresh.side_effect = refresh_side_effect
        mock_db.query.return_value = mock_query_register
        
        register_response = client.post(
            "/api/auth/register",
            json={"email": email, "password": password}
        )
        assert register_response.status_code == 201
        
        # Настройка моков для логина
        password_hash = hasher.hash(password)
        mock_user = Mock(spec=UserORM)
        mock_user.id = i + 1
        mock_user.email = email
        mock_user.password_hash = password_hash
        mock_user.role = "student"
        
        mock_query_login = MagicMock()
        mock_query_login.filter.return_value = mock_query_login
        mock_query_login.first.return_value = mock_user
        mock_db.query.return_value = mock_query_login
        
        login_response = client.post(
            "/api/auth/login",
            json={"email": email, "password": password}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        users.append({"email": email, "token": token})
    
    # Проверяем, что все пользователи могут получить свою информацию
    for i, user in enumerate(users):
        mock_user_me = Mock(spec=UserORM)
        mock_user_me.id = i + 1
        mock_user_me.email = user["email"]
        mock_user_me.role = "student"
        
        mock_query_me = MagicMock()
        mock_query_me.filter.return_value = mock_query_me
        mock_query_me.first.return_value = mock_user_me
        mock_db.query.return_value = mock_query_me
        
        me_response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {user['token']}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == user["email"]
