"""Smoke test for the personal knowledge base with Graphiti integration."""
import requests
import time
import json

BASE_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_health():
    """Test health endpoint."""
    print_section("Test 1: Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("✅ Health check passed")

def test_create_single_memory():
    """Test creating a single memory."""
    print_section("Test 2: Create Single Memory")
    
    memory_data = {
        "title": "Python 编程最佳实践",
        "content": "在 Python 中，应该遵循 PEP 8 编码规范。使用有意义的变量名，保持代码简洁。函数应该只做一件事，并且做好。使用类型提示可以提高代码可读性。",
        "group_id": "programming"
    }
    
    response = requests.post(f"{BASE_URL}/api/memories", json=memory_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    assert response.status_code == 201
    memory = response.json()
    memory_id = memory["id"]
    print(f"✅ Memory created with ID: {memory_id}")
    
    return memory_id

def test_list_memories():
    """Test listing memories."""
    print_section("Test 3: List Memories")
    
    response = requests.get(f"{BASE_URL}/api/memories?keyword=")
    print(f"Status: {response.status_code}")
    memories = response.json()
    print(f"Found {len(memories)} memories")
    
    for memory in memories:
        print(f"  - {memory['title']} (ID: {memory['id']}, Status: {memory.get('graph_status', 'N/A')})")
    
    assert response.status_code == 200
    print("✅ List memories passed")
    
    return memories

def test_add_to_graph(memory_id):
    """Test adding a memory to the knowledge graph."""
    print_section("Test 4: Add Memory to Knowledge Graph")
    
    print(f"Adding memory {memory_id} to graph...")
    response = requests.post(f"{BASE_URL}/api/memories/{memory_id}/add-to-graph")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    assert response.status_code == 202
    print("✅ Memory queued for graph ingestion")
    
    # Wait a bit for processing
    print("\nWaiting for processing (10 seconds)...")
    time.sleep(10)
    
    # Check status
    print("\nChecking graph status...")
    response = requests.get(f"{BASE_URL}/api/memories/{memory_id}/graph-status")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    status_data = response.json()
    print(f"\nGraph Status: {status_data['graph_status']}")
    if status_data.get('graph_error'):
        print(f"Error: {status_data['graph_error']}")
    if status_data.get('graph_episode_uuid'):
        print(f"Episode UUID: {status_data['graph_episode_uuid']}")
    
    return status_data

def test_batch_create_and_add():
    """Test creating multiple memories and batch adding to graph."""
    print_section("Test 5: Batch Create and Add to Graph")
    
    # Create multiple memories
    memories_data = [
        {
            "title": "机器学习基础",
            "content": "机器学习是人工智能的一个分支，它使计算机能够从数据中学习。主要分为监督学习、无监督学习和强化学习三大类。常用算法包括线性回归、决策树、神经网络等。",
            "group_id": "ai"
        },
        {
            "title": "Docker 容器化技术",
            "content": "Docker 是一个开源的容器化平台。它允许开发者将应用及其依赖打包到一个轻量级、可移植的容器中。使用 Dockerfile 定义镜像，docker-compose 管理多容器应用。",
            "group_id": "devops"
        },
        {
            "title": "RESTful API 设计原则",
            "content": "RESTful API 应该使用 HTTP 方法（GET、POST、PUT、DELETE）来表示操作。URL 应该是名词而不是动词。使用适当的状态码。支持版本控制和分页。提供清晰的错误消息。",
            "group_id": "programming"
        }
    ]
    
    memory_ids = []
    for i, data in enumerate(memories_data, 1):
        print(f"\nCreating memory {i}/3: {data['title']}")
        response = requests.post(f"{BASE_URL}/api/memories", json=data)
        assert response.status_code == 201
        memory = response.json()
        memory_ids.append(memory["id"])
        print(f"  ✅ Created with ID: {memory['id']}")
    
    print(f"\n✅ Created {len(memory_ids)} memories")
    
    # Batch add to graph
    print("\nBatch adding to knowledge graph...")
    batch_data = {"memory_ids": memory_ids}
    response = requests.post(f"{BASE_URL}/api/memories/batch-add-to-graph", json=batch_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    assert response.status_code == 202
    result = response.json()
    print(f"✅ Queued {result['queued_count']} memories for graph ingestion")
    
    # Wait for processing
    print("\nWaiting for batch processing (15 seconds)...")
    time.sleep(15)
    
    # Check status of all memories
    print("\nChecking status of all memories...")
    for memory_id in memory_ids:
        response = requests.get(f"{BASE_URL}/api/memories/{memory_id}/graph-status")
        status_data = response.json()
        print(f"  - Memory {memory_id[:8]}...: {status_data['graph_status']}")
        if status_data.get('graph_error'):
            print(f"    Error: {status_data['graph_error'][:100]}...")
    
    return memory_ids

def test_final_list():
    """Test final listing of all memories."""
    print_section("Test 6: Final Memory List")
    
    response = requests.get(f"{BASE_URL}/api/memories?keyword=")
    memories = response.json()
    
    print(f"Total memories: {len(memories)}\n")
    
    for memory in memories:
        print(f"Title: {memory['title']}")
        print(f"  ID: {memory['id']}")
        print(f"  Group: {memory['group_id']}")
        print(f"  Graph Status: {memory.get('graph_status', 'N/A')}")
        if memory.get('graph_episode_uuid'):
            print(f"  Episode UUID: {memory['graph_episode_uuid']}")
        print()
    
    print("✅ Final list retrieved")

def run_smoke_test():
    """Run complete smoke test."""
    print("\n" + "="*60)
    print("  SMOKE TEST: Personal Knowledge Base + Graphiti")
    print("="*60)
    
    try:
        # Test 1: Health check
        test_health()
        
        # Test 2: Create single memory
        memory_id = test_create_single_memory()
        
        # Test 3: List memories
        test_list_memories()
        
        # Test 4: Add to graph
        test_add_to_graph(memory_id)
        
        # Test 5: Batch create and add
        test_batch_create_and_add()
        
        # Test 6: Final list
        test_final_list()
        
        print_section("SMOKE TEST COMPLETED SUCCESSFULLY ✅")
        print("All tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise

if __name__ == "__main__":
    run_smoke_test()
