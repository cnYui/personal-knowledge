from fastapi.testclient import TestClient

from app.main import app


def test_send_chat_message_returns_answer():
    client = TestClient(app)

    response = client.post("/api/chat/messages", json={"message": "什么是向量空间？"})

    assert response.status_code == 200
    assert "answer" in response.json()
