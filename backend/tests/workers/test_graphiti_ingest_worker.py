import pytest
from unittest.mock import Mock, patch, AsyncMock
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
    # Setup mocks
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
    mock_client_instance.add_memory_episode = AsyncMock(return_value='episode-uuid-456')
    mock_graphiti_client.return_value = mock_client_instance
    
    worker = GraphitiIngestWorker()
    worker.repository = mock_repository
    
    # Process memory
    await worker._process_memory('test-memory-123')
    
    # Verify
    mock_repository.get.assert_called_once_with(mock_db, 'test-memory-123')
    mock_client_instance.add_memory_episode.assert_called_once()
    assert mock_memory.graph_status == 'added'
    assert mock_memory.graph_episode_uuid == 'episode-uuid-456'
    assert mock_memory.graph_added_at is not None
    assert mock_memory.graph_error is None
    mock_db.commit.assert_called()
    mock_db.close.assert_called_once()



@pytest.mark.anyio
@patch('app.workers.graphiti_ingest_worker.GraphitiClient')
@patch('app.workers.graphiti_ingest_worker.SessionLocal')
async def test_process_memory_failure(mock_session_local, mock_graphiti_client):
    # Setup mocks
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
    mock_client_instance.add_memory_episode = AsyncMock(side_effect=Exception(error_message))
    mock_graphiti_client.return_value = mock_client_instance
    
    worker = GraphitiIngestWorker()
    worker.repository = mock_repository
    
    # Process memory (should handle exception)
    await worker._process_memory('test-memory-123')
    
    # Verify error handling
    assert mock_memory.graph_status == 'failed'
    assert mock_memory.graph_error == error_message
    mock_db.commit.assert_called()
    mock_db.close.assert_called_once()


@pytest.mark.anyio
@patch('app.workers.graphiti_ingest_worker.GraphitiClient')
@patch('app.workers.graphiti_ingest_worker.SessionLocal')
async def test_process_memory_not_found(mock_session_local, mock_graphiti_client):
    # Setup mocks
    mock_db = Mock()
    mock_session_local.return_value = mock_db
    
    mock_repository = Mock()
    mock_repository.get.return_value = None
    
    mock_client_instance = Mock()
    mock_graphiti_client.return_value = mock_client_instance
    
    worker = GraphitiIngestWorker()
    worker.repository = mock_repository
    
    # Process memory that doesn't exist
    await worker._process_memory('nonexistent-memory')
    
    # Verify no episode was added
    mock_client_instance.add_memory_episode.assert_not_called()
    mock_db.close.assert_called_once()
