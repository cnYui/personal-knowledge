"""Check status of recent memories."""

import asyncio
import httpx

BASE_URL = 'http://localhost:8000'


async def check_status():
    """Check status of all memories."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f'{BASE_URL}/api/memories?keyword=')
        memories = response.json()

        print(f'\nTotal memories: {len(memories)}\n')

        added_count = 0
        pending_count = 0
        failed_count = 0
        not_added_count = 0

        for memory in memories:
            status = memory['graph_status']
            if status == 'added':
                added_count += 1
                print(f'✅ {memory["title"][:30]:30} - ADDED (UUID: {memory["graph_episode_uuid"][:8]}...)')
            elif status == 'pending':
                pending_count += 1
                print(f'⏳ {memory["title"][:30]:30} - PENDING')
            elif status == 'failed':
                failed_count += 1
                error = memory.get('graph_error', 'Unknown error')[:50]
                print(f'❌ {memory["title"][:30]:30} - FAILED ({error}...)')
            else:
                not_added_count += 1

        print(f'\n📊 Summary:')
        print(f'   Added: {added_count}')
        print(f'   Pending: {pending_count}')
        print(f'   Failed: {failed_count}')
        print(f'   Not Added: {not_added_count}')


if __name__ == '__main__':
    asyncio.run(check_status())
