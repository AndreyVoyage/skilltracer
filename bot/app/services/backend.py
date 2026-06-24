"""HTTP client for SkillTracer backend API."""

from __future__ import annotations

import httpx

from app.config import settings


class BackendClient:
    """Async HTTP client for the SkillTracer backend."""

    def __init__(self) -> None:
        self.base_url = settings.BACKEND_URL.rstrip("/")
        self._token: str | None = None

    @property
    def headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def set_token(self, token: str) -> None:
        """Set JWT access token for subsequent requests."""
        self._token = token

    async def authenticate(self, telegram_id: int, username: str | None, first_name: str | None) -> str:
        """Authenticate bot request and store JWT token.

        Returns the access token string.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/auth/bot",
                json={
                    "telegram_id": telegram_id,
                    "username": username,
                    "first_name": first_name,
                },
                headers={"X-Bot-Token": settings.BOT_API_TOKEN},
            )
            response.raise_for_status()
            data = response.json()
            token = data["access_token"]
            self._token = token
            return token

    async def get_categories(self) -> list[dict]:
        """Fetch categories for the authenticated user."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/categories",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def create_entry(self, entry_date: str, ratings: list[dict], comment: str | None = None) -> dict:
        """Create a new daily entry."""
        payload: dict = {
            "entry_date": entry_date,
            "ratings": ratings,
        }
        if comment:
            payload["comment"] = comment

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/entries",
                json=payload,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def upload_media(self, entry_id: int, file_path: str, caption: str | None = None) -> dict:
        """Upload a media attachment for an entry.

        Note: This uses multipart/form-data and streams the file.
        """
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                files = {"file": f}
                data = {"caption": caption} if caption else {}
                response = await client.post(
                    f"{self.base_url}/api/v1/entries/{entry_id}/media",
                    files=files,
                    data=data,
                    headers={"Authorization": f"Bearer {self._token}"},
                )
            response.raise_for_status()
            return response.json()


backend = BackendClient()
