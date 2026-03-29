import pytest
from unittest.mock import Mock, patch
from app.services.graphiti_client import GraphitiClient


def test_graphiti_client_initialization():
    with patch('app.services.graphiti_client.Graphiti') as mock_graphiti:
        client = GraphitiClient()
        
        mock_graphiti.assert_called_once()
        assert client.client is not None



from datetime import datetime


@pytest.mark.anyio
async def test_add_memory_episode():
    with patch('app.services.graphiti_client.Graphiti') as mock_graphiti_class:
        mock_client = Mock()
        mock_graphiti_class.return_value = mock_client
        
        mock_result = Mock()
        mock_result.episode.uuid = 'test-episode-uuid'
        
        # Make add_episode an async mock
        async def mock_add_episode(*args, **kwargs):
            return mock_result
        
        mock_client.add_episode = mock_add_episode
        
        client = GraphitiClient()
        
        episode_uuid = await client.add_memory_episode(
            memory_id='mem-123',
            title='Test Memory',
            content='Test content',
            group_id='default',
            created_at=datetime(2026, 3, 29, 10, 0, 0),
        )
        
        assert episode_uuid == 'test-episode-uuid'
