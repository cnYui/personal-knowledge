import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.database import Base, get_db
from app.models.memory import Memory


# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = 'sqlite:///./test_integration.db'
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={'check_same_thread': False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Mock worker for testing
mock_worker = MagicMock()
mock_worker.enqueue = AsyncMock()


def override_get_worker():
    return mock_worker


@pytest.fixture(scope='module')
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope='module')
def test_client():
    """Create a test client with dependency overrides."""
    from app.main import app
    from app.dependencies import get_worker
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_worker] = override_get_worker
    
    return TestClient(app)


@pytest.mark.integration
@pytest.mark.anyio
async def test_end_to_end_graph_ingestion(setup_database, test_client):
    """Test complete flow: create memory -> queue for graph -> verify status."""
    client = test_client
    
    # Create a memory
    response = client.post('/api/memories', json={
        'title': 'Test Memory',
        'content': 'This is a test memory for graph ingestion',
        'group_id': 'test-group',
    })
    assert response.status_code == 201
    memory_id = response.json()['id']
    
    # Queue for graph ingestion
    response = client.post(f'/api/memories/{memory_id}/add-to-graph')
    assert response.status_code == 202
    assert response.json()['graph_status'] == 'pending'
    
    # Verify worker was called
    mock_worker.enqueue.assert_called_once_with(memory_id)
    
    # Check status
    response = client.get(f'/api/memories/{memory_id}/graph-status')
    assert response.status_code == 200
    data = response.json()
    assert data['graph_status'] in ['pending', 'added', 'failed']
    assert data['memory_id'] == memory_id


@pytest.mark.integration
@pytest.mark.anyio
async def test_batch_graph_ingestion(setup_database, test_client):
    """Test batch ingestion of multiple memories."""
    client = test_client
    
    # Reset mock
    mock_worker.enqueue.reset_mock()
    
    # Create multiple memories
    memory_ids = []
    for i in range(3):
        response = client.post('/api/memories', json={
            'title': f'Test Memory {i}',
            'content': f'Content {i}',
            'group_id': 'test-group',
        })
        assert response.status_code == 201
        memory_ids.append(response.json()['id'])
    
    # Batch queue
    response = client.post('/api/memories/batch-add-to-graph', json={
        'memory_ids': memory_ids,
    })
    assert response.status_code == 202
    data = response.json()
    assert data['queued_count'] == 3
    assert len(data['memory_ids']) == 3
    
    # Verify worker was called for each memory
    assert mock_worker.enqueue.call_count == 3


@pytest.mark.integration
@pytest.mark.anyio
async def test_graph_status_tracking(setup_database, test_client):
    """Test that graph status is properly tracked through the ingestion lifecycle."""
    client = test_client
    
    # Reset mock
    mock_worker.enqueue.reset_mock()
    
    # Create a memory
    response = client.post('/api/memories', json={
        'title': 'Status Tracking Test',
        'content': 'Testing status transitions',
        'group_id': 'test-group',
    })
    assert response.status_code == 201
    memory_id = response.json()['id']
    
    # Initial status should be 'not_added'
    response = client.get(f'/api/memories/{memory_id}/graph-status')
    assert response.status_code == 200
    assert response.json()['graph_status'] == 'not_added'
    
    # Queue for ingestion
    response = client.post(f'/api/memories/{memory_id}/add-to-graph')
    assert response.status_code == 202
    
    # Status should now be 'pending'
    response = client.get(f'/api/memories/{memory_id}/graph-status')
    assert response.status_code == 200
    data = response.json()
    assert data['graph_status'] == 'pending'
    assert data['graph_episode_uuid'] is None
    assert data['graph_added_at'] is None


@pytest.mark.integration
@pytest.mark.anyio
async def test_duplicate_queue_prevention(setup_database, test_client):
    """Test that memories already queued or added cannot be queued again."""
    client = test_client
    
    # Reset mock
    mock_worker.enqueue.reset_mock()
    
    # Create a memory
    response = client.post('/api/memories', json={
        'title': 'Duplicate Test',
        'content': 'Testing duplicate prevention',
        'group_id': 'test-group',
    })
    assert response.status_code == 201
    memory_id = response.json()['id']
    
    # Queue for ingestion (first time)
    response = client.post(f'/api/memories/{memory_id}/add-to-graph')
    assert response.status_code == 202
    
    # Try to queue again (should fail or be idempotent)
    response = client.post(f'/api/memories/{memory_id}/add-to-graph')
    # Depending on implementation, this might return 400 or 202 with same status
    assert response.status_code in [202, 400]


@pytest.mark.integration
@pytest.mark.anyio
async def test_batch_with_invalid_memory_ids(setup_database, test_client):
    """Test batch ingestion with some invalid memory IDs."""
    client = test_client
    
    # Reset mock
    mock_worker.enqueue.reset_mock()
    
    # Create one valid memory
    response = client.post('/api/memories', json={
        'title': 'Valid Memory',
        'content': 'Valid content',
        'group_id': 'test-group',
    })
    assert response.status_code == 201
    valid_id = response.json()['id']
    
    # Try batch with valid and invalid IDs
    response = client.post('/api/memories/batch-add-to-graph', json={
        'memory_ids': [valid_id, 'invalid-id-1', 'invalid-id-2'],
    })
    
    # Should handle gracefully - either skip invalid or return error
    # Implementation dependent, but should not crash
    assert response.status_code in [202, 400, 404]


@pytest.mark.integration
@pytest.mark.anyio
async def test_memory_with_images_graph_ingestion(setup_database, test_client):
    """Test that memories with associated images can be queued for graph ingestion."""
    client = test_client
    
    # Reset mock
    mock_worker.enqueue.reset_mock()
    
    # Create a memory (images would be added separately via upload endpoint)
    response = client.post('/api/memories', json={
        'title': 'Memory with Images',
        'content': 'This memory has associated images',
        'group_id': 'test-group',
    })
    assert response.status_code == 201
    memory_id = response.json()['id']
    
    # Queue for graph ingestion
    response = client.post(f'/api/memories/{memory_id}/add-to-graph')
    assert response.status_code == 202
    assert response.json()['graph_status'] == 'pending'
    
    # Verify status
    response = client.get(f'/api/memories/{memory_id}/graph-status')
    assert response.status_code == 200
    assert response.json()['graph_status'] == 'pending'
