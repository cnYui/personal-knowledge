from fastapi.testclient import TestClient

from app.main import app


def test_upload_memory_with_image_returns_created():
    with TestClient(app) as client:
        response = client.post(
            "/api/uploads/memories",
            data={
                "content": "A graph with nodes and edges.",
                "group_id": "default",
            },
            files={"images": ("note.png", b"fake-image-bytes", "image/png")},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["title_status"] in {"pending", "ready", "failed"}
    assert body["group_id"] == "default"
    assert body["images_count"] == 1
