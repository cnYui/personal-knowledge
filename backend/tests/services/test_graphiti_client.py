from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from app.services.graphiti_client import GraphIngestChunkLimitError, GraphitiClient


@pytest.mark.anyio
async def test_graphiti_client_initialization_is_lazy():
    with patch('app.services.graphiti_client.Graphiti') as mock_graphiti:
        client = GraphitiClient()

        assert client.client is None

        async def fake_close():
            return None

        mock_graphiti.return_value.close = fake_close
        await client._ensure_runtime_client()
        mock_graphiti.assert_called_once()
        assert client.client is mock_graphiti.return_value


@pytest.mark.anyio
async def test_add_memory_episode():
    with patch('app.services.graphiti_client.Graphiti') as mock_graphiti_class:
        mock_client = Mock()
        mock_graphiti_class.return_value = mock_client

        mock_result = Mock()
        mock_result.episode.uuid = 'test-episode-uuid'

        async def mock_add_episode(*args, **kwargs):
            return mock_result

        mock_client.add_episode = mock_add_episode
        mock_client.close = mock_add_episode

        client = GraphitiClient()

        episode_uuid = await client.add_memory_episode(
            memory_id='mem-123',
            title='Test Memory',
            content='Test content',
            group_id='default',
            created_at=datetime(2026, 3, 29, 10, 0, 0),
        )

        assert episode_uuid == 'test-episode-uuid'


def test_split_memory_content_returns_single_chunk_for_short_text():
    client = GraphitiClient()
    short_text = '这是一个较短的知识片段。'

    chunks = client.split_memory_content(short_text)

    assert chunks == [short_text]


def test_split_memory_content_splits_long_text_into_multiple_chunks():
    client = GraphitiClient()
    paragraph = '这是一段用于图谱构建的长文本。' * 180
    content = '\n\n'.join([paragraph, paragraph, paragraph])

    chunks = client.split_memory_content(content)

    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)
    assert all(len(chunk) <= client.max_chunk_length for chunk in chunks)


def test_split_memory_content_force_splits_single_large_paragraph():
    client = GraphitiClient()
    oversized_paragraph = 'A' * (client.max_chunk_length * 2 + 100)

    chunks = client.split_memory_content(oversized_paragraph)

    assert len(chunks) == 3
    assert ''.join(chunks) == oversized_paragraph


def test_split_memory_content_raises_when_chunk_count_exceeds_limit():
    client = GraphitiClient()
    repeated = ('A' * client.max_chunk_length) + '\n\n'
    content = repeated * (client.max_chunk_count + 1)

    with pytest.raises(GraphIngestChunkLimitError):
        client.split_memory_content(content)


@pytest.mark.anyio
async def test_add_memory_in_chunks_uses_chunk_suffix_for_long_text():
    client = GraphitiClient()
    paragraph = '长文段落。' * 300
    content = '\n\n'.join([paragraph, paragraph])
    calls: list[tuple[str, str]] = []

    async def episode_adder(chunk_title: str, chunk_content: str) -> str:
        calls.append((chunk_title, chunk_content))
        return f'uuid-{len(calls)}'

    episode_uuids = await client.add_memory_in_chunks(
        memory_id='memory-1',
        title='测试标题',
        content=content,
        group_id='default',
        created_at=datetime(2026, 4, 5, 10, 0, 0),
        episode_adder=episode_adder,
    )

    assert len(calls) == len(episode_uuids)
    assert len(calls) > 1
    assert calls[0][0] == f'测试标题 (1/{len(calls)})'
    assert calls[-1][0] == f'测试标题 ({len(calls)}/{len(calls)})'


@pytest.mark.anyio
async def test_add_memory_in_chunks_keeps_original_title_for_short_text():
    client = GraphitiClient()
    calls: list[tuple[str, str]] = []

    async def episode_adder(chunk_title: str, chunk_content: str) -> str:
        calls.append((chunk_title, chunk_content))
        return 'uuid-1'

    episode_uuids = await client.add_memory_in_chunks(
        memory_id='memory-2',
        title='短文标题',
        content='短文内容',
        group_id='default',
        created_at=datetime(2026, 4, 5, 10, 0, 0),
        episode_adder=episode_adder,
    )

    assert episode_uuids == ['uuid-1']
    assert calls == [('短文标题', '短文内容')]
