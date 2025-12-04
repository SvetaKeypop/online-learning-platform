import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

CURRENT_DIR = os.path.dirname(__file__)
SERVICE_ROOT = os.path.dirname(CURRENT_DIR)
if SERVICE_ROOT not in sys.path:
    sys.path.insert(0, SERVICE_ROOT)

from src.infrastructure.cache import get_cache, set_cache, delete_cache, delete_cache_pattern

@patch('src.infrastructure.cache.get_redis')
def test_get_cache_hit(mock_redis):
    """Тест получения значения из кэша (hit)"""
    mock_client = MagicMock()
    mock_client.get.return_value = '{"key": "value"}'
    mock_redis.return_value = mock_client
    
    result = get_cache("test_key")
    assert result == {"key": "value"}
    mock_client.get.assert_called_once_with("test_key")

@patch('src.infrastructure.cache.get_redis')
def test_get_cache_miss(mock_redis):
    """Тест получения значения из кэша (miss)"""
    mock_client = MagicMock()
    mock_client.get.return_value = None
    mock_redis.return_value = mock_client
    
    result = get_cache("test_key")
    assert result is None

@patch('src.infrastructure.cache.get_redis')
def test_get_cache_error(mock_redis):
    """Тест обработки ошибки при получении из кэша"""
    mock_redis.side_effect = Exception("Redis error")
    
    result = get_cache("test_key")
    assert result is None

@patch('src.infrastructure.cache.get_redis')
def test_set_cache(mock_redis):
    """Тест сохранения значения в кэш"""
    mock_client = MagicMock()
    mock_redis.return_value = mock_client
    
    result = set_cache("test_key", {"key": "value"}, ttl=300)
    assert result is True
    mock_client.setex.assert_called_once()

@patch('src.infrastructure.cache.get_redis')
def test_set_cache_error(mock_redis):
    """Тест обработки ошибки при сохранении в кэш"""
    mock_redis.side_effect = Exception("Redis error")
    
    result = set_cache("test_key", {"key": "value"})
    assert result is False

@patch('src.infrastructure.cache.get_redis')
def test_delete_cache(mock_redis):
    """Тест удаления значения из кэша"""
    mock_client = MagicMock()
    mock_redis.return_value = mock_client
    
    result = delete_cache("test_key")
    assert result is True
    mock_client.delete.assert_called_once_with("test_key")

@patch('src.infrastructure.cache.get_redis')
def test_delete_cache_pattern(mock_redis):
    """Тест удаления по паттерну"""
    mock_client = MagicMock()
    mock_client.keys.return_value = ["key1", "key2", "key3"]
    mock_client.delete.return_value = 3
    mock_redis.return_value = mock_client
    
    result = delete_cache_pattern("key*")
    assert result == 3
    mock_client.keys.assert_called_once_with("key*")

