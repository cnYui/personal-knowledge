"""
Test script for text optimization API.
"""

import asyncio

import httpx


async def test_text_optimization():
    """Test the text optimization endpoint."""
    test_text = """呃，我今天，就是，学习了那个，嗯，Python的那个，啊，架构设计。
    然后呢，我看到了，我...我看到了一个很好的，某种程度上来说，就是很好的例子。
    这个例子里面用到了，那个，界口设计，还有那个，不数的方案。
    大概花了，嗯，二十五分钟，学习了百分之十的内容，花了五块钱买的课程。"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            'http://localhost:8000/api/text/optimize',
            json={'text': test_text},
            timeout=30.0,
        )

        if response.status_code == 200:
            result = response.json()
            print('✅ Text optimization successful!')
            print(f'\n原始文本 ({result["original_length"]} 字符):')
            print(test_text)
            print(f'\n优化后文本 ({result["optimized_length"]} 字符):')
            print(result['optimized_text'])
        else:
            print(f'❌ Request failed: {response.status_code}')
            print(response.text)


if __name__ == '__main__':
    asyncio.run(test_text_optimization())
