import pytest

from app.services.document_processor import DocumentProcessor, UnsupportedFileTypeError


def test_splits_long_text_with_metadata():
    processor = DocumentProcessor(chunk_size=100, chunk_overlap=10)
    chunks = processor.process("a.txt", ("word " * 200).encode())
    assert len(chunks) > 1
    assert all(len(c.page_content) <= 100 for c in chunks)
    assert all(c.metadata["source"] == "a.txt" for c in chunks)


def test_rejects_unknown_extension():
    with pytest.raises(UnsupportedFileTypeError):
        DocumentProcessor(100, 10).process("a.docx", b"data")
