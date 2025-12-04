# Руководство по тестированию

## Обзор

Проект использует `pytest` для тестирования всех сервисов. Тесты разделены на несколько категорий:

- **Unit тесты** - тестирование отдельных компонентов
- **Integration тесты** - тестирование взаимодействия компонентов
- **API тесты** - тестирование HTTP endpoints

## Структура тестов

```
service-name/
  tests/
    test_health.py      # Health check тесты
    test_*.py           # Unit тесты
    test_integration.py # Integration тесты
    conftest.py         # Pytest конфигурация
```

## Запуск тестов

### Локально

```bash
# Все тесты
pytest

# Конкретный сервис
cd courses-service
pytest

# С покрытием
pytest --cov=src --cov-report=html

# Конкретный тест
pytest tests/test_courses.py::test_list_courses_empty

# Только unit тесты
pytest -m unit

# Только integration тесты
pytest -m integration
```

### В CI/CD

Тесты автоматически запускаются при каждом push в `main` через GitHub Actions.

## Типы тестов

### 1. Health Check тесты

Проверяют базовую работоспособность сервисов:

```python
def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

### 2. API тесты

Тестируют HTTP endpoints:

- **Courses Service**: CRUD операции для курсов и уроков
- **Auth Service**: регистрация, логин, получение информации о пользователе
- **Progress Service**: завершение уроков, получение прогресса

### 3. Integration тесты

Тестируют полные сценарии использования:

- Полный жизненный цикл курса (создание → добавление уроков → обновление → удаление)
- Полный поток аутентификации (регистрация → логин → получение информации)

### 4. Кэш тесты

Тестируют работу кэширования:

- Получение из кэша (hit/miss)
- Сохранение в кэш
- Удаление из кэша
- Обработка ошибок Redis

## Покрытие кода

Текущее покрытие можно проверить:

```bash
pytest --cov=src --cov-report=term-missing
```

Целевое покрытие: **> 80%**

## Моки и фикстуры

### Тестовая БД

Каждый тест использует изолированную SQLite БД в памяти:

```python
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
```

### Моки

Используются для:
- JWT токенов (авторизация)
- Redis (кэширование)
- Внешних зависимостей

## Примеры тестов

### Тест создания курса

```python
@patch('src.interfaces.http.routers.courses.require_admin')
def test_create_course(mock_admin, client):
    mock_admin.return_value = {"sub": "admin@example.com", "role": "admin"}
    
    response = client.post(
        "/api/courses",
        json={"title": "Test Course", "description": "Test Description"},
        headers={"Authorization": "Bearer test"}
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Test Course"
```

### Тест регистрации пользователя

```python
def test_register_user_success(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
```

## Добавление новых тестов

1. Создайте файл `test_*.py` в директории `tests/`
2. Используйте фикстуры из `conftest.py`
3. Следуйте naming convention: `test_<functionality>`
4. Добавьте маркеры для категоризации (`@pytest.mark.unit`, `@pytest.mark.integration`)

## Troubleshooting

### Тесты падают локально

1. Убедитесь, что установлены все зависимости: `pip install -r requirements.txt pytest`
2. Проверьте, что тестовая БД создается корректно
3. Запустите с `-v` для подробного вывода: `pytest -v`

### Тесты падают в CI/CD

1. Проверьте логи в GitHub Actions
2. Убедитесь, что все зависимости указаны в `requirements.txt`
3. Проверьте версии Python (должна быть 3.12)

## Метрики

- **Количество тестов**: 50+
- **Покрытие**: > 80%
- **Время выполнения**: < 30 секунд для всех тестов

## Best Practices

1. ✅ Каждый тест должен быть независимым
2. ✅ Используйте фикстуры для setup/teardown
3. ✅ Тестируйте как успешные, так и неуспешные сценарии
4. ✅ Используйте понятные имена тестов
5. ✅ Добавляйте docstrings для сложных тестов
6. ✅ Избегайте тестов, зависящих от порядка выполнения

