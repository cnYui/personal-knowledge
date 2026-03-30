"""
Test script to measure knowledge graph processing time.
"""

import asyncio
import time

import httpx


async def test_processing_time():
    """Test how long it takes to process a memory into the knowledge graph."""
    async with httpx.AsyncClient() as client:
        # Get memories
        response = await client.get('http://localhost:8000/api/memories')
        memories = response.json()
        
        if not memories:
            print('⚠️  No memories found')
            return
        
        memory = memories[0]
        memory_id = memory['id']
        
        print(f'Testing with memory: {memory["title"]}')
        print(f'Content length: {len(memory["content"])} characters')
        print('-' * 80)
        
        # Check initial status
        print(f'Initial graph status: {memory.get("graph_status", "none")}')
        
        # If already added, we can't test processing time
        if memory.get('graph_status') == 'added':
            print('✅ Memory already in graph')
            print(f'Episode UUID: {memory.get("graph_episode_uuid")}')
            return
        
        # Add to graph and measure time
        print('\n⏱️  Starting to add to graph...')
        start_time = time.time()
        
        response = await client.post(
            f'http://localhost:8000/api/memories/{memory_id}/add-to-graph',
            timeout=60.0,
        )
        
        if response.status_code != 202:
            print(f'❌ Failed to queue: {response.status_code}')
            return
        
        print('✅ Queued successfully')
        
        # Poll for completion
        max_wait = 120  # 2 minutes max
        poll_interval = 2  # Check every 2 seconds
        elapsed = 0
        
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            
            response = await client.get(
                f'http://localhost:8000/api/memories/{memory_id}/graph-status'
            )
            
            if response.status_code == 200:
                status_data = response.json()
                current_status = status_data['graph_status']
                
                if current_status == 'added':
                    end_time = time.time()
                    total_time = end_time - start_time
                    print(f'\n✅ Processing complete!')
                    print(f'Total time: {total_time:.2f} seconds')
                    print(f'Episode UUID: {status_data["graph_episode_uuid"]}')
                    return
                elif current_status == 'failed':
                    print(f'\n❌ Processing failed: {status_data.get("graph_error")}')
                    return
                else:
                    print(f'⏳ Still processing... ({elapsed}s elapsed, status: {current_status})')
        
        print(f'\n⚠️  Timeout after {max_wait} seconds')


if __name__ == '__main__':
    asyncio.run(test_processing_time())
