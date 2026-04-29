# 本地启动性能排查

## 背景

2026-04-29 对当前工作区 `D:\CodeWorkSpace\personal-knowledge-base\.worktrees\main-merge-memories` 的前后端启动慢问题做了一次定向排查，目标是明确：

1. 前端为什么启动慢
2. 后端为什么启动慢
3. 后端应采用什么方案加速启动
4. `AGENTS.md` 里应该保留什么启动方法

## 结论

### 前端慢启动根因

前端真正慢的不是 Vite 本身，而是 dev compose 的启动方式：

1. `docker-compose.dev.yml` 当前前端命令是 `npm ci && npm run dev -- --host 0.0.0.0 --port 5173`
2. 这意味着每次起 dev 容器都会重新安装依赖
3. Windows 宿主机目录挂载到 Linux 容器后，`frontend/node_modules` 容易混入不同平台的二进制产物
4. 一旦目录里同时残留 Windows 的 `esbuild.exe` / `rollup.win32-x64-msvc.node` 和容器内 Linux 安装过程，`npm ci` 很容易报 `EIO` / `EPERM`，容器反复重启

当前工作区在宿主机直接运行 Vite 时，`vite-dev.log` 显示：

- `ready in 283 ms`

所以前端“慢启动”的核心问题不是应用构建本身，而是“每次都用 dev 容器重新 `npm ci`”这条链路过重且不稳定。

### 后端慢启动根因

后端慢启动是由“重型模型客户端在启动阶段被提前初始化”造成的，而且当前代码路径里至少有两层触发点：

1. `backend/app/routers/graph.py` 在模块级直接创建 `GraphVisualizationService()`
2. `GraphVisualizationService.__init__()` 直接创建 `GraphitiClient()`
3. `GraphitiClient.__init__()` 直接创建 `LocalEmbedder()`
4. `LocalEmbedder.__init__()` 会立即加载 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

除此之外，后端 lifespan 启动流程里还有第二层：

1. `backend/app/main.py` 的 startup step 1 会创建 `GraphitiIngestWorker()`
2. `GraphitiIngestWorker.__init__()` 也会直接创建 `GraphitiClient()`
3. 这会再次触发 `LocalEmbedder()` 初始化

也就是说，当前后端启动并不是“先把 Web 服务拉起来，再按需使用图谱能力”，而是“为了让图谱相关能力可用，先把 embedding 模型和 Graphiti 客户端在启动期就准备好”。

这会带来两个问题：

1. `/health` 在应用启动完成前不可用，外部看起来像服务卡住
2. 图谱和入图相关能力把 chat、settings、普通 API 的启动时间一起拖慢了

## 证据

### 前端

1. `docker-compose.dev.yml` 里前端命令包含 `npm ci`
2. 当前宿主机 Vite 日志 `frontend/vite-dev.log` 显示 `ready in 283 ms`
3. 本次排障里 `pkb-frontend-dev` 反复报错：
   - `EIO: i/o error, unlink '/app/node_modules/@esbuild/win32-x64/esbuild.exe'`
   - `EIO: i/o error, unlink '/app/node_modules/@rollup/rollup-win32-x64-msvc/rollup.win32-x64-msvc.node'`

### 后端

关键代码链路：

1. `backend/app/routers/graph.py`
2. `backend/app/services/graph_visualization_service.py`
3. `backend/app/services/graphiti_client.py`
4. `backend/app/services/local_embedder.py`
5. `backend/app/workers/graphiti_ingest_worker.py`
6. `backend/app/main.py`

本次运行日志里能看到：

1. 应用启动阶段会执行 `Loading local embedding model: paraphrase-multilingual-MiniLM-L12-v2`
2. `/health` 在 `Application startup complete` 之前可能返回 `Empty reply from server`

## 推荐启动方式

### 日常开发默认方式

1. 后端继续用 Docker
2. 前端改用宿主机直接跑 Vite

原因：

1. 后端依赖数据库、Neo4j、模型配置和容器网络，放 Docker 更稳
2. 前端宿主机启动几乎是秒开，且避免 dev 容器反复 `npm ci`

