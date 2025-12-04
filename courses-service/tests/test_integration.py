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

def test_full_course_lifecycle(client, admin_override, mock_db):
    """Интеграционный тест полного жизненного цикла курса"""
    from src.infrastructure.models import Course, Lesson
    
    # Настройка моков для создания курса
    mock_course = Mock(spec=Course)
    mock_course.id = 1
    mock_course.title = "Python Basics"
    mock_course.description = "Learn Python"
    
    def refresh_side_effect(obj):
        obj.id = 1
    
    mock_db.refresh.side_effect = refresh_side_effect
    
    # 1. Создаем курс
    create_response = client.post(
        "/api/courses",
        json={"title": "Python Basics", "description": "Learn Python"},
        headers={"Authorization": "Bearer test"}
    )
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]
    
    # Настройка моков для списка курсов
    mock_query_courses = MagicMock()
    mock_query_courses.order_by.return_value = mock_query_courses
    mock_query_courses.limit.return_value = mock_query_courses
    mock_query_courses.offset.return_value = mock_query_courses
    mock_query_courses.all.return_value = [mock_course]
    
    # 2. Получаем список курсов
    def query_side_effect(model):
        if model == Course:
            return mock_query_courses
        return MagicMock()
    
    mock_db.query.side_effect = query_side_effect
    list_response = client.get("/api/courses")
    assert list_response.status_code == 200
    courses = list_response.json()
    assert len(courses) >= 1
    
    # Настройка моков для создания урока
    mock_lesson = Mock(spec=Lesson)
    mock_lesson.id = 1
    mock_lesson.course_id = course_id
    mock_lesson.title = "Introduction"
    mock_lesson.content = "Welcome to Python"
    mock_lesson.order = 1
    
    def refresh_lesson_side_effect(obj):
        obj.id = 1
        obj.course_id = course_id
    
    mock_db.refresh.side_effect = refresh_lesson_side_effect
    
    # 3. Создаем уроки
    lesson1_response = client.post(
        f"/api/courses/{course_id}/lessons",
        json={"title": "Introduction", "content": "Welcome to Python", "order": 1},
        headers={"Authorization": "Bearer test"}
    )
    assert lesson1_response.status_code == 201
    lesson1_id = lesson1_response.json()["id"]
    
    # Настройка моков для получения уроков
    mock_lesson2 = Mock(spec=Lesson)
    mock_lesson2.id = 2
    mock_lesson2.course_id = course_id
    mock_lesson2.title = "Variables"
    mock_lesson2.content = "Learn about variables"
    mock_lesson2.order = 2
    
    mock_query_course_check = MagicMock()
    mock_query_course_check.filter.return_value = mock_query_course_check
    mock_query_course_check.first.return_value = mock_course
    
    mock_query_lessons = MagicMock()
    mock_query_lessons.filter.return_value = mock_query_lessons
    mock_query_lessons.order_by.return_value = mock_query_lessons
    mock_query_lessons.all.return_value = [mock_lesson, mock_lesson2]
    
    def query_lessons_side_effect(model):
        if model == Course:
            return mock_query_course_check
        elif model == Lesson:
            return mock_query_lessons
        return MagicMock()
    
    mock_db.query.side_effect = query_lessons_side_effect
    
    # 4. Получаем уроки курса
    lessons_response = client.get(f"/api/courses/{course_id}/lessons")
    assert lessons_response.status_code == 200
    lessons = lessons_response.json()
    assert len(lessons) == 2
    assert lessons[0]["order"] == 1
    assert lessons[1]["order"] == 2

def test_course_with_multiple_lessons(client, admin_override, mock_db):
    """Тест курса с множеством уроков"""
    from src.infrastructure.models import Course, Lesson
    
    # Настройка моков для создания курса
    mock_course = Mock(spec=Course)
    mock_course.id = 1
    mock_course.title = "Advanced Course"
    mock_course.description = "Many lessons"
    
    def refresh_course_side_effect(obj):
        obj.id = 1
    
    mock_db.refresh.side_effect = refresh_course_side_effect
    
    # Создаем курс
    course_response = client.post(
        "/api/courses",
        json={"title": "Advanced Course", "description": "Many lessons"},
        headers={"Authorization": "Bearer test"}
    )
    assert course_response.status_code == 201
    course_id = course_response.json()["id"]
    
    # Настройка моков для получения уроков
    mock_lessons = []
    for i in range(10):
        mock_lesson = Mock(spec=Lesson)
        mock_lesson.id = i + 1
        mock_lesson.course_id = course_id
        mock_lesson.title = f"Lesson {i+1}"
        mock_lesson.content = f"Content {i+1}"
        mock_lesson.order = i + 1
        mock_lessons.append(mock_lesson)
    
    mock_query_course_check = MagicMock()
    mock_query_course_check.filter.return_value = mock_query_course_check
    mock_query_course_check.first.return_value = mock_course
    
    mock_query_lessons = MagicMock()
    mock_query_lessons.filter.return_value = mock_query_lessons
    mock_query_lessons.order_by.return_value = mock_query_lessons
    mock_query_lessons.all.return_value = mock_lessons
    
    def query_lessons_side_effect(model):
        if model == Course:
            return mock_query_course_check
        elif model == Lesson:
            return mock_query_lessons
        return MagicMock()
    
    mock_db.query.side_effect = query_lessons_side_effect
    
    # Получаем все уроки
    lessons_response = client.get(f"/api/courses/{course_id}/lessons")
    assert lessons_response.status_code == 200
    lessons = lessons_response.json()
    assert len(lessons) == 10
    
    # Проверяем порядок
    for i, lesson in enumerate(lessons):
        assert lesson["order"] == i + 1
