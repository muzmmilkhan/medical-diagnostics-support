from typing import Protocol

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import Settings


class VectorStore(Protocol):
    def add_documents(self, documents: list[Document]) -> int: ...

    def similarity_search(self, query: str, k: int) -> list[Document]: ...


class ChromaVectorStore:
    """Persistent Chroma collection backed by OpenAI embeddings."""

    def __init__(self, settings: Settings) -> None:
        settings.vector_db_path.mkdir(parents=True, exist_ok=True)
        embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )
        self._store = Chroma(
            collection_name=settings.collection_name,
            embedding_function=embeddings,
            persist_directory=str(settings.vector_db_path),
        )

    def add_documents(self, documents: list[Document]) -> int:
        if not documents:
            return 0
        self._store.add_documents(documents)
        return len(documents)

    def similarity_search(self, query: str, k: int) -> list[Document]:
        return self._store.similarity_search(query, k=k)
