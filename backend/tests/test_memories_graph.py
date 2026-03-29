from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app import dependencies


@pytest.fixture
def mock_worker():
    """Mock the GraphitiIngestWorker for testing."""
    worker = MagicMock()
    worker.enqueue = AsyncMock()
    return worker


@pytest.fixture
def client_with_worker(mock_worker, monkeypatch):
    """Create test client with mocked worker."""
    monkeypatch.setattr('app.dependencies.graphiti_worker', mock_worker)
    return TestClient(app)


def test_add_memory_to_graph(client_with_worker, mock_worker):
    """Test adding a single memory to the knowledge graph."""
    client = client_with_worker
    
    # Create a memory first
    create_response = client.post(
        '/api/memories',
        json={
            'title': 'Test Memory',
            'content': 'This is a test memory for graph ingestion.',
            'group_id': 'default',
            'title_status': 'ready',
        },
    )
    assert create_response.status_code == 201
    memory_id = create_response.json()['id']
    
    # Add to graph
    response = client.post(f'/api/memories/{memory_id}/add-to-graph')
    
    assert response.status_code == 202
    data = response.json()
    assert data['message'] == 'Memory queued for knowledge graph ingestion'
    assert data['memory_id'] == memory_id
    assert data['graph_status'] == 'pending'
    
    # Verify worker was called
    mock_worker.enqueue.assert_called_once_with(memory_id)


def test_add_memory_to_graph_not_found(client_with_worker):
    """Test adding non-existent memory to graph returns 404."""
    client = client_with_worker
    
    response = client.post('/api/memories/nonexistent-id/add-to-graph')
    
    assert response.status_code == 404


def test_batch_add_to_graph(client_with_worker, mock_worker):
    """Test batch adding memories to the knowledge graph."""
    client = client_with_worker
    
    # Create multiple memories
    memory_ids = []
    for i in range(3):
        create_response = client.post(
            '/api/memories',
            json={
                'title': f'Test Memory {i}',
                'content': f'Content {i}',
                'group_id': 'default',
                'title_status': 'ready',
            },
        )
        assert create_response.status_code == 201
        memory_ids.append(create_response.json()['id'])
    
    # Batch add to graph
    response = client.post(
        '/api/memories/batch-add-to-graph',
        json={'memory_ids': memory_ids},
    )
    
    assert response.status_code == 202
    data = response.json()
    assert data['queued_count'] == 3
    assert set(data['memory_ids']) == set(memory_ids)
    assert '3 memories queued' in data['message']
    
    # Verify worker was called for each memory
    assert mock_worker.enqueue.call_count == 3


def test_get_graph_status(client_with_worker):
    """Test getting graph status for a memory."""
    client = client_with_worker
    
    # Create a memory
    create_response = client.post(
        '/api/memories',
        json={
            'title': 'Status Test',
            'content': 'Testing status endpoint',
            'group_id': 'default',
            'title_status': 'ready',
        },
    )
    assert create_response.status_code == 201
    memory_id = create_response.json()['id']
    
    # Get graph status
    response = client.get(f'/api/memories/{memory_id}/graph-status')
    
    assert response.status_code == 200
    data = response.json()
    assert data['memory_id'] == memory_id
    assert data['graph_status'] == 'not_added'
    assert data['graph_episode_uuid'] is None
    assert data['graph_added_at'] is None
    assert data['graph_error'] is None


def test_get_graph_status_not_found(client_with_worker):
    """Test getting graph status for non-existent memory returns 404."""
    client = client_with_worker
    
    response = client.get('/api/memories/nonexistent-id/graph-status')
    
    assert response.status_code == 404
