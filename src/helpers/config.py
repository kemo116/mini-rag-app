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
    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str
    COHERE_API_KEY: str = None
    OPENAI_API_URL: str = None
    OPENAI_API_KEY: str = None

    GENERATION_MODEL_ID: str = None
    EMBEDDING_MODEL_ID: str = None
    EMBEDDING_MODEL_SIZE: int = None
    INPUT_DEFAULT_MAX_CHARACTERS: int = None
    GENERATION_DEFAULT_MAX_TOKENS: int = None 
    GENERATION_DEFAULT_TEMPERATURE: float = None

    class Config:
        env_file = ".env"

def get_settings():
    return Settings()