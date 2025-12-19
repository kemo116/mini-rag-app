from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):

    APP_NAME: str
    APP_VERSION: str
    OPENAI_API_KEY: str
    CHUNK_SIZE: int

    FILE_MAX_SIZE: int
    FILE_ALLOWED_EXTENSIONS: list
    class Config:
        env_file = ".env"

def get_settings():
    return Settings()