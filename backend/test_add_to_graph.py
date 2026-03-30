"""
Test script for add-to-graph API endpoint.
"""

import asyncio

import httpx


async def test_add_to_graph():
    """Test the add-to-graph endpoint."""
    async with httpx.AsyncClient() as client:
        # First, get list of memories
        response = await client.get('http://localhost:8000/api/memories')
        
        if response.status_code != 200:
            print(f'❌ Failed to get memories: {response.status_code}')
            return
        
        memories = response.json()
        
        if not memories:
            print('⚠️  No memories found in database')
            return
        
        # Test adding first memory to graph
        memory_id = memories[0]['id']
        print(f'Testing with memory ID: {memory_id}')
        print(f'Title: {memories[0]["title"]}')
        
        response = await client.post(
            f'http://localhost:8000/api/memories/{memory_id}/add-to-graph',
            timeout=30.0,
        )
        
        if response.status_code == 202:
            result = response.json()
            print('✅ Add to graph successful!')
            print(f'Message: {result["message"]}')
            print(f'Graph status: {result["graph_status"]}')
        else:
            print(f'❌ Request failed: {response.status_code}')
            print(response.text)


if __name__ == '__main__':
    asyncio.run(test_add_to_graph())
