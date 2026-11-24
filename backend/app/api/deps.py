from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from langchain_openai import ChatOpenAI

from app.core.config import Settings, get_settings
from app.services.document_processor import DocumentProcessor
from app.services.rag_service import RAGService
from app.services.storage_service import S3StorageService
from app.services.vector_store import ChromaVectorStore, VectorStore


def _require_openai_key(settings: Settings) -> None:
    if settings.openai_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured on the server.",
        )


@lru_cache
def _chroma_store() -> ChromaVectorStore:
    return ChromaVectorStore(get_settings())


def get_vector_store() -> VectorStore:
    _require_openai_key(get_settings())
    return _chroma_store()


@lru_cache
def get_document_processor() -> DocumentProcessor:
    settings = get_settings()
    return DocumentProcessor(settings.chunk_size, settings.chunk_overlap)


@lru_cache
def get_storage() -> S3StorageService | None:
    return S3StorageService.from_settings(get_settings())


def get_rag_service(
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> RAGService:
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.llm_temperature,
        api_key=settings.openai_api_key,
    )
    return RAGService(llm, vector_store, k=settings.retriever_k)


SettingsDep = Annotated[Settings, Depends(get_settings)]
VectorStoreDep = Annotated[VectorStore, Depends(get_vector_store)]
DocumentProcessorDep = Annotated[DocumentProcessor, Depends(get_document_processor)]
StorageDep = Annotated[S3StorageService | None, Depends(get_storage)]
RAGServiceDep = Annotated[RAGService, Depends(get_rag_service)]
