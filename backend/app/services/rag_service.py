from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.schemas.query import ChatMessage
from app.services.vector_store import VectorStore

SYSTEM_PROMPT = """You are a medical diagnostics support assistant for clinicians.
Answer the question using only the context below, which comes from documents the user uploaded.
If the context does not contain the answer, say that you don't know rather than guessing.
Be concise and cite context passages by their [number] where relevant.
Your answers support, but never replace, professional clinical judgement.

Context:
{context}"""


def format_context(documents: list[Document]) -> str:
    if not documents:
        return "(no relevant documents found)"
    return "\n\n".join(f"[{i}] {doc.page_content}" for i, doc in enumerate(documents, start=1))


class RAGService:
    def __init__(self, llm: BaseChatModel, vector_store: VectorStore, k: int = 4) -> None:
        self._llm = llm
        self._vector_store = vector_store
        self._k = k

    def answer(
        self, question: str, history: list[ChatMessage] | None = None
    ) -> tuple[str, list[Document]]:
        documents = self._vector_store.similarity_search(question, k=self._k)
        messages: list[BaseMessage] = [
            SystemMessage(content=SYSTEM_PROMPT.format(context=format_context(documents)))
        ]
        for message in history or []:
            cls = HumanMessage if message.role == "user" else AIMessage
            messages.append(cls(content=message.content))
        messages.append(HumanMessage(content=question))

        result = self._llm.invoke(messages)
        return str(result.content), documents
