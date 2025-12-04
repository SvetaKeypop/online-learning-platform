import pytest
import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
SERVICE_ROOT = os.path.dirname(CURRENT_DIR)
if SERVICE_ROOT not in sys.path:
    sys.path.insert(0, SERVICE_ROOT)

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Настройка тестового окружения"""
    # Отключаем rate limiting для тестов (или используем тестовый Redis)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/99")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_auth.db")

