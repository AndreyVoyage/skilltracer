"""
API Test Fixtures

Общие фикстуры для тестов API.
"""

import pytest
import hmac
import hashlib
import json
import urllib.parse
import time
from datetime import date, timedelta

import pytest_asyncio
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database import async_engine
from app.models.base import Base


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Создает и очищает таблицы для API тестов."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client():
    """TestClient для FastAPI приложения."""
    return TestClient(app)


def generate_init_data(user_id: int, username: str = "testuser", first_name: str = "Test") -> str:
    """
    Генерирует валидный initData для тестирования.
    
    Args:
        user_id: ID пользователя Telegram
        username: Username пользователя
        first_name: Имя пользователя
        
    Returns:
        Query string с подписью для Telegram Mini App
    """
    user = json.dumps({
        "id": user_id,
        "username": username,
        "first_name": first_name,
        "last_name": "User",
        "photo_url": None,
    })
    
    data = {
        "user": user,
        "auth_date": str(int(time.time())),
        "query_id": "test_query_id",
    }
    
    # Сортируем и формируем data_check_string
    data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(data.items()))
    
    # Вычисляем HMAC-SHA256
    secret_key = hmac.new(
        b"WebAppData",
        settings.BOT_TOKEN.encode(),
        hashlib.sha256
    ).digest()
    
    hash_value = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    data['hash'] = hash_value
    return urllib.parse.urlencode(data)


@pytest.fixture
def auth_headers_user1():
    """Заголовки авторизации для пользователя 1."""
    return {"X-Init-Data": generate_init_data(123456, "testuser1", "User1")}


@pytest.fixture
def auth_headers_user2():
    """Заголовки авторизации для пользователя 2."""
    return {"X-Init-Data": generate_init_data(123457, "testuser2", "User2")}


@pytest.fixture
def auth_headers_user3():
    """Заголовки авторизации для пользователя 3."""
    return {"X-Init-Data": generate_init_data(123458, "testuser3", "User3")}


@pytest.fixture
def expired_init_data():
    """Просроченный initData (для тестов валидации)."""
    user = json.dumps({
        "id": 123456,
        "username": "testuser",
        "first_name": "Test",
    })
    
    # auth_date из прошлого (больше 5 минут)
    data = {
        "user": user,
        "auth_date": str(int(time.time()) - 400),  # 6+ минут назад
        "query_id": "test_query_id",
    }
    
    data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(data.items()))
    
    secret_key = hmac.new(
        b"WebAppData",
        settings.BOT_TOKEN.encode(),
        hashlib.sha256
    ).digest()
    
    hash_value = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    data['hash'] = hash_value
    return urllib.parse.urlencode(data)


@pytest.fixture
def invalid_init_data():
    """Невалидный initData (неправильная подпись)."""
    user = json.dumps({
        "id": 123456,
        "username": "testuser",
        "first_name": "Test",
    })
    
    data = {
        "user": user,
        "auth_date": str(int(time.time())),
        "query_id": "test_query_id",
        "hash": "invalid_hash_value",
    }
    
    return urllib.parse.urlencode(data)
