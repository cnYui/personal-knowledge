"""Verify database is empty."""

import asyncio
import httpx

async def verify():
    async with httpx.AsyncClient() as client:
        response = await client.get('http://localhost:8000/api/memories?keyword=')
        memories = response.json()
        print(f'Total memories in database: {len(memories)}')
        if len(memories) == 0:
            print('✅ Database is empty and ready for real data')
        else:
            print(f'⚠️  Database still contains {len(memories)} memories')

if __name__ == '__main__':
    asyncio.run(verify())
