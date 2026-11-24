from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.api import deps
from app.main import create_app
from app.services.rag_service import RAGService


class InMemoryVectorStore:
    def __init__(self) -> None:
        self.documents: list[Document] = []

    def add_documents(self, documents: list[Document]) -> int:
        self.documents.extend(documents)
        return len(documents)

    def similarity_search(self, query: str, k: int) -> list[Document]:
        return self.documents[:k]


@pytest.fixture
def vector_store() -> InMemoryVectorStore:
    return InMemoryVectorStore()


@pytest.fixture
def client(vector_store: InMemoryVectorStore) -> Iterator[TestClient]:
    app = create_app()
    fake_llm = FakeListChatModel(responses=["Metformin is a common first-line therapy [1]."])
    app.dependency_overrides[deps.get_vector_store] = lambda: vector_store
    app.dependency_overrides[deps.get_storage] = lambda: None
    app.dependency_overrides[deps.get_rag_service] = lambda: RAGService(fake_llm, vector_store)
    with TestClient(app) as test_client:
        yield test_client
