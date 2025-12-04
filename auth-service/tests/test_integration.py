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
from src.interfaces.http.routers.auth import get_limiter

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

# Отключаем rate limiting в тестах
def override_get_limiter():
    from unittest.mock import MagicMock
    # Создаем mock limiter, который ничего не делает
    mock_limiter = MagicMock()
    # Переопределяем метод limit чтобы он возвращал декоратор, который ничего не делает
    def noop_limit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    mock_limiter.limit = noop_limit
    return mock_limiter

app.dependency_overrides[get_limiter] = override_get_limiter

@pytest.fixture(scope="function")
def client():
    # Создаем таблицы перед каждым тестом на тестовом engine
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield TestClient(app)
    # Очищаем после теста
    Base.metadata.drop_all(bind=test_engine)

def test_full_auth_flow(client):
    """Интеграционный тест полного потока аутентификации"""
    email = "integration@example.com"
    password = "securepassword123"
    
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
    
    # 2. Попытка повторной регистрации (должна провалиться)
    duplicate_response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password}
    )
    assert duplicate_response.status_code == 400
    
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
    wrong_password_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "wrongpassword"}
    )
    assert wrong_password_response.status_code == 401
    
    # 5. Получение информации о себе с валидным токеном
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

def test_multiple_users(client):
    """Тест работы с несколькими пользователями"""
    users = []
    
    # Создаем несколько пользователей
    for i in range(5):
        email = f"user{i}@example.com"
        password = f"password{i}"
        
        register_response = client.post(
            "/api/auth/register",
            json={"email": email, "password": password}
        )
        assert register_response.status_code == 201
        
        login_response = client.post(
            "/api/auth/login",
            json={"email": email, "password": password}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        users.append({"email": email, "token": token})
    
    # Проверяем, что все пользователи могут получить свою информацию
    for user in users:
        me_response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {user['token']}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == user["email"]

