from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import motor.motor_asyncio

class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    CHUNK_SIZE: int

    POSTGRESS_USERNAME: str
    POSTGRESS_PASSWORD: str
    POSTGRESS_MAIN_DATABASE: str
    POSTGRESS_HOST: str
    POSTGRESS_PORT: int

    FILE_MAX_SIZE: int
    FILE_ALLOWED_EXTENSIONS: list
    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str
    
    COHERE_API_KEY: Optional[str] = None
    OPENAI_API_URL: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OLLAMA_API_URL: Optional[str] = None

    GENERATION_MODEL_ID_LITERAL: list = []
    GENERATION_MODEL_ID: Optional[str] = None
    EMBEDDING_MODEL_ID: Optional[str] = None
    EMBEDDING_MODEL_SIZE: Optional[int] = None
    INPUT_DEFAULT_MAX_CHARACTERS: Optional[int] = None
    GENERATION_DEFAULT_MAX_TOKENS: Optional[int] = None
    GENERATION_DEFAULT_TEMPERATURE: Optional[float] = None


    VECTOR_DB_BACKEND_LITERAL: list = []
    VECTOR_DB_BACKEND: str = "QDRANT"
    VECTOR_DB_PATH: str = "qdrant_db"
    VECTOR_DB_DISTANCE_METHOD: str = "cosine"
    VECTOR_DB_PGVEC_INDEX_THRESHOLD: int = 100
    PRIMARY_LANG: str = "en"
    DEFAULT_LANG: str = "en"

    class Config:
        env_file = ".env"

def get_settings():
    return Settings()