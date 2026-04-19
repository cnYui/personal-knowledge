from fastapi.testclient import TestClient

from app.main import app
from app.workers.title_generation_worker import title_generation_worker


def test_upload_memory_with_image_returns_created(monkeypatch):
    enqueued_ids: list[str] = []

    async def fake_enqueue(memory_id: str):
        enqueued_ids.append(memory_id)

    monkeypatch.setattr(title_generation_worker, "enqueue", fake_enqueue)

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
    assert body["title"] == "标题生成中"
    assert body["title_status"] == "pending"
    assert body["group_id"] == "default"
    assert body["images_count"] == 1
    assert body["processing_status"] == "pending"
    assert enqueued_ids == [body["id"]]
