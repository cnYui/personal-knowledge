from fastapi.testclient import TestClient

from app.main import app
from app.workers.title_generation_worker import title_generation_worker


def test_create_and_list_memories():
    with TestClient(app) as client:
        create_response = client.post(
            "/api/memories",
            json={
                "title": "Linear Algebra",
                "content": "Vector spaces and basis.",
                "group_id": "default",
                "title_status": "ready",
            },
        )

        assert create_response.status_code == 201
        created = create_response.json()

        list_response = client.get("/api/memories")
        payload = list_response.json()

    assert list_response.status_code == 200
    target = next((item for item in payload if item["id"] == created["id"]), None)
    assert target is not None
    assert target["title"] == "Linear Algebra"
    assert target["group_id"] == "default"
    assert target["graph_error"] is None


def test_create_memory_clip_enqueues_title_generation(monkeypatch):
    enqueued_ids: list[str] = []

    async def fake_enqueue(memory_id: str):
        enqueued_ids.append(memory_id)

    monkeypatch.setattr(title_generation_worker, "enqueue", fake_enqueue)

    with TestClient(app) as client:
        response = client.post(
            "/api/memories/clip",
            json={
                "title": "临时标题",
                "content": "这是一段来自浏览器插件的摘录内容。",
                "source_platform": "chatgpt",
                "source_url": "https://chatgpt.com/c/test",
                "source_type": "browser_clip",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "标题生成中"
    assert body["title_status"] == "pending"
    assert enqueued_ids == [body["id"]]
