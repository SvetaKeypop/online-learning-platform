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
from src.interfaces.http.authz import require_admin

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
    db.delete = MagicMock()
    return db

def create_override_get_db(mock_db):
    """Создает функцию переопределения get_db для тестов"""
    def _get_db():
        yield mock_db
    return _get_db

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
def client(mock_db):
    """Фикстура для тестового клиента"""
    # Переопределяем get_db для каждого теста
    app.dependency_overrides[get_db] = create_override_get_db(mock_db)
    yield TestClient(app)
    # Очищаем после теста
    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]

def test_list_courses_empty(client, mock_db):
    """Тест получения пустого списка курсов"""
    # Мокируем пустой результат
    mock_query = MagicMock()
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.all.return_value = []
    mock_db.query.return_value = mock_query
    
    response = client.get("/api/courses")
    assert response.status_code == 200
    assert response.json() == []

def test_list_courses_with_pagination(client, mock_db):
    """Тест пагинации курсов"""
    # Мокируем курс
    from src.infrastructure.models import Course
    mock_course = Mock(spec=Course)
    mock_course.id = 1
    mock_course.title = "Test Course"
    mock_course.description = "Test Description"
    
    # Мокируем результат запроса
    mock_query = MagicMock()
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.all.return_value = [mock_course]
    mock_db.query.return_value = mock_query
    
    response = client.get("/api/courses?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Course"

def test_list_courses_invalid_pagination(client):
    """Тест невалидной пагинации"""
    response = client.get("/api/courses?limit=0")
    assert response.status_code == 422
    
    response = client.get("/api/courses?limit=101")
    assert response.status_code == 422
    
    response = client.get("/api/courses?offset=-1")
    assert response.status_code == 422

def test_get_course_lessons_not_found(client, mock_db):
    """Тест получения уроков несуществующего курса"""
    # Мокируем, что курс не найден
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None
    mock_db.query.return_value = mock_query
    
    response = client.get("/api/courses/999/lessons")
    assert response.status_code == 404

def test_get_course_lessons_empty(client, mock_db):
    """Тест получения пустого списка уроков"""
    # Мокируем, что курс существует, но уроков нет
    from src.infrastructure.models import Course, Lesson
    mock_course = Mock(spec=Course)
    mock_course.id = 1
    
    mock_query_course = MagicMock()
    mock_query_course.filter.return_value = mock_query_course
    mock_query_course.first.return_value = mock_course
    
    mock_query_lesson = MagicMock()
    mock_query_lesson.filter.return_value = mock_query_lesson
    mock_query_lesson.order_by.return_value = mock_query_lesson
    mock_query_lesson.all.return_value = []
    
    def query_side_effect(model):
        # Используем is для сравнения классов, чтобы избежать проблем с SQLAlchemy
        if model is Course:
            return mock_query_course
        elif model is Lesson:
            return mock_query_lesson
        # Для db.query(Course.id) - проверяем, является ли это Column объектом
        # SQLAlchemy Column имеет атрибут 'key' или 'property'
        if hasattr(model, 'key') or (hasattr(model, 'property') and hasattr(model.property, 'key')):
            # Это атрибут модели, например Course.id
            mock_attr_query = MagicMock()
            mock_attr_query.filter.return_value = mock_attr_query
            mock_attr_query.first.return_value = 1  # Возвращаем id курса
            return mock_attr_query
        return MagicMock()
    
    mock_db.query.side_effect = query_side_effect
    
    response = client.get("/api/courses/1/lessons")
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

def test_create_course(client, admin_override, mock_db):
    """Тест создания курса"""
    # Мокируем создание курса
    from src.infrastructure.models import Course
    mock_course = Mock(spec=Course)
    mock_course.id = 1
    mock_course.title = "Test Course"
    mock_course.description = "Test Description"
    
    mock_db.refresh.return_value = None
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    
    # Мокируем refresh чтобы установить id
    def refresh_side_effect(obj):
        obj.id = 1
    
    mock_db.refresh.side_effect = refresh_side_effect
    
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

def test_update_course_not_found(client, admin_override, mock_db):
    """Тест обновления несуществующего курса"""
    # Мокируем, что курс не найден
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None
    mock_db.query.return_value = mock_query
    
    response = client.put(
        "/api/courses/999",
        json={"title": "Updated Title"},
        headers={"Authorization": "Bearer test"}
    )
    assert response.status_code == 404

def test_delete_course_not_found(client, admin_override, mock_db):
    """Тест удаления несуществующего курса"""
    # Мокируем, что курс не найден
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None
    mock_db.query.return_value = mock_query
    
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
