from pydantic_settings import BaseSettings, SettingsConfigDict
import motor.motor_asyncio


class Settings(BaseSettings):

    APP_NAME: str
    APP_VERSION: str
    OPENAI_API_KEY: str
    CHUNK_SIZE: int
    MONGODB_URL: str
    MONGODB_DB: str
    FILE_MAX_SIZE: int
    FILE_ALLOWED_EXTENSIONS: list
    class Config:
        env_file = ".env"

def get_settings():
    return Settings()