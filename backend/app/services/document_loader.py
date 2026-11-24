"""Turn an uploaded PDF or TXT file into small text chunks."""

import io

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)


def load_and_split(filename: str, content: bytes) -> list[Document]:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        pages = [
            Document(page_content=page.extract_text() or "", metadata={"source": filename, "page": number})
            for number, page in enumerate(reader.pages, start=1)
        ]
    else:  # .txt
        text = content.decode("utf-8", errors="ignore")
        pages = [Document(page_content=text, metadata={"source": filename})]

    return splitter.split_documents(pages)
