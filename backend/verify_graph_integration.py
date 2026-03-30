"""
验证知识图谱集成是否正常工作
"""

import asyncio
import time

import requests

BASE_URL = 'http://localhost:8000'


def create_test_memory():
    """创建一个测试记忆"""
    print('📝 创建测试记忆...')
    response = requests.post(
        f'{BASE_URL}/api/memories',
        json={
            'title': '测试知识图谱集成',
            'content': '这是一个测试记忆，用于验证 Graphiti 知识图谱集成是否正常工作。包含实体：Python、FastAPI、Neo4j。',
            'group_id': 'test',
        },
    )
    response.raise_for_status()
    memory = response.json()
    print(f'✅ 记忆已创建: {memory["id"]}')
    print(f'   状态: {memory["graph_status"]}')
    return memory


def add_to_graph(memory_id):
    """将记忆添加到知识图谱"""
    print(f'\n🔄 将记忆添加到知识图谱...')
    response = requests.post(f'{BASE_URL}/api/memories/{memory_id}/add-to-graph')
    response.raise_for_status()
    result = response.json()
    print(f'✅ {result["message"]}')
    print(f'   状态: {result["graph_status"]}')
    return result


def check_status(memory_id):
    """检查知识图谱处理状态"""
    response = requests.get(f'{BASE_URL}/api/memories/{memory_id}/graph-status')
    response.raise_for_status()
    return response.json()


def wait_for_completion(memory_id, timeout=60):
    """等待知识图谱处理完成"""
    print(f'\n⏳ 等待处理完成（最多 {timeout} 秒）...')
    start_time = time.time()

    while time.time() - start_time < timeout:
        status = check_status(memory_id)
        current_status = status['graph_status']

        if current_status == 'added':
            print(f'\n✅ 处理完成！')
            print(f'   Episode UUID: {status["graph_episode_uuid"]}')
            print(f'   完成时间: {status["graph_added_at"]}')
            return True
        elif current_status == 'failed':
            print(f'\n❌ 处理失败！')
            print(f'   错误信息: {status["graph_error"]}')
            return False
        else:
            elapsed = int(time.time() - start_time)
            print(f'   [{elapsed}s] 状态: {current_status}', end='\r')
            time.sleep(2)

    print(f'\n⚠️  超时！最终状态: {current_status}')
    return False


def main():
    """主函数"""
    print('🚀 开始验证知识图谱集成\n')
    print('=' * 60)

    try:
        # 1. 创建测试记忆
        memory = create_test_memory()

        # 2. 添加到知识图谱
        add_to_graph(memory['id'])

        # 3. 等待处理完成
        success = wait_for_completion(memory['id'])

        print('\n' + '=' * 60)
        if success:
            print('🎉 验证成功！知识图谱集成正常工作。')
        else:
            print('⚠️  验证未完全成功，请检查日志。')

    except Exception as e:
        print(f'\n❌ 验证失败: {e}')
        import traceback

        traceback.print_exc()


if __name__ == '__main__':
    main()
