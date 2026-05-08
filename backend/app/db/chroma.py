import chromadb
from chromadb.config import Settings as ChromaSettings
from pathlib import Path
from functools import lru_cache
from app.core.config import get_settings

app_settings = get_settings()


@lru_cache()
def get_chroma_client() -> chromadb.ClientAPI:
    Path(app_settings.chroma_db_path).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=app_settings.chroma_db_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client


def get_pdf_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name="pdf_documents",
        metadata={"hnsw:space": "cosine"},
    )
