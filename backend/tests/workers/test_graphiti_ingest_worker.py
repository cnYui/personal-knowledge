from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.workers.graphiti_ingest_worker import GraphitiIngestWorker


@patch('app.workers.graphiti_ingest_worker.GraphitiClient')
def test_worker_initialization(mock_graphiti_client):
    worker = GraphitiIngestWorker()

    assert worker.queue is not None
    assert worker.running is False
    assert worker.graphiti_client is not None
    assert worker.repository is not None


@pytest.mark.anyio
@patch('app.workers.graphiti_ingest_worker.GraphitiClient')
async def test_enqueue(mock_graphiti_client):
    worker = GraphitiIngestWorker()

    memory_id = 'test-memory-123'
    await worker.enqueue(memory_id)

    assert worker.queue.qsize() == 1
    queued_id = await worker.queue.get()
    assert queued_id == memory_id


@pytest.mark.anyio
@patch('app.workers.graphiti_ingest_worker.GraphitiClient')
@patch('app.workers.graphiti_ingest_worker.SessionLocal')
async def test_process_memory_success(mock_session_local, mock_graphiti_client):
    mock_db = Mock()
    mock_session_local.return_value = mock_db

    mock_memory = Mock()
    mock_memory.id = 'test-memory-123'
    mock_memory.title = 'Test Memory'
    mock_memory.content = 'Test content'
    mock_memory.group_id = 'default'
    mock_memory.created_at = Mock()

    mock_repository = Mock()
    mock_repository.get.return_value = mock_memory

    mock_client_instance = Mock()
    mock_client_instance.add_memory_in_chunks = AsyncMock(return_value=['episode-uuid-1', 'episode-uuid-2'])
    mock_graphiti_client.return_value = mock_client_instance
    mock_scheduler = Mock()

    worker = GraphitiIngestWorker(profile_refresh_scheduler=mock_scheduler)
    worker.repository = mock_repository

    await worker._process_memory('test-memory-123')

    mock_repository.get.assert_called_once_with(mock_db, 'test-memory-123')
    mock_client_instance.add_memory_in_chunks.assert_called_once()
    assert mock_memory.graph_status == 'added'
    assert mock_memory.graph_episode_uuid == 'episode-uuid-1'
    assert mock_memory.graph_added_at is not None
    assert mock_memory.graph_error is None
    mock_scheduler.request_refresh.assert_called_once_with(reason='graph_ingest_success')
    mock_db.commit.assert_called()
    mock_db.close.assert_called_once()


@pytest.mark.anyio
@patch('app.workers.graphiti_ingest_worker.GraphitiClient')
@patch('app.workers.graphiti_ingest_worker.SessionLocal')
async def test_process_memory_failure(mock_session_local, mock_graphiti_client):
    mock_db = Mock()
    mock_session_local.return_value = mock_db

    mock_memory = Mock()
    mock_memory.id = 'test-memory-123'
    mock_memory.title = 'Test Memory'
    mock_memory.content = 'Test content'
    mock_memory.group_id = 'default'
    mock_memory.created_at = Mock()

    mock_repository = Mock()
    mock_repository.get.return_value = mock_memory

    mock_client_instance = Mock()
    error_message = 'Graphiti connection failed'
    mock_client_instance.add_memory_in_chunks = AsyncMock(side_effect=Exception(error_message))
    mock_graphiti_client.return_value = mock_client_instance

    worker = GraphitiIngestWorker()
    worker.repository = mock_repository

    await worker._process_memory('test-memory-123')

    assert mock_memory.graph_status == 'failed'
    assert mock_memory.graph_error == error_message
    mock_db.commit.assert_called()
    mock_db.close.assert_called_once()


@pytest.mark.anyio
@patch('app.workers.graphiti_ingest_worker.GraphitiClient')
@patch('app.workers.graphiti_ingest_worker.SessionLocal')
async def test_process_memory_not_found(mock_session_local, mock_graphiti_client):
    mock_db = Mock()
    mock_session_local.return_value = mock_db

    mock_repository = Mock()
    mock_repository.get.return_value = None

    mock_client_instance = Mock()
    mock_client_instance.add_memory_in_chunks = AsyncMock()
    mock_graphiti_client.return_value = mock_client_instance

    worker = GraphitiIngestWorker()
    worker.repository = mock_repository

    await worker._process_memory('nonexistent-memory')

    mock_client_instance.add_memory_in_chunks.assert_not_called()
    mock_db.close.assert_called_once()


@pytest.mark.anyio
@patch('app.workers.graphiti_ingest_worker.GraphitiClient')
async def test_add_memory_episode_with_retry_uses_chunk_title_and_content(mock_graphiti_client):
    mock_client_instance = Mock()
    mock_client_instance.add_memory_episode = AsyncMock(return_value='episode-uuid-456')
    mock_graphiti_client.return_value = mock_client_instance

    worker = GraphitiIngestWorker()
    memory = Mock()
    memory.id = 'memory-1'
    memory.group_id = 'default'
    memory.created_at = Mock()
    memory.graph_error = None
    db = Mock()

    episode_uuid = await worker._add_memory_episode_with_retry(
        db=db,
        memory=memory,
        title='标题 (1/2)',
        content='分段内容',
    )

    assert episode_uuid == 'episode-uuid-456'
    mock_client_instance.add_memory_episode.assert_awaited_once_with(
        memory_id='memory-1',
        title='标题 (1/2)',
        content='分段内容',
        group_id='default',
        created_at=memory.created_at,
    )
