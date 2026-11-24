"""Answer a question using the most relevant document chunks (RAG)."""

from langchain_openai import ChatOpenAI

from app.config import Config
from app.services.vector_store import VectorStore

PROMPT = """You are a medical diagnostics support assistant.
Answer the question using only the context below. If the answer is not in the context, say you don't know.

Context:
{context}

Question: {question}"""


class LLMService:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.llm = ChatOpenAI(
            model=Config.OPENAI_MODEL,
            temperature=0.2,
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.BASE_URL,  # None = default OpenAI URL
        )

    def ask(self, question: str) -> tuple[str, list[dict]]:
        # 1. Find the chunks most related to the question
        chunks = self.vector_store.search(question)
        context = "\n\n".join(chunk.page_content for chunk in chunks)

        # 2. Ask the LLM, giving it those chunks as context
        response = self.llm.invoke(PROMPT.format(context=context, question=question))

        sources = [
            {"source": c.metadata.get("source"), "page": c.metadata.get("page"), "text": c.page_content[:300]}
            for c in chunks
        ]
        return response.content, sources
