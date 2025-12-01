from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    DATABASE_URL: str = Field(...)
    SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = "HS256"
    class Config: env_file = ".env"; extra = "ignore"

settings = Settings()
