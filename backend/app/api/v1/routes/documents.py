import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.deps import DocumentProcessorDep, SettingsDep, StorageDep, VectorStoreDep
from app.schemas.documents import UploadResponse
from app.services.document_processor import SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=UploadResponse)
def upload_document(
    settings: SettingsDep,
    processor: DocumentProcessorDep,
    vector_store: VectorStoreDep,
    storage: StorageDep,
    file: UploadFile = File(...),
) -> UploadResponse:
    """Upload a .pdf or .txt file, split it into chunks and index it for retrieval."""
    filename = Path(file.filename or "").name
    if not filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No file selected.")
    if Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only .txt and .pdf files are supported.")

    content = file.file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, f"File exceeds {settings.max_upload_mb} MB limit."
        )

    try:
        chunks = processor.process(filename, content)
    except Exception as exc:
        logger.exception("Failed to parse %s", filename)
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Could not read document: {exc}"
        ) from exc
    if not chunks:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "No extractable text found in document."
        )

    stored_in_s3 = False
    if storage is not None:
        try:
            storage.upload(content, filename)
            stored_in_s3 = True
        except Exception:
            # Archival is best-effort; indexing still proceeds.
            logger.exception("S3 upload failed for %s", filename)

    vector_store.add_documents(chunks)
    logger.info("Indexed %s (%d chunks)", filename, len(chunks))
    return UploadResponse(
        message="File uploaded and processed successfully",
        filename=filename,
        chunks_processed=len(chunks),
        stored_in_s3=stored_in_s3,
    )