### 推荐命令

后端：

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps --force-recreate backend
```

前端：

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

验收：

```powershell
curl.exe -i --max-time 20 http://127.0.0.1:8000/health
curl.exe -i --max-time 20 http://127.0.0.1:5173
```

## 后端加速方案

### 推荐方案

把图谱与 embedding 的初始化从“启动期同步执行”改成“按需懒加载 + 可选后台预热”。

### 具体拆分

1. 去掉 `graph.py` 里的模块级 `GraphVisualizationService()`，改成请求时获取 service
2. `GraphVisualizationService` 默认不要在构造函数里持有 `GraphitiClient`
3. 图谱可视化优先直接用 Neo4j driver；只有真正需要 Graphiti driver 时再拿 Graphiti client
4. `GraphitiIngestWorker` 启动时只创建队列和 worker task，不要在 `__init__` 或 `start()` 阶段初始化 `GraphitiClient`
5. 在第一次真正入图时，再创建 `GraphitiClient` 和 `LocalEmbedder`
6. 如果担心第一次入图请求变慢，可以在 FastAPI startup 完成后单独起后台预热线程或异步任务，但不能阻塞 `/health`

### 预期效果

1. `/health` 可以更快返回 200
2. chat、settings、memories 等不依赖图谱写入的页面不会再被 embedding 模型初始化拖慢
3. 图谱写入的冷启动成本被移动到真正需要它的那一刻，而不是所有接口共担

### 风险与取舍

1. 第一次入图任务会比现在更慢
2. 需要给 Graphiti client 做一次性懒初始化和并发保护，避免多个首次请求重复初始化
3. 如果后续希望“启动后图谱能力立刻可用”，可以在后台预热，但要和健康检查解耦

### 不推荐方案

1. 继续保留启动期同步加载，只尝试换更快模型
2. 继续把前端日常开发绑定到 dev 容器 + `npm ci`

原因：

1. 这两个方案都没有解决“重型初始化放错时机”的根问题
2. 即使模型变小、网络更快，启动链路仍然耦合过重

## 对 AGENTS.md 的要求

`AGENTS.md` 只应保留：

1. 当前推荐启动方式
2. 固定端口约定
3. 极少量必须记住的启动前提
4. 指向详细排障文档的链接

不应继续把一次次排障日志、长篇错误现象和所有临时处理堆在 `AGENTS.md` 里。

## 实现结果

本次已按推荐方案落地以下修改：

1. `backend/app/routers/graph.py` 去掉模块级 `GraphVisualizationService()`，避免 import 阶段创建图谱可视化 service
2. `backend/app/services/graph_visualization_service.py` 改为可选注入 `graphiti_client`，默认不再主动创建 `GraphitiClient`
3. `backend/app/workers/graphiti_ingest_worker.py` 改为首次真正入图时才通过 `_get_graphiti_client()` 创建 `GraphitiClient`
4. `backend/app/main.py` 调整 startup 顺序：先恢复 pending 队列、先启动标题 worker、最后才启动图谱 worker 的消费循环

## 验证结果

### 单元与集成验证

已执行：

```powershell
cd backend
pytest tests/test_startup_lifecycle.py tests/test_health.py tests/services/test_graph_visualization_service.py tests/workers/test_graphiti_ingest_worker.py tests/test_memories_graph.py -q
```

结果：

- `25 passed`

### 真实冷启动验证

已执行：

```powershell
docker restart pkb-backend
curl.exe -i --max-time 20 http://127.0.0.1:8000/health
docker logs --since 2m pkb-backend
```

结果：

1. `/health` 冷启动后恢复为 `200 OK`
2. 最新启动日志中，`Application startup complete` 已经出现在本轮 startup 结束处
3. 最新 startup 日志里不再出现 `Loading local embedding model: paraphrase-multilingual-MiniLM-L12-v2` 这类 embedding 初始化记录

这说明当前实现已经把后端健康检查路径和图谱 embedding 初始化从启动主路径上拆开了。
