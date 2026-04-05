from app.models.memory import Memory, MemoryGraphEpisode


def test_memory_model_has_expected_fields():
    memory = Memory(title="Test", title_status="ready", content="Body", group_id="default")

    assert memory.title == "Test"
    assert memory.content == "Body"
    assert memory.title_status == "ready"
    assert memory.group_id == "default"
    assert hasattr(memory, "created_at")
    assert hasattr(memory, "updated_at")


def test_memory_graph_episode_model_has_expected_fields_and_relationships():
    memory = Memory(title="Test", title_status="ready", content="Body", group_id="default")
    episode = MemoryGraphEpisode(
        memory=memory,
        episode_uuid="episode-1",
        version=1,
        chunk_index=0,
        is_latest=True,
    )

    assert episode.memory is memory
    assert episode.episode_uuid == "episode-1"
    assert episode.version == 1
    assert episode.chunk_index == 0
    assert episode.is_latest is True
    assert hasattr(episode, "reference_time")
    assert hasattr(episode, "created_at")
    assert hasattr(memory, "graph_episodes")
