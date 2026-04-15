"""
Auth API Tests

Тесты авторизации через Telegram initData.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestAuth:
    """Тесты авторизации."""
    
    def test_valid_init_data(self, client, auth_headers_user1):
        """Проверка валидации правильного initData."""
        response = client.get("/api/v1/me", headers=auth_headers_user1)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 123456
        assert data["username"] == "testuser1"
    
    def test_invalid_init_data(self, client, invalid_init_data):
        """Невалидный initData должен вернуть 401."""
        headers = {"X-Init-Data": invalid_init_data}
        response = client.get("/api/v1/me", headers=headers)
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]
    
    def test_expired_init_data(self, client, expired_init_data):
        """Просроченный initData (старше 5 минут) должен вернуть 401."""
        headers = {"X-Init-Data": expired_init_data}
        response = client.get("/api/v1/me", headers=headers)
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
    
    def test_missing_init_data(self, client):
        """Отсутствие initData должно вернуть 401."""
        response = client.get("/api/v1/me")
        assert response.status_code == 401
        assert "Missing" in response.json()["detail"]
    
    def test_init_data_creates_user(self, client, auth_headers_user1):
        """Валидный initData должен создать пользователя если его нет."""
        # Первый запрос создает пользователя
        response = client.get("/api/v1/me", headers=auth_headers_user1)
        assert response.status_code == 200
        
        # Второй запрос возвращает того же пользователя
        response2 = client.get("/api/v1/me", headers=auth_headers_user1)
        assert response2.status_code == 200
        assert response.json()["id"] == response2.json()["id"]
