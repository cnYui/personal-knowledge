"""快速测试聊天功能"""

import requests

BASE_URL = 'http://localhost:8000'

# 测试聊天
response = requests.post(
    f'{BASE_URL}/api/chat/messages',
    json={'message': '星期一收集什么垃圾？'},
    timeout=30,
)

print('状态码:', response.status_code)
if response.status_code == 200:
    result = response.json()
    print('\n回答:')
    print(result['answer'])
    print(f'\n引用数量: {len(result["references"])}')
else:
    print('错误:', response.text)
