"""
Script to inspect the knowledge graph content in Neo4j.
"""

import asyncio
from neo4j import AsyncGraphDatabase

from app.core.config import settings


async def inspect_graph():
    """Inspect the knowledge graph and display sample entities and relationships."""
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    
    try:
        async with driver.session() as session:
            print("=" * 80)
            print("知识图谱内容检查")
            print("=" * 80)
            
            # 1. 统计节点数量
            result = await session.run("MATCH (n) RETURN count(n) as count")
            record = await result.single()
            total_nodes = record['count']
            print(f"\n总节点数: {total_nodes}")
            
            # 2. 统计关系数量
            result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            record = await result.single()
            total_rels = record['count']
            print(f"总关系数: {total_rels}")
            
            # 3. 查看节点类型分布
            print("\n节点类型分布:")
            result = await session.run("""
                MATCH (n)
                RETURN labels(n) as labels, count(*) as count
                ORDER BY count DESC
            """)
            async for record in result:
                print(f"  {record['labels']}: {record['count']}")
            
            # 4. 查看关系类型分布
            print("\n关系类型分布:")
            result = await session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(*) as count
                ORDER BY count DESC
            """)
            async for record in result:
                print(f"  {record['type']}: {record['count']}")
            
            # 5. 查看示例实体节点（Entity）
            print("\n" + "=" * 80)
            print("示例实体节点 (前5个):")
            print("=" * 80)
            result = await session.run("""
                MATCH (n:Entity)
                RETURN n.uuid as uuid, n.name as name, n.summary as summary
                LIMIT 5
            """)
            async for record in result:
                print(f"\nUUID: {record['uuid']}")
                print(f"名称: {record['name']}")
                print(f"摘要: {record['summary']}")
                print("-" * 80)
            
            # 6. 查看示例关系（带完整信息）
            print("\n" + "=" * 80)
            print("示例实体关系 (前3个):")
            print("=" * 80)
            result = await session.run("""
                MATCH (source:Entity)-[r]->(target:Entity)
                RETURN 
                    source.name as source_name,
                    type(r) as rel_type,
                    target.name as target_name,
                    r.name as rel_name,
                    r.fact as fact,
                    r.created_at as created_at
                LIMIT 3
            """)
            async for record in result:
                print(f"\n源实体: {record['source_name']}")
                print(f"关系类型: {record['rel_type']}")
                print(f"关系名称: {record['rel_name']}")
                print(f"目标实体: {record['target_name']}")
                print(f"事实描述: {record['fact']}")
                print(f"创建时间: {record['created_at']}")
                print("-" * 80)
            
            # 7. 查看一个完整的三元组示例
            print("\n" + "=" * 80)
            print("完整三元组示例 (实体-关系-实体):")
            print("=" * 80)
            result = await session.run("""
                MATCH (source:Entity)-[r]->(target:Entity)
                RETURN 
                    source.uuid as source_uuid,
                    source.name as source_name,
                    source.summary as source_summary,
                    type(r) as rel_type,
                    r.uuid as rel_uuid,
                    r.name as rel_name,
                    r.fact as fact,
                    target.uuid as target_uuid,
                    target.name as target_name,
                    target.summary as target_summary
                LIMIT 1
            """)
            record = await result.single()
            if record:
                print(f"\n【源实体】")
                print(f"  UUID: {record['source_uuid']}")
                print(f"  名称: {record['source_name']}")
                print(f"  摘要: {record['source_summary']}")
                print(f"\n【关系】")
                print(f"  UUID: {record['rel_uuid']}")
                print(f"  类型: {record['rel_type']}")
                print(f"  名称: {record['rel_name']}")
                print(f"  事实: {record['fact']}")
                print(f"\n【目标实体】")
                print(f"  UUID: {record['target_uuid']}")
                print(f"  名称: {record['target_name']}")
                print(f"  摘要: {record['target_summary']}")
            
    finally:
        await driver.close()


if __name__ == '__main__':
    asyncio.run(inspect_graph())
