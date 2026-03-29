"""Test title generation functionality."""

import asyncio
import httpx

BASE_URL = 'http://localhost:8000'


async def test_title_generation():
    """Test creating a memory without title and watching it get generated."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create memory without title
        print('Creating memory without title...')
        form_data = {
            'title': '',  # Empty title should trigger generation
            'content': '这是一篇关于 Python 异步编程的文章。asyncio 是 Python 的标准库,提供了编写异步代码的工具。通过使用 async/await 语法,我们可以编写高效的并发程序。',
            'group_id': 'test',
        }

        response = await client.post(f'{BASE_URL}/api/uploads/memories', data=form_data)
        print(f'Status: {response.status_code}')
        memory = response.json()
        memory_id = memory['id']
        print(f'Memory created: {memory_id}')
        print(f'Initial title: {memory["title"]}')
        print(f'Initial title_status: {memory["title_status"]}')

        # Poll for title generation
        print('\nPolling for title generation...')
        for i in range(12):  # Poll for up to 60 seconds
            await asyncio.sleep(5)
            response = await client.get(f'{BASE_URL}/api/memories?keyword=')
            memories = response.json()

            # Find our memory
            our_memory = next((m for m in memories if m['id'] == memory_id), None)
            if our_memory:
                print(
                    f'[{i*5}s] Title: {our_memory["title"]}, Status: {our_memory["title_status"]}'
                )

                if our_memory['title_status'] == 'ready':
                    print(f'\n✅ Title generated successfully: {our_memory["title"]}')
                    return
                elif our_memory['title_status'] == 'failed':
                    print('\n❌ Title generation failed')
                    return

        print('\n⏱️ Timeout waiting for title generation')


if __name__ == '__main__':
    asyncio.run(test_title_generation())
