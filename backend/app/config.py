"""
Skill Tracer Configuration Module

Использует Pydantic Settings для валидации и загрузки конфигурации
из переменных окружения и .env файла.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """
    Настройки приложения Skill Tracer.
    
    Все значения могут быть переопределены через переменные окружения
    или .env файл в корне проекта.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Telegram Bot
    BOT_TOKEN: str
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://skilluser:skillpass@localhost:5432/skilltracer"
    
    # WebApp
    WEBAPP_URL: str = "http://localhost"
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    
    # Environment
    ENVIRONMENT: str = "development"  # development / production
    
    # Domain (used for Caddy and webhook configuration)
    DOMAIN: str = "localhost"
    
    # SOCKS5 proxy for Telegram API (e.g. socks5://user:pass@host:port)
    TELEGRAM_PROXY: Optional[str] = None
    
    # Bot mode: webhook (default) or polling
    BOT_MODE: str = "webhook"
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """
        Проверка что DATABASE_URL использует поддерживаемый драйвер.
        
        Для async SQLAlchemy с PostgreSQL требуется asyncpg.
        """
        allowed_prefixes = (
            "postgresql+asyncpg://",
            "postgresql+psycopg://",
            "sqlite+aiosqlite://",
        )
        if not any(v.startswith(prefix) for prefix in allowed_prefixes):
            raise ValueError(
                f"DATABASE_URL должен начинаться с одного из: {allowed_prefixes}. "
                f"Для PostgreSQL с async используйте 'postgresql+asyncpg://'"
            )
        return v
    
    @property
    def is_development(self) -> bool:
        """Проверка что окружение разработки."""
        return self.ENVIRONMENT.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Проверка что окружение продакшена."""
        return self.ENVIRONMENT.lower() == "production"


# Глобальный экземпляр настроек
settings = Settings()
