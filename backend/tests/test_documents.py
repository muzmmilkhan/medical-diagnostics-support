def test_upload_txt_indexes_chunks(client, vector_store):
    content = ("Type 2 diabetes is managed with lifestyle changes and metformin. " * 40).encode()
    response = client.post(
        "/api/v1/documents", files={"file": ("notes.txt", content, "text/plain")}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "notes.txt"
    assert body["chunks_processed"] > 1
    assert body["stored_in_s3"] is False
    assert len(vector_store.documents) == body["chunks_processed"]


def test_upload_rejects_unsupported_type(client):
    response = client.post(
        "/api/v1/documents", files={"file": ("image.png", b"\x89PNG", "image/png")}
    )
    assert response.status_code == 400


def test_upload_rejects_empty_text(client):
    response = client.post("/api/v1/documents", files={"file": ("empty.txt", b"   ", "text/plain")})
    assert response.status_code == 422


def test_upload_rejects_invalid_pdf(client):
    response = client.post(
        "/api/v1/documents", files={"file": ("bad.pdf", b"not a pdf", "application/pdf")}
    )
    assert response.status_code == 422
