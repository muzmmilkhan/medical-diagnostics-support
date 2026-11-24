import logging

from fastapi import APIRouter, HTTPException, status

from app.api.deps import RAGServiceDep
from app.schemas.query import QueryRequest, QueryResponse, Source

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["query"])

SNIPPET_LENGTH = 300


@router.post("", response_model=QueryResponse)
def query(request: QueryRequest, rag: RAGServiceDep) -> QueryResponse:
    """Answer a question using the indexed documents as context."""
    try:
        answer, documents = rag.answer(request.question, request.history)
    except Exception as exc:
        logger.exception("RAG query failed")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "The language model request failed. Please retry."
        ) from exc

    sources = [
        Source(
            source=str(doc.metadata.get("source", "unknown")),
            page=doc.metadata.get("page"),
            snippet=doc.page_content[:SNIPPET_LENGTH],
        )
        for doc in documents
    ]
    return QueryResponse(answer=answer, sources=sources)
