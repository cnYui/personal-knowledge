"""测试新的 RAG 端点（不保存到数据库）"""

import requests

BASE_URL = 'http://localhost:8000'

print('🧪 测试 RAG 端点\n')

# 测试 RAG 查询
response = requests.post(
    f'{BASE_URL}/api/chat/rag',
    json={'message': '星期一收集什么垃圾？'},
    timeout=30,
)

print(f'状态码: {response.status_code}')

if response.status_code == 200:
    result = response.json()
    print(f'\n✅ 成功！')
    print(f'\n回答:\n{result["answer"]}')
    print(f'\n引用数量: {len(result["references"])}')
    
    if result['references']:
        print('\n引用示例:')
        for i, ref in enumerate(result['references'][:3], 1):
            print(f'{i}. 类型: {ref["type"]}')
            if ref.get('fact'):
                print(f'   内容: {ref["fact"][:80]}...')
else:
    print(f'\n❌ 失败: {response.text}')
