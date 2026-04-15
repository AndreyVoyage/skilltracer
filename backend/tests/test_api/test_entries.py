"""
Entries API Tests

Тесты CRUD для DailyEntry.
"""

import pytest
from datetime import date, timedelta


class TestEntries:
    """Тесты записей дня."""
    
    def test_create_entry(self, client, auth_headers_user1):
        """Создание новой записи."""
        response = client.post(
            "/api/v1/entries",
            headers=auth_headers_user1,
            json={
                "entry_date": date.today().isoformat(),
                "mood": 4,
                "text": "Отличный день!",
                "metrics": [],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mood"] == 4
        assert data["text"] == "Отличный день!"
        assert "id" in data
    
    def test_edit_entry_within_10_days(self, client, auth_headers_user1):
        """Редактирование записи в пределах 10 дней разрешено."""
        today = date.today()
        
        # Создаем запись
        client.post(
            "/api/v1/entries",
            headers=auth_headers_user1,
            json={
                "entry_date": today.isoformat(),
                "mood": 3,
                "text": "Средний день",
            },
        )
        
        # Редактируем
        response = client.post(
            "/api/v1/entries",
            headers=auth_headers_user1,
            json={
                "entry_date": today.isoformat(),
                "mood": 5,
                "text": "На самом деле отличный день!",
            },
        )
        assert response.status_code == 200
        assert response.json()["mood"] == 5
    
    def test_edit_entry_after_10_days(self, client, auth_headers_user1):
        """Редактирование записи старше 10 дней должно вернуть 400."""
        old_date = (date.today() - timedelta(days=15)).isoformat()
        
        response = client.post(
            "/api/v1/entries",
            headers=auth_headers_user1,
            json={
                "entry_date": old_date,
                "mood": 4,
            },
        )
        assert response.status_code == 400
        assert "10 days" in response.json()["detail"]
    
    def test_private_entries(self, client, auth_headers_user1, auth_headers_user2):
        """Пользователь 2 не должен видеть записи пользователя 1."""
        # User 1 создает запись
        client.post(
            "/api/v1/entries",
            headers=auth_headers_user1,
            json={
                "entry_date": date.today().isoformat(),
                "mood": 4,
                "text": "Секретная запись пользователя 1",
            },
        )
        
        # User 2 получает свои записи
        response = client.get("/api/v1/entries", headers=auth_headers_user2)
        assert response.status_code == 200
        entries = response.json()
        
        # Проверяем что записи User 1 не видны
        for entry in entries:
            assert entry.get("text") != "Секретная запись пользователя 1"
    
    def test_get_entries_with_date_range(self, client, auth_headers_user1):
        """Получение записей с фильтром по датам."""
        today = date.today()
        
        # Создаем запись
        client.post(
            "/api/v1/entries",
            headers=auth_headers_user1,
            json={
                "entry_date": today.isoformat(),
                "mood": 4,
            },
        )
        
        # Получаем с фильтром
        response = client.get(
            "/api/v1/entries",
            headers=auth_headers_user1,
            params={
                "start_date": today.isoformat(),
                "end_date": today.isoformat(),
            },
        )
        assert response.status_code == 200
        entries = response.json()
        assert len(entries) >= 1
    
    def test_delete_entry(self, client, auth_headers_user1):
        """Удаление записи."""
        today = date.today()
        
        # Создаем запись
        client.post(
            "/api/v1/entries",
            headers=auth_headers_user1,
            json={
                "entry_date": today.isoformat(),
                "mood": 4,
            },
        )
        
        # Удаляем
        response = client.delete(
            f"/api/v1/entries/{today.isoformat()}",
            headers=auth_headers_user1,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        
        # Проверяем что удалена
        get_response = client.get(
            f"/api/v1/entries/{today.isoformat()}",
            headers=auth_headers_user1,
        )
        assert get_response.status_code == 404
    
    def test_mood_validation(self, client, auth_headers_user1):
        """Настроение должно быть от 1 до 5."""
        today = date.today()
        
        # Mood 6 - невалидное
        response = client.post(
            "/api/v1/entries",
            headers=auth_headers_user1,
            json={
                "entry_date": today.isoformat(),
                "mood": 6,
            },
        )
        assert response.status_code == 422  # Validation error
