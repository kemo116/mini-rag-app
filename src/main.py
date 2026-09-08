from contextlib import asynccontextmanager
from fastapi import FastAPI

from routes import data, nlp, base
from helpers.config import get_settings
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.llm.templates.template_parser import TemplateParser
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 1. Define the lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP CODE ---
    settings =  get_settings()
    postgres_conn = f"postgresql+asyncpg://{settings.POSTGRESS_USERNAME}:{settings.POSTGRESS_PASSWORD}@{settings.POSTGRESS_HOST}:{settings.POSTGRESS_PORT}/{settings.POSTGRESS_MAIN_DATABASE}"
    app.db_engine = create_async_engine(postgres_conn, echo=True)
    app.db_client = sessionmaker(
        app.db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    app.db_client = app.mongo_conn[settings.MONGODB_DB]

    llm_provider_factory = LLMProviderFactory(settings)
    vector_db_provider_factory = VectorDBProviderFactory(settings)

    app.generation_client = llm_provider_factory.create(provider=settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(model_id= settings.GENERATION_MODEL_ID)
    
    app.embedding_client = llm_provider_factory.create(provider=settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(model_id=settings.EMBEDDING_MODEL_ID, embedding_size=settings.EMBEDDING_MODEL_SIZE)

    app.vector_db_client = vector_db_provider_factory.create(provider=settings.VECTOR_DB_BACKEND)
    app.vector_db_client.connect()
    app.template_parser = TemplateParser(default_language=settings.PRIMARY_LANG, language=settings.DEFAULT_LANG)
    
    yield  # <-- This tells FastAPI the app is ready and to start accepting requests

    # --- SHUTDOWN CODE ---
    app.db_engine.dispose()
    app.vector_db_client.disconnect()


# 2. Pass the lifespan to the FastAPI instance
app = FastAPI(lifespan=lifespan)

# 3. Include your routers
app.include_router(base.router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)