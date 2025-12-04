from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./auth.db"
    REDIS_URL: str = "redis://localhost:6379/1"
    SECRET_KEY: str = "dev-secret-auth"
    JWT_ALGORITHM: str = "HS256"
    LOG_LEVEL: str = "INFO"
    RATE_LIMIT_PER_MINUTE: int = 60
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
