from __future__ import annotations

import hashlib
import hmac
import time

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_current_user
from app.models.schemas import TelegramAuthData, UserCreate
from app.models.user import User
from app.services.auth import (
    create_access_token,
    decode_access_token,
    get_or_create_user,
    verify_telegram_auth,
)


def _make_telegram_hash(data: dict[str, object], bot_token: str) -> str:
    """Generate a Telegram Login Widget HMAC-SHA256 hash for testing."""
    items = sorted(
        (key, str(value))
        for key, value in data.items()
        if value is not None and key != "hash"
    )
    data_check_string = "\n".join(f"{key}={value}" for key, value in items)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    return hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()


def _valid_telegram_payload() -> dict[str, object]:
    """Return a sample Telegram auth payload with a fresh auth_date."""
    return {
        "id": 123456789,
        "first_name": "Andrey",
        "username": "andreyvoyage",
        "auth_date": int(time.time()),
    }


class TestTelegramAuthValidation:
    """Tests for Telegram OAuth hash verification."""

    def test_valid_hash_returns_true(self) -> None:
        """A correctly signed Telegram payload should be accepted."""
        payload = _valid_telegram_payload()
        payload["hash"] = _make_telegram_hash(payload, settings.TELEGRAM_BOT_TOKEN)
        data = TelegramAuthData.model_validate(payload)

        assert verify_telegram_auth(data) is True

    def test_invalid_hash_returns_false(self) -> None:
        """A payload with a tampered hash should be rejected."""
        payload = _valid_telegram_payload()
        payload["hash"] = "invalidhash"
        data = TelegramAuthData.model_validate(payload)

        assert verify_telegram_auth(data) is False

    def test_expired_auth_date_returns_false(self) -> None:
        """A payload older than the allowed window should be rejected."""
        payload = _valid_telegram_payload()
        payload["auth_date"] = int(time.time()) - 100_000
        payload["hash"] = _make_telegram_hash(payload, settings.TELEGRAM_BOT_TOKEN)
        data = TelegramAuthData.model_validate(payload)

        assert verify_telegram_auth(data) is False


class TestTokenGeneration:
    """Tests for JWT access token creation and decoding."""

    def test_create_and_decode_token(self) -> None:
        """A created token should decode back to the original user ID."""
        token = create_access_token(user_id=42)

        assert isinstance(token, str)
        assert decode_access_token(token) == 42

    def test_decode_invalid_token_returns_none(self) -> None:
        """Decoding a malformed token should return None."""
        assert decode_access_token("not-a-valid-token") is None

    def test_decode_tampered_token_returns_none(self) -> None:
        """A tampered token should fail decoding and return None."""
        token = create_access_token(user_id=42)
        tampered = token[:-5] + "xxxxx"

        assert decode_access_token(tampered) is None


class TestUserService:
    """Tests for user persistence logic."""

    async def test_create_user(self, db_session: AsyncSession) -> None:
        """Creating a new user should persist it with all fields."""
        user = await get_or_create_user(
            db_session,
            UserCreate(
                telegram_id=987654321,
                username="testuser",
                first_name="Test",
                last_name="User",
            ),
        )

        assert user.id is not None
        assert user.telegram_id == 987654321
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.last_name == "User"

    async def test_get_existing_user(
        self,
        db_session: AsyncSession,
        sample_user: User,
    ) -> None:
        """Calling get_or_create_user for an existing user should return it."""
        user = await get_or_create_user(
            db_session,
            UserCreate(
                telegram_id=sample_user.telegram_id,
                username="new_username",
                first_name="New",
            ),
        )

        assert user.id == sample_user.id
        assert user.telegram_id == sample_user.telegram_id
        assert user.username == "new_username"
        assert user.first_name == "New"


class TestAuthEndpoints:
    """Tests for the authentication API endpoints."""

    def test_telegram_auth_valid_returns_token(self, client: TestClient) -> None:
        """A valid Telegram payload should yield a JWT access token."""
        payload = _valid_telegram_payload()
        payload["hash"] = _make_telegram_hash(payload, settings.TELEGRAM_BOT_TOKEN)

        response = client.post("/api/v1/auth/telegram", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert decode_access_token(data["access_token"]) is not None

    def test_telegram_auth_invalid_hash_returns_401(self, client: TestClient) -> None:
        """An invalid Telegram hash should return HTTP 401."""
        payload = _valid_telegram_payload()
        payload["hash"] = "invalidhash"

        response = client.post("/api/v1/auth/telegram", json=payload)

        assert response.status_code == 401

    def test_get_current_user_unauthorized(self, client: TestClient) -> None:
        """Requesting /auth/me without a token should return HTTP 401."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_get_current_user_authorized(
        self,
        client: TestClient,
        sample_user: User,
    ) -> None:
        """Requesting /auth/me with a valid token should return the user."""
        token = create_access_token(sample_user.id)

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_user.id
        assert data["telegram_id"] == sample_user.telegram_id


class TestGetCurrentUserDependency:
    """Tests for the get_current_user dependency."""

    async def test_get_current_user_valid(
        self,
        db_session: AsyncSession,
        sample_user: User,
    ) -> None:
        """A valid token should resolve to the corresponding user."""
        token = create_access_token(sample_user.id)
        credentials = type("Credentials", (), {"credentials": token})()

        user = await get_current_user(credentials=credentials, db=db_session)

        assert user.id == sample_user.id

    async def test_get_current_user_missing_token(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Missing credentials should raise HTTP 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None, db=db_session)

        assert exc_info.value.status_code == 401

    async def test_get_current_user_invalid_token(
        self,
        db_session: AsyncSession,
    ) -> None:
        """An invalid token should raise HTTP 401."""
        credentials = type("Credentials", (), {"credentials": "bad-token"})()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=credentials, db=db_session)

        assert exc_info.value.status_code == 401

    async def test_get_current_user_unknown_user(
        self,
        db_session: AsyncSession,
    ) -> None:
        """A token for a non-existent user should raise HTTP 401."""
        token = create_access_token(user_id=999_999)
        credentials = type("Credentials", (), {"credentials": token})()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=credentials, db=db_session)

        assert exc_info.value.status_code == 401


def test_health_check(client: TestClient) -> None:
    """The health endpoint should remain available."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
