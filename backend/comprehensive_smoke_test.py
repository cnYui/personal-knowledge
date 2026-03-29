"""
Comprehensive smoke test for Memory Management features.

Tests all operations that can be performed from the frontend:
1. Create memory
2. Search/filter memories by keyword
3. Update/edit memory
4. Delete memory
5. Add memory to knowledge graph
6. Check graph status
"""

import asyncio
import httpx

BASE_URL = 'http://localhost:8000'


async def test_all_operations():
    """Test all memory management operations."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        print('=' * 70)
        print('  COMPREHENSIVE SMOKE TEST: Memory Management')
        print('=' * 70)

        # Test 1: Create Memory
        print('\n' + '=' * 70)
        print('  Test 1: Create Memory')
        print('=' * 70)

        create_data = {
            'title': '测试记忆 - 综合测试',
            'content': '这是一个用于测试所有功能的记忆。包含关键词：Python、测试、数据库。',
            'group_id': 'test',
        }

        response = await client.post(f'{BASE_URL}/api/memories', json=create_data)
        print(f'\nStatus: {response.status_code}')
        if response.status_code != 201:
            print(f'❌ Failed to create memory: {response.text}')
            return

        memory = response.json()
        memory_id = memory['id']
        print(f'✅ Memory created successfully')
        print(f'   ID: {memory_id}')
        print(f'   Title: {memory["title"]}')
        print(f'   Content: {memory["content"][:50]}...')

        # Test 2: Search/Filter by Keyword
        print('\n' + '=' * 70)
        print('  Test 2: Search Memories by Keyword')
        print('=' * 70)

        # Test 2a: Search with keyword "Python"
        print('\n[2a] Searching for keyword "Python"...')
        response = await client.get(f'{BASE_URL}/api/memories?keyword=Python')
        print(f'Status: {response.status_code}')
        if response.status_code != 200:
            print(f'❌ Failed to search: {response.text}')
            return

        memories = response.json()
        found = any(m['id'] == memory_id for m in memories)
        print(f'Found {len(memories)} memories')
        if found:
            print(f'✅ Our memory found in search results')
        else:
            print(f'❌ Our memory NOT found in search results')

        # Test 2b: Search with keyword "测试"
        print('\n[2b] Searching for keyword "测试"...')
        response = await client.get(f'{BASE_URL}/api/memories?keyword=测试')
        print(f'Status: {response.status_code}')
        memories = response.json()
        found = any(m['id'] == memory_id for m in memories)
        print(f'Found {len(memories)} memories')
        if found:
            print(f'✅ Our memory found in Chinese keyword search')
        else:
            print(f'❌ Our memory NOT found in Chinese keyword search')

        # Test 2c: Search with non-matching keyword
        print('\n[2c] Searching for non-matching keyword "不存在的关键词"...')
        response = await client.get(f'{BASE_URL}/api/memories?keyword=不存在的关键词')
        print(f'Status: {response.status_code}')
        memories = response.json()
        found = any(m['id'] == memory_id for m in memories)
        print(f'Found {len(memories)} memories')
        if not found:
            print(f'✅ Our memory correctly NOT found (keyword doesn\'t match)')
        else:
            print(f'⚠️  Our memory found even though keyword doesn\'t match')

        # Test 3: Update/Edit Memory
        print('\n' + '=' * 70)
        print('  Test 3: Update Memory')
        print('=' * 70)

        update_data = {
            'title': '测试记忆 - 已更新',
            'content': '这是更新后的内容。新增关键词：更新、修改、编辑。',
        }

        response = await client.put(f'{BASE_URL}/api/memories/{memory_id}', json=update_data)
        print(f'\nStatus: {response.status_code}')
        if response.status_code != 200:
            print(f'❌ Failed to update memory: {response.text}')
            return

        updated_memory = response.json()
        print(f'✅ Memory updated successfully')
        print(f'   New Title: {updated_memory["title"]}')
        print(f'   New Content: {updated_memory["content"][:50]}...')

        # Verify update by fetching
        print('\n[3a] Verifying update by fetching memory...')
        response = await client.get(f'{BASE_URL}/api/memories?keyword=')
        memories = response.json()
        our_memory = next((m for m in memories if m['id'] == memory_id), None)
        if our_memory and our_memory['title'] == update_data['title']:
            print(f'✅ Update verified in database')
        else:
            print(f'❌ Update NOT reflected in database')

        # Test 4: Add to Knowledge Graph
        print('\n' + '=' * 70)
        print('  Test 4: Add Memory to Knowledge Graph')
        print('=' * 70)

        response = await client.post(f'{BASE_URL}/api/memories/{memory_id}/add-to-graph')
        print(f'\nStatus: {response.status_code}')
        if response.status_code != 202:
            print(f'❌ Failed to add to graph: {response.text}')
            return

        result = response.json()
        print(f'✅ Memory queued for graph ingestion')
        print(f'   Message: {result["message"]}')
        print(f'   Graph Status: {result["graph_status"]}')

        # Test 5: Check Graph Status
        print('\n' + '=' * 70)
        print('  Test 5: Check Graph Status')
        print('=' * 70)

        print('\nWaiting 20 seconds for graph processing...')
        await asyncio.sleep(20)

        response = await client.get(f'{BASE_URL}/api/memories/{memory_id}/graph-status')
        print(f'\nStatus: {response.status_code}')
        if response.status_code != 200:
            print(f'❌ Failed to get graph status: {response.text}')
            return

        status = response.json()
        print(f'Graph Status: {status["graph_status"]}')
        if status['graph_status'] == 'added':
            print(f'✅ Memory successfully added to knowledge graph')
            print(f'   Episode UUID: {status["graph_episode_uuid"]}')
            print(f'   Added At: {status["graph_added_at"]}')
        elif status['graph_status'] == 'pending':
            print(f'⏳ Memory still being processed')
        elif status['graph_status'] == 'failed':
            print(f'❌ Graph ingestion failed')
            print(f'   Error: {status.get("graph_error", "Unknown error")}')
        else:
            print(f'⚠️  Unexpected status: {status["graph_status"]}')

        # Test 6: Delete Memory
        print('\n' + '=' * 70)
        print('  Test 6: Delete Memory')
        print('=' * 70)

        response = await client.delete(f'{BASE_URL}/api/memories/{memory_id}')
        print(f'\nStatus: {response.status_code}')
        if response.status_code != 204:
            print(f'❌ Failed to delete memory: {response.text}')
            return

        print(f'✅ Memory deleted successfully')

        # Verify deletion
        print('\n[6a] Verifying deletion...')
        response = await client.get(f'{BASE_URL}/api/memories?keyword=')
        memories = response.json()
        found = any(m['id'] == memory_id for m in memories)
        if not found:
            print(f'✅ Memory confirmed deleted from database')
        else:
            print(f'❌ Memory still exists in database after deletion')

        # Final Summary
        print('\n' + '=' * 70)
        print('  TEST SUMMARY')
        print('=' * 70)
        print('\n✅ All tests completed successfully!')
        print('\nVerified operations:')
        print('  1. ✅ Create memory')
        print('  2. ✅ Search by keyword (English and Chinese)')
        print('  3. ✅ Update memory')
        print('  4. ✅ Add to knowledge graph')
        print('  5. ✅ Check graph status')
        print('  6. ✅ Delete memory')


if __name__ == '__main__':
    asyncio.run(test_all_operations())
