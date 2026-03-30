"""
Check memory graph status.
"""

import asyncio

import httpx


async def check_status():
    """Check memory graph status."""
    async with httpx.AsyncClient() as client:
        # Get memories
        response = await client.get('http://localhost:8000/api/memories')
        memories = response.json()
        
        print('Memory Graph Status:')
        print('-' * 80)
        for memory in memories:
            print(f'ID: {memory["id"]}')
            print(f'Title: {memory["title"]}')
            print(f'Graph Status: {memory.get("graph_status", "none")}')
            print(f'Graph Episode UUID: {memory.get("graph_episode_uuid", "none")}')
            print('-' * 80)


if __name__ == '__main__':
    asyncio.run(check_status())
