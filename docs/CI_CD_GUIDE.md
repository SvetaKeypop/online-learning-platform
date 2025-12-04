# Руководство по использованию CI/CD

## Обзор

В проекте реализован CI/CD pipeline через GitHub Actions, который автоматически:
1. Запускает тесты для всех Python-сервисов
2. Собирает Docker-образы
3. Публикует образы в Docker Hub
4. Деплоит обновления на сервер через self-hosted runner

## Как это работает

### Триггер
Pipeline запускается автоматически при каждом push в ветку `main`.

### Этапы CI/CD

#### 1. Тестирование (`tests`)
- Запускается для каждого сервиса: `auth-service`, `courses-service`, `progress-service`
- Устанавливает Python 3.12
- Устанавливает зависимости
- Запускает тесты через `pytest`

#### 2. Сборка и публикация (`build-and-push`)
- Собирает Docker-образы для всех сервисов
- Публикует образы в Docker Hub с соответствующими тегами
- Образы:
  - `{DOCKERHUB_USERNAME}/coderror-auth-service:latest`
  - `{DOCKERHUB_USERNAME}/coderror-courses-service:latest` и `v5`
  - `{DOCKERHUB_USERNAME}/coderror-progress-service:latest` и `v2`
  - `{DOCKERHUB_USERNAME}/coderror-frontend:latest`

#### 3. Деплой (`deploy`)
- Выполняется на self-hosted runner (ваш локальный Windows-сервер)
- Скачивает последние образы из Docker Hub
- Обновляет Docker Stack через `docker stack deploy`

## Настройка CI/CD

### 1. Настройка GitHub Secrets

В настройках репозитория GitHub (`Settings` → `Secrets and variables` → `Actions`) нужно добавить:

- **DOCKERHUB_USERNAME** - ваш логин в Docker Hub
- **DOCKERHUB_TOKEN** - токен доступа к Docker Hub (создается в Docker Hub → Account Settings → Security)

### 2. Настройка Self-Hosted Runner

Для работы деплоя нужен self-hosted runner на вашем Windows-сервере:

1. **Установка runner:**
   - Перейдите в `Settings` → `Actions` → `Runners` → `New self-hosted runner`
   - Следуйте инструкциям для Windows
   - Запустите runner как службу

2. **Требования на сервере:**
   - Docker Desktop или Docker Engine
   - Docker Swarm должен быть инициализирован (`docker swarm init`)
   - PowerShell

### 3. Синхронизация тегов

**✅ Исправлено:** CI/CD теперь пушит образы с правильными тегами:
- `courses-service`: `latest` и `v5` (соответствует `docker-stack.yml`)
- `progress-service`: `latest` и `v2` (соответствует `docker-stack.yml`)
- `auth-service`: `latest`
- `frontend`: `latest`

При деплое используются версионные теги (`v5`, `v2`), что позволяет контролировать версии в продакшене.

## Использование CI/CD

### Автоматический деплой

1. **Внесите изменения в код**
2. **Закоммитьте и запушьте в main:**
   ```bash
   git add .
   git commit -m "Описание изменений"
   git push origin main
   ```

3. **Pipeline запустится автоматически:**
   - Проверьте статус в GitHub: `Actions` → выберите последний workflow run
   - Дождитесь завершения всех этапов

4. **Проверьте деплой:**
   ```bash
   docker service ls
   docker service ps coderror_courses-service
   ```

**Важно:** Контейнеры обновляются автоматически без простоя! Не нужно их останавливать вручную. Docker Swarm делает rolling update: сначала запускает новый контейнер, потом останавливает старый.

### Ручной запуск (если нужно)

Можно запустить workflow вручную через GitHub UI:
- `Actions` → выберите workflow → `Run workflow`

## Текущие проблемы и рекомендации

### ✅ Проблема с тегами решена

CI/CD теперь пушит образы с правильными версионными тегами, соответствующими `docker-stack.yml`.

### Рекомендации

1. **Используйте версионные теги** для продакшена:
   - В CI/CD можно добавить теги на основе git tag или commit SHA
   - Это позволит откатываться к предыдущим версиям

2. **Добавьте уведомления:**
   - Email при успешном/неуспешном деплое
   - Slack/Discord интеграцию

3. **Добавьте health checks:**
   - После деплоя проверять, что сервисы отвечают
   - Автоматический rollback при ошибках

## Проверка статуса CI/CD

### В GitHub:
1. Откройте репозиторий на GitHub
2. Перейдите в `Actions`
3. Выберите последний workflow run
4. Проверьте статус каждого job

### На сервере:
```bash
# Проверить статус сервисов
docker service ls

# Проверить логи деплоя
docker service logs coderror_courses-service --tail 20
```

## Отладка проблем

### Если тесты падают:
- Проверьте логи в GitHub Actions
- Запустите тесты локально: `pytest` в директории сервиса

### Если сборка образов падает:
- Проверьте Dockerfile
- Проверьте, что Docker Hub credentials правильные

### Если деплой не работает:
- Проверьте, что self-hosted runner запущен
- Проверьте логи runner: `Actions` → `Runners` → выберите runner → `View logs`
- Убедитесь, что Docker Swarm инициализирован на сервере

