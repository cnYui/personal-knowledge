"""Quick test for single memory ingestion."""

import asyncio
import httpx

BASE_URL = 'http://localhost:8000'


async def test_single_memory():
    """Test creating and ingesting a single memory."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create memory
        print('Creating memory...')
        response = await client.post(
            f'{BASE_URL}/api/memories',
            json={
                'title': '测试记忆',
                'content': '这是一个简单的测试记忆,用于验证知识图谱集成。',
                'group_id': 'test',
            },
        )
        print(f'Status: {response.status_code}')
        memory = response.json()
        memory_id = memory['id']
        print(f'Memory created: {memory_id}')

        # Add to graph
        print('\nAdding to graph...')
        response = await client.post(f'{BASE_URL}/api/memories/{memory_id}/add-to-graph')
        print(f'Status: {response.status_code}')
        print(f'Response: {response.json()}')

        # Wait and check status
        print('\nWaiting 20 seconds for processing...')
        await asyncio.sleep(20)

        response = await client.get(f'{BASE_URL}/api/memories/{memory_id}/graph-status')
        print(f'\nFinal status: {response.json()}')


if __name__ == '__main__':
    asyncio.run(test_single_memory())
