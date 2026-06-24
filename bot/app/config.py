from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    BACKEND_URL: str = "http://localhost:8000"
    BOT_API_TOKEN: str = "bot-dev-token-change-in-production"

    class Config:
        env_file = ".env"

settings = Settings()
