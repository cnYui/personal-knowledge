from fastapi.testclient import TestClient

from app.main import app


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
