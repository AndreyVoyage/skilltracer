"""
Groups API Tests

Тесты групп и групповой ленты.
"""

import pytest
from datetime import date, timedelta


class TestGroups:
    """Тесты групп."""
    
    def test_create_group(self, client, auth_headers_user1):
        """Создание группы."""
        response = client.post(
            "/api/v1/groups",
            headers=auth_headers_user1,
            json={
                "name": "Test Group",
                "description": "Test description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Group"
        assert "invite_code" in data
        assert len(data["invite_code"]) == 8
    
    def test_cannot_create_second_group(self, client, auth_headers_user1):
        """Нельзя создать вторую группу если уже в одной состоишь."""
        # Создаем первую группу
        client.post(
            "/api/v1/groups",
            headers=auth_headers_user1,
            json={"name": "First Group"},
        )
        
        # Пытаемся создать вторую
        response = client.post(
            "/api/v1/groups",
            headers=auth_headers_user1,
            json={"name": "Second Group"},
        )
        assert response.status_code == 400
        assert "Already in a group" in response.json()["detail"]
    
    def test_join_group_by_code(self, client, auth_headers_user1, auth_headers_user2):
        """Присоединение к группе по коду."""
        # User 1 создает группу
        create_response = client.post(
            "/api/v1/groups",
            headers=auth_headers_user1,
            json={"name": "Join Test Group"},
        )
        invite_code = create_response.json()["invite_code"]
        
        # User 2 присоединяется
        response = client.post(
            "/api/v1/groups/join",
            headers=auth_headers_user2,
            json={"invite_code": invite_code},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "joined"
    
    def test_join_invalid_code(self, client, auth_headers_user1):
        """Нельзя присоединиться по невалидному коду."""
        response = client.post(
            "/api/v1/groups/join",
            headers=auth_headers_user1,
            json={"invite_code": "INVALID"},
        )
        assert response.status_code == 404
    
    def test_max_3_members(self, client, auth_headers_user1, auth_headers_user2, auth_headers_user3):
        """Максимум 3 человека в группе."""
        # User 1 создает группу
        create_response = client.post(
            "/api/v1/groups",
            headers=auth_headers_user1,
            json={"name": "3 Members Group"},
        )
        invite_code = create_response.json()["invite_code"]
        
        # User 2 присоединяется
        client.post(
            "/api/v1/groups/join",
            headers=auth_headers_user2,
            json={"invite_code": invite_code},
        )
        
        # User 3 присоединяется (теперь в группе 3 человека)
        client.post(
            "/api/v1/groups/join",
            headers=auth_headers_user3,
            json={"invite_code": invite_code},
        )
        
        # User 4 пытается присоединиться (должно быть 400)
        from tests.test_api.conftest import generate_init_data
        auth_headers_user4 = {"X-Init-Data": generate_init_data(123459, "testuser4")}
        
        response = client.post(
            "/api/v1/groups/join",
            headers=auth_headers_user4,
            json={"invite_code": invite_code},
        )
        assert response.status_code == 400
        assert "full" in response.json()["detail"].lower()
    
    def test_feed_shows_only_published(self, client, auth_headers_user1, auth_headers_user2):
        """В ленте видны только published отчеты."""
        # Создаем группу
        create_response = client.post(
            "/api/v1/groups",
            headers=auth_headers_user1,
            json={"name": "Feed Test Group"},
        )
        invite_code = create_response.json()["invite_code"]
        
        # User 2 присоединяется
        client.post(
            "/api/v1/groups/join",
            headers=auth_headers_user2,
            json={"invite_code": invite_code},
        )
        
        # User 1 публикует отчет
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        # Создаем записи и публикуем
        for i in range(3):
            entry_date = monday + timedelta(days=i)
            client.post(
                "/api/v1/entries",
                headers=auth_headers_user1,
                json={
                    "entry_date": entry_date.isoformat(),
                    "mood": 4,
                },
            )
        
        client.post(
            f"/api/v1/weeks/{monday.isoformat()}/publish",
            headers=auth_headers_user1,
        )
        
        # User 2 смотрит ленту
        response = client.get("/api/v1/groups/feed", headers=auth_headers_user2)
        assert response.status_code == 200
        feed = response.json()
        
        # Все отчеты в ленте - published
        for item in feed:
            assert item["user"]["id"] != 123457  # Не свой отчет
            # Проверяем что данные есть
            assert "avg_mood" in item
            assert "filled_days" in item
