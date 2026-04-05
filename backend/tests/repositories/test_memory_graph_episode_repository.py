from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.memory import Memory, MemoryGraphEpisode
from app.repositories.memory_graph_episode_repository import MemoryGraphEpisodeRepository


SQLALCHEMY_TEST_DATABASE_URL = 'sqlite:///./test.db'
test_engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={'check_same_thread': False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


def test_get_next_version_returns_one_for_memory_without_rows(db_session):
    repo = MemoryGraphEpisodeRepository()
    memory = Memory(title="Test", title_status="ready", content="Body", group_id="default")
    db_session.add(memory)
    db_session.commit()

    assert repo.get_next_version(db_session, memory.id) == 1


def test_replace_latest_version_demotes_old_rows_and_promotes_new_rows(db_session):
    repo = MemoryGraphEpisodeRepository()
    memory = Memory(title="Test", title_status="ready", content="Body", group_id="default")
    db_session.add(memory)
    db_session.commit()

    old_row = MemoryGraphEpisode(
        memory_id=memory.id,
        episode_uuid="episode-old",
        version=1,
        chunk_index=0,
        is_latest=True,
        reference_time=datetime(2026, 4, 5, tzinfo=UTC),
    )
    db_session.add(old_row)
    db_session.commit()

    repo.replace_latest_version(
        db_session,
        memory_id=memory.id,
        version=2,
        episodes=[
            {"episode_uuid": "episode-new-1", "chunk_index": 0, "reference_time": datetime(2026, 4, 6, tzinfo=UTC)},
            {"episode_uuid": "episode-new-2", "chunk_index": 1, "reference_time": datetime(2026, 4, 6, tzinfo=UTC)},
        ],
    )

    rows = (
        db_session.query(MemoryGraphEpisode)
        .filter(MemoryGraphEpisode.memory_id == memory.id)
        .order_by(MemoryGraphEpisode.version, MemoryGraphEpisode.chunk_index)
        .all()
    )
    assert [(row.version, row.chunk_index, row.is_latest) for row in rows] == [
        (1, 0, False),
        (2, 0, True),
        (2, 1, True),
    ]


def test_list_latest_episode_uuids_returns_lookup_map(db_session):
    repo = MemoryGraphEpisodeRepository()
    memory = Memory(title="Test", title_status="ready", content="Body", group_id="default")
    db_session.add(memory)
    db_session.commit()
    db_session.add_all(
        [
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid="episode-old", version=1, chunk_index=0, is_latest=False),
            MemoryGraphEpisode(memory_id=memory.id, episode_uuid="episode-new", version=2, chunk_index=0, is_latest=True),
        ]
    )
    db_session.commit()

    lookup = repo.get_latest_episode_uuid_set(db_session, ["episode-old", "episode-new", "episode-missing"])
    assert lookup == {"episode-new"}