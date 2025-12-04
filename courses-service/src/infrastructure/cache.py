import json
import redis
from typing import Optional, Any
from ..config import settings

_redis_client: Optional[redis.Redis] = None

def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
    return _redis_client

def get_cache(key: str) -> Optional[Any]:
    """Получить значение из кэша"""
    try:
        client = get_redis()
        value = client.get(key)
        if value:
            return json.loads(value)
    except Exception:
        # Если Redis недоступен, просто возвращаем None
        pass
    return None

def set_cache(key: str, value: Any, ttl: int = None) -> bool:
    """Сохранить значение в кэш"""
    try:
        client = get_redis()
        ttl = ttl or settings.CACHE_TTL
        client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        return True
    except Exception:
        # Если Redis недоступен, просто игнорируем
        return False

def delete_cache(key: str) -> bool:
    """Удалить значение из кэша"""
    try:
        client = get_redis()
        client.delete(key)
        return True
    except Exception:
        return False

def delete_cache_pattern(pattern: str) -> int:
    """Удалить все ключи по паттерну"""
    try:
        client = get_redis()
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)
        return 0
    except Exception:
        return 0

