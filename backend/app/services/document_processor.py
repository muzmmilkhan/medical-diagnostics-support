import io
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".txt"})


class UnsupportedFileTypeError(ValueError):
    pass


def load_documents(filename: str, content: bytes) -> list[Document]:
    """Turn raw file bytes into LangChain documents (one per PDF page, or one for text)."""
    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        documents = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                documents.append(
                    Document(page_content=text, metadata={"source": filename, "page": page_number})
                )
        return documents
    if extension == ".txt":
        text = content.decode("utf-8", errors="replace")
        return [Document(page_content=text, metadata={"source": filename})] if text.strip() else []
    raise UnsupportedFileTypeError(f"Unsupported file type: {extension or 'none'}")


class DocumentProcessor:
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def process(self, filename: str, content: bytes) -> list[Document]:
        return self._splitter.split_documents(load_documents(filename, content))
