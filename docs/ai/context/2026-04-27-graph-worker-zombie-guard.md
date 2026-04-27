# Graph Worker 僵尸任务与事件循环阻塞修复

日期：2026-04-27

## 问题现象

memories 页面手动入图时，`POST /api/memories/{id}/add-to-graph` 已成功入队，但：

- `GET /api/memories/{id}/graph-status` 在任务执行期间会明显变慢，甚至请求超时
- 同一条 memory 在 `pending` 且没有 retry metadata 时，再次触发入图会被误判为 zombie，导致重复入队
- 首次任务超时失败后，残留队列项会继续把同一条 memory 再执行一轮
- Docker 中 `uvicorn` 工作进程长时间 CPU 接近 100%

## 根因

### 1. 本地 embedding 同步阻塞事件循环

`backend/app/services/local_embedder.py` 中：

- `LocalEmbedder.create()`
- `LocalEmbedder.create_batch()`

虽然定义为 `async`，但内部直接调用同步的 `sentence-transformers model.encode()`。

Graphiti 入图会在单个 worker 任务中多次触发 search、去重和 embedding 生成。这些同步 CPU 任务跑在 FastAPI 同一个事件循环线程里，导致状态查询等普通 API 也被拖慢。

### 2. worker 没有 memory 级别去重

`GraphitiIngestWorker.enqueue()` 之前只是简单 `queue.put(memory_id)`，没有区分：

- 已在队列里等待
- 已在处理中

因此重复点击入图、状态轮询误判 zombie、启动恢复等路径都可能把同一条 memory 重复塞进队列。

### 3. 残留队列项缺少状态校验

worker 真正开始处理前，没有检查数据库里的 `graph_status` 是否仍然是 `pending``。`

如果前一个任务已把 memory 标成 `failed` 或 `added`，残留的旧队列项仍会继续执行，形成“僵尸任务复活”。

## 修复策略

### 1. embedder 线程化

把本地 `model.encode()` 包装到 `asyncio.to_thread(...)`，让 CPU 密集的 embedding 计算离开事件循环线程。

### 2. worker 去重

`GraphitiIngestWorker` 增加：

- `_queued_memory_ids`
- `_processing_memory_ids`
- `is_memory_active(memory_id)`

规则：

- 已排队或执行中的 memory 不能再次入队
- worker 出队时把 memory 从 queued 集合移到 processing 集合
- worker 完成后清理 processing 集合

### 3. stale queue item 防御

`_process_memory()` 开始时增加状态校验：

- 只有 `graph_status == 'pending'` 才真正执行入图
- 非 `pending` 的残留队列项直接跳过

### 4. service 层优先看 worker 活跃状态

`MemoryService.add_to_graph()` 在判断 zombie 之前，先询问 worker：

- 如果当前 memory 已活跃，直接返回，不做重复 enqueue

这样可以避免“任务还在跑，只是还没写 retry metadata”时被误判为 zombie。

## 验证

新增回归测试覆盖：

- `LocalEmbedder.create()` 不阻塞事件循环
- worker 重复 enqueue 被拒绝
- stale non-pending queue item 被跳过
- active pending memory 不会被 service 重复入队

相关测试：

- `backend/tests/services/test_local_embedder.py`
- `backend/tests/workers/test_graphiti_ingest_worker.py`
- `backend/tests/test_memories_graph.py`

## 后续约束

- 后续若继续使用本地 embedding、OCR、reranker 等 CPU 密集逻辑，默认先检查是否需要 `asyncio.to_thread()` 或独立 worker 线程/进程
- `pending` 状态不能再直接等价于“可重排队”；必须同时考虑 worker 内存态或持久化 lease
