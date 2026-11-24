"""API endpoints: /health, /upload and /query."""

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.document_loader import load_and_split
from app.services.llm_service import LLMService
from app.services.storage_service import S3Storage
from app.services.vector_store import VectorStore

router = APIRouter()

vector_store = VectorStore()
llm_service = LLMService(vector_store)
storage = S3Storage()


class QueryRequest(BaseModel):
    question: str


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/upload")
def upload(file: UploadFile):
    if not file.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(status_code=400, detail="Only .pdf and .txt files are supported")

    content = file.file.read()
    chunks = load_and_split(file.filename, content)
    if not chunks:
        raise HTTPException(status_code=400, detail="No text found in the file")

    saved_to_s3 = storage.upload(content, file.filename)
    vector_store.add_documents(chunks)

    return {"message": "File processed", "chunks": len(chunks), "saved_to_s3": saved_to_s3}


@router.post("/query")
def query(request: QueryRequest):
    answer, sources = llm_service.ask(request.question)
    return {"answer": answer, "sources": sources}
