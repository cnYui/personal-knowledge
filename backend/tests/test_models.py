from app.models.memory import Memory


def test_memory_model_has_expected_fields():
    memory = Memory(title="Test", title_status="ready", content="Body", group_id="default")

    assert memory.title == "Test"
    assert memory.content == "Body"
    assert memory.title_status == "ready"
    assert memory.group_id == "default"
    assert hasattr(memory, "created_at")
    assert hasattr(memory, "updated_at")
