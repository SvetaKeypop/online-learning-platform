# Руководство по деплою и использованию

## ❌ НЕ нужно завершать контейнеры вручную!

**Docker Swarm автоматически обновляет контейнеры** при выполнении `docker stack deploy`. Это называется **rolling update** (постепенное обновление).

### Как работает обновление

Благодаря настройкам в `docker-stack.yml`:
```yaml
update_config:
  parallelism: 1
  order: start-first      # Сначала запускается новый контейнер
  failure_action: rollback
```

**Процесс обновления:**
1. ✅ Docker Swarm скачивает новый образ
2. ✅ Запускает новый контейнер рядом со старым
3. ✅ Ждет, пока новый контейнер станет здоровым
4. ✅ Останавливает старый контейнер
5. ✅ Если новый контейнер не запустился - автоматический откат (rollback)

**Результат:** Обновление происходит **без простоя** (zero-downtime)!

## Использование CI/CD

### Автоматический деплой

1. **Внесите изменения в код**
2. **Закоммитьте и запушьте:**
   ```bash
   git add .
   git commit -m "Описание изменений"
   git push origin main
   ```

3. **CI/CD запустится автоматически:**
   - Тесты → Сборка → Публикация → Деплой
   - Проверьте статус: GitHub → `Actions` → последний workflow

4. **Контейнеры обновятся автоматически** - ничего делать не нужно!

### Ручной деплой (если нужно)

Если хотите обновить вручную без CI/CD:

```powershell
# 1. Скачать новые образы из Docker Hub
docker pull nvzhn/coderror-auth-service:latest
docker pull nvzhn/coderror-courses-service:v5
docker pull nvzhn/coderror-progress-service:v2
docker pull nvzhn/coderror-frontend:latest

# 2. Обновить стек (контейнеры обновятся автоматически)
cd deploy
docker stack deploy -c docker-stack.yml coderror
```

**Важно:** Не нужно останавливать контейнеры вручную! `docker stack deploy` сделает это автоматически.

## Проверка после деплоя

### 1. Проверить статус сервисов

```powershell
# Список всех сервисов
docker service ls

# Детальный статус конкретного сервиса
docker service ps coderror_courses-service
docker service ps coderror_progress-service
docker service ps coderror_auth-service
docker service ps coderror_frontend
```

**Ожидаемый результат:**
```
ID             NAME                          IMAGE                                          NODE            DESIRED STATE   CURRENT STATE
abc123...      coderror_courses-service.1    nvzhn/coderror-courses-service:v5             docker-desktop   Running         Running 2 minutes ago
```

### 2. Проверить логи

```powershell
# Логи конкретного сервиса
docker service logs coderror_courses-service --tail 50
docker service logs coderror_progress-service --tail 50
docker service logs coderror_auth-service --tail 50
docker service logs coderror_frontend --tail 50

# Логи в реальном времени
docker service logs -f coderror_courses-service
```

**Что искать:**
- ✅ `DB is up` - база данных подключена
- ✅ `Application startup complete` - приложение запущено
- ✅ `INFO: Uvicorn running on` - сервер работает
- ❌ `ERROR` или `Exception` - проблемы

### 3. Проверить здоровье сервисов

```powershell
# Проверить health endpoints
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

**Ожидаемый результат:** `{"status":"ok"}` или `{"status":"healthy"}`

### 4. Проверить работу через браузер

Откройте в браузере:
- **Frontend:** http://localhost:8080
- **API Docs (если есть):** http://localhost:8001/docs

## Использование приложения после деплоя

### Через веб-интерфейс

1. Откройте http://localhost:8080
2. Зарегистрируйтесь или войдите
3. Просматривайте курсы, проходите уроки

### Через API

#### 1. Регистрация нового пользователя

```powershell
# PowerShell
$body = @{
    email = "user@example.com"
    password = "password123"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/auth/register" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

#### 2. Вход и получение токена

```powershell
$body = @{
    email = "user@example.com"
    password = "password123"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

$token = $response.access_token
```

#### 3. Получение списка курсов

```powershell
Invoke-RestMethod -Uri "http://localhost:8001/api/courses" `
    -Method GET `
    -Headers @{Authorization = "Bearer $token"}
```

#### 4. Создание курса (только для admin)

```powershell
$body = @{
    title = "Новый курс"
    description = "Описание курса"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/courses" `
    -Method POST `
    -ContentType "application/json" `
    -Headers @{Authorization = "Bearer $token"} `
    -Body $body
```

#### 5. Отметка прогресса

```powershell
Invoke-RestMethod -Uri "http://localhost:8002/api/progress/1/complete" `
    -Method POST `
    -Headers @{Authorization = "Bearer $token"}
```

**Подробные примеры:** см. `scripts/API_EXAMPLES.md`

## Полезные команды

### Мониторинг

```powershell
# Статус всех сервисов
docker service ls

# Использование ресурсов
docker stats

# События Swarm
docker service events coderror_courses-service
```

### Откат к предыдущей версии

Если что-то пошло не так, Docker Swarm может автоматически откатиться (благодаря `failure_action: rollback`).

Или вручную:

```powershell
# Откатить сервис к предыдущей версии
docker service rollback coderror_courses-service

# Проверить историю обновлений
docker service ps coderror_courses-service
```

### Остановка и запуск

```powershell
# Остановить весь стек (все сервисы)
docker stack rm coderror

# Запустить стек заново
cd deploy
docker stack deploy -c docker-stack.yml coderror
```

### Очистка

```powershell
# Удалить неиспользуемые образы
docker image prune -a

# Удалить остановленные контейнеры
docker container prune

# Полная очистка (осторожно!)
docker system prune -a
```

## Решение проблем

### Сервис не запускается

1. **Проверьте логи:**
   ```powershell
   docker service logs coderror_courses-service --tail 100
   ```

2. **Проверьте статус:**
   ```powershell
   docker service ps coderror_courses-service
   ```

3. **Проверьте образ:**
   ```powershell
   docker images | grep coderror-courses-service
   ```

### База данных не подключается

1. **Проверьте postgres:**
   ```powershell
   docker service ps coderror_postgres
   docker service logs coderror_postgres --tail 50
   ```

2. **Проверьте подключение:**
   ```powershell
   docker exec -it $(docker ps -q -f name=coderror_postgres) psql -U admin -d courses_db
   ```

### Обновление не применяется

1. **Проверьте, что образ обновился:**
   ```powershell
   docker images | grep coderror-courses-service
   ```

2. **Принудительно обновите сервис:**
   ```powershell
   docker service update --force coderror_courses-service
   ```

3. **Проверьте, что используется правильный тег:**
   ```powershell
   # В docker-stack.yml должно быть:
   # image: nvzhn/coderror-courses-service:v5
   ```

## Чек-лист после деплоя

- [ ] Все сервисы в статусе `Running`
- [ ] Логи не содержат ошибок
- [ ] Health endpoints отвечают
- [ ] Веб-интерфейс открывается
- [ ] API работает (можно залогиниться)
- [ ] База данных подключена (в логах есть `DB is up`)

## Резюме

✅ **НЕ нужно** останавливать контейнеры вручную  
✅ **НЕ нужно** перезапускать сервисы  
✅ **Просто** делайте `git push` - все обновится автоматически  
✅ **Проверяйте** статус через `docker service ls` и логи  
✅ **Используйте** приложение через http://localhost:8080 или API

