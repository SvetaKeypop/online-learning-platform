from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./progress.db"
    REDIS_URL: str = "redis://localhost:6379/2"
    SECRET_KEY: str = "dev-secret-progress"
    JWT_ALGORITHM: str = "HS256"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
