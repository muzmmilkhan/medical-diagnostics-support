"""Store text chunks as embeddings in a local Chroma database and search them."""

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.config import Config


class VectorStore:
    def __init__(self):
        embeddings = OpenAIEmbeddings(
            model=Config.OPENAI_EMBEDDING_MODEL, api_key=Config.OPENAI_API_KEY
        )
        self.db = Chroma(
            collection_name="medical_documents",
            embedding_function=embeddings,
            persist_directory=Config.VECTOR_DB_PATH,
        )

    def add_documents(self, chunks: list[Document]) -> None:
        self.db.add_documents(chunks)

    def search(self, question: str, k: int = 4) -> list[Document]:
        return self.db.similarity_search(question, k=k)
