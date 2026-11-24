from langchain_core.documents import Document


def test_query_returns_answer_and_sources(client, vector_store):
    vector_store.add_documents(
        [Document(page_content="Metformin is first-line.", metadata={"source": "d.pdf", "page": 3})]
    )
    response = client.post(
        "/api/v1/query",
        json={
            "question": "What is first-line therapy?",
            "history": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hey"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "Metformin" in body["answer"]
    assert body["sources"] == [
        {"source": "d.pdf", "page": 3, "snippet": "Metformin is first-line."}
    ]


def test_query_requires_question(client):
    response = client.post("/api/v1/query", json={"question": ""})
    assert response.status_code == 422
