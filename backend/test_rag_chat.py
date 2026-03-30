"""
测试 RAG 聊天功能
"""

import requests

BASE_URL = 'http://localhost:8000'


def test_chat():
    """测试聊天功能"""
    print('🤖 测试 RAG 聊天功能\n')
    print('=' * 60)

    # 测试问题列表
    questions = [
        '垃圾收集的时间表是什么？',
        '星期一收集什么垃圾？',
        '可燃垃圾在哪些日子收集？',
        '金属罐什么时候收集？',
    ]

    for i, question in enumerate(questions, 1):
        print(f'\n问题 {i}: {question}')
        print('-' * 60)

        try:
            response = requests.post(
                f'{BASE_URL}/api/chat/messages',
                json={'message': question},
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()

            print(f'\n回答:\n{result["answer"]}\n')

            if result['references']:
                print(f'参考信息 ({len(result["references"])} 条):')
                for ref in result['references'][:5]:  # 显示前5条
                    if ref['type'] == 'entity':
                        print(f'  - 实体: {ref["name"]}')
                        if ref.get('summary'):
                            print(f'    描述: {ref["summary"][:100]}...')
                    elif ref['type'] == 'relationship':
                        print(f'  - 关系: {ref["fact"][:100]}...')
            else:
                print('参考信息: 无')

        except Exception as e:
            print(f'❌ 错误: {e}')

    print('\n' + '=' * 60)
    print('✅ 测试完成')


if __name__ == '__main__':
    test_chat()
