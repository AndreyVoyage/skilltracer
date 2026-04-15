"""
Reports API Tests

Тесты публикации недельных отчетов.
"""

import pytest
from datetime import date, timedelta


class TestReports:
    """Тесты недельных отчетов."""
    
    def test_get_current_week(self, client, auth_headers_user1):
        """Получение текущей недели."""
        response = client.get("/api/v1/weeks/current", headers=auth_headers_user1)
        assert response.status_code == 200
        data = response.json()
        assert "week_start" in data
        assert "week_end" in data
        assert data["status"] in ["draft", "published"]
    
    def test_get_week_data(self, client, auth_headers_user1):
        """Получение агрегированных данных недели."""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        client.post(
            "/api/v1/entries",
            headers=auth_headers_user1,
            json={
                "entry_date": monday.isoformat(),
                "mood": 4,
                "text": "Тест данных недели",
            },
        )
        
        response = client.get(
            f"/api/v1/weeks/{monday.isoformat()}/data",
            headers=auth_headers_user1,
        )
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "trackers" in data
        assert "file_ids" in data
        assert len(data["entries"]) >= 1
    
    def test_render_report_accepted(self, client, auth_headers_user1):
        """Запрос на генерацию отчета возвращает 202."""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        # Создаем запись
        client.post(
            "/api/v1/entries",
            headers=auth_headers_user1,
            json={
                "entry_date": monday.isoformat(),
                "mood": 4,
            },
        )
        
        response = client.post(
            f"/api/v1/weeks/{monday.isoformat()}/render",
            headers=auth_headers_user1,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
    
    def test_render_report_empty_week_fails(self, client, auth_headers_user1):
        """Генерация отчета для пустой недели возвращает 400."""
        today = date.today()
        monday = today - timedelta(days=today.weekday()) - timedelta(weeks=4)
        
        response = client.post(
            f"/api/v1/weeks/{monday.isoformat()}/render",
            headers=auth_headers_user1,
        )
        assert response.status_code == 400
        assert "No entries" in response.json()["detail"]
    
    def test_download_rendered_report(self, client, auth_headers_user1):
        """Скачивание сгенерированного отчета возвращает JPEG."""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        client.post(
            "/api/v1/entries",
            headers=auth_headers_user1,
            json={
                "entry_date": monday.isoformat(),
                "mood": 4,
                "text": "Тест скачивания",
            },
        )
        
        response = client.get(
            f"/api/v1/weeks/{monday.isoformat()}/render/download",
            headers=auth_headers_user1,
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
    
    def test_share_report(self, client, auth_headers_user1):
        """Поделиться отчетом ставит задачу в очередь."""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        client.post(
            "/api/v1/entries",
            headers=auth_headers_user1,
            json={
                "entry_date": monday.isoformat(),
                "mood": 5,
            },
        )
        
        response = client.post(
            f"/api/v1/weeks/{monday.isoformat()}/share",
            headers=auth_headers_user1,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert "queue_id" in data
    
    def test_cannot_publish_empty_week(self, client, auth_headers_user1):
        """Нельзя опубликовать неделю без записей (минимум 3 дня)."""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        response = client.post(
            f"/api/v1/weeks/{monday.isoformat()}/publish",
            headers=auth_headers_user1,
        )
        assert response.status_code == 400
        assert "3 days" in response.json()["detail"]
    
    def test_publish_week(self, client, auth_headers_user1):
        """Публикация недели с 3+ записями."""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        # Создаем 3 записи на неделе
        for i in range(3):
            entry_date = monday + timedelta(days=i)
            client.post(
                "/api/v1/entries",
                headers=auth_headers_user1,
                json={
                    "entry_date": entry_date.isoformat(),
                    "mood": 4,
                    "text": f"День {i+1}",
                },
            )
        
        # Публикуем
        response = client.post(
            f"/api/v1/weeks/{monday.isoformat()}/publish",
            headers=auth_headers_user1,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        assert data["filled_days"] == 3
        assert data["avg_mood"] is not None
    
    def test_analytics_data_format(self, client, auth_headers_user1):
        """Проверка формата данных для графиков."""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        # Создаем записи
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
        
        # Получаем аналитику
        response = client.get(
            f"/api/v1/weeks/{monday.isoformat()}/analytics",
            headers=auth_headers_user1,
        )
        assert response.status_code == 200
        data = response.json()
        
        # Проверяем структуру
        assert "mood_by_day" in data
        assert "tracker_averages" in data
        assert "stats" in data
        
        # Проверяем mood_by_day (должно быть 7 дней)
        assert len(data["mood_by_day"]) == 7
