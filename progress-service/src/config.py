from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./progress.db"
    SECRET_KEY: str = "dev-secret-progress"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
