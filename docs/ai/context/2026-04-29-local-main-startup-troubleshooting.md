# 本地 main 分支启动排障记录

## 背景

2026-04-29 在本地重新启动当前 `main` 分支前后端时，目标端口保持项目约定：

- 前端：`5173`
- 后端：`8000`

本次启动路径为：

`D:\CodeWorkSpace\personal-knowledge-base\.worktrees\main-merge-memories`

当前默认启动方式已经收敛为：

- 后端使用 Docker
- 前端使用宿主机直接运行 Vite

本文件保留详细排障细节，不再作为日常启动步骤说明；日常启动方法以 `AGENTS.md` 和 `docs/ai/context/2026-04-29-startup-performance-analysis.md` 为准。

## 遇到的问题与处理

### 端口被 Docker/WSL 转发占用

现象：

`Get-NetTCPConnection -LocalPort 5173,8000` 显示占用进程为 `wslrelay` 和 `com.docker.backend`。

处理：

不要直接杀 Docker Desktop 后台进程。先执行：

```powershell
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Ports}}"
```

定位到：

- `poco-claw-backend-1` 占用 `8000`
- 旧 `pkb-frontend-dev` 占用 `5173`

按用户要求直接释放端口：

```powershell
docker stop poco-claw-backend-1 pkb-frontend-dev
```

### 数据库容器名冲突

现象：

执行 dev compose 启动时，报 `pkb-postgres` 和 `pkb-neo4j` 容器名已经存在。

原因：

已有旧数据库容器仍在运行，compose 尝试按当前项目再次创建同名容器。

处理：

优先复用旧数据库容器，不要贸然删除数据库容器。只重建前后端：

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps backend frontend
```

如果旧 `pkb-backend` 或 `pkb-frontend-dev` 容器名也冲突，先删除旧前后端容器：

```powershell
docker rm -f pkb-backend pkb-frontend-dev
```

### 前端容器里找不到 npm

现象：

`pkb-frontend-dev` 日志反复出现：

```text
sh: npm: not found
```

原因：

本地 Docker 的 `node:20-alpine` 标签曾被错误构建成生产 Nginx 镜像，导致 dev compose 虽然配置了 `image: node:20-alpine`，但容器里实际没有 Node/npm。

处理：

```powershell
docker pull node:20-alpine
docker rm -f pkb-frontend-dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps --no-build frontend
```

### 后端无法解析 postgres 主机名

现象：

`pkb-backend` 日志出现：

```text
psycopg.OperationalError: [Errno -5] No address associated with hostname
```

原因：

旧 `pkb-postgres/pkb-neo4j` 容器在 `personal-knowledge-base_default` 网络，当前 `main` worktree 的后端在 `main-merge-memories_default` 网络。后端容器内无法解析 `postgres` 和 `neo4j`。

处理：

把旧数据库容器接入当前 compose 网络，并设置别名：

```powershell
docker network connect --alias postgres main-merge-memories_default pkb-postgres
docker network connect --alias neo4j main-merge-memories_default pkb-neo4j
docker restart pkb-backend
```

### 容器已监听但 HTTP empty reply

现象：

`curl http://127.0.0.1:8000/health` 或 `curl http://127.0.0.1:5173` 返回 `Empty reply from server`。

原因：

- 后端 Uvicorn 已监听端口，但应用仍在加载 embedding 模型和启动 worker
- 前端容器已监听端口，但仍在执行 `npm ci`，Vite dev server 尚未 ready
- 这次进一步确认，后端慢启动的具体卡点在应用导入阶段：`graph` 路由模块级 `GraphVisualizationService()` 会立即构造 `GraphitiClient`，继而触发 `LocalEmbedder` 从 HuggingFace 加载 `paraphrase-multilingual-MiniLM-L12-v2`

补充：

- 以上现象是 2026-04-29 懒加载改造前的历史排障记录
- 当前代码已把 `graph` 路由和 `GraphitiIngestWorker` 的图谱客户端初始化改成懒加载；如果现在仍看到 `/health` 空回复，不应再默认归因到 embedding 启动，应继续排查容器、数据库、网络或 reload 状态

处理：

查看日志并等待：

```powershell
docker logs --tail 120 pkb-backend
docker logs --tail 120 pkb-frontend-dev
```

后端等待出现：

```text
Application startup complete
```

前端等待出现：

```text
VITE ... ready
```

## 最终验收

最终验收通过：

```powershell
curl.exe -i --max-time 15 http://127.0.0.1:8000/health
curl.exe -i --max-time 15 http://127.0.0.1:5173
```

结果：

- `http://127.0.0.1:8000/health` 返回 `200 OK` 和 `{"status":"ok"}`
- `http://127.0.0.1:5173` 返回 `200 OK` 和 Vite HTML
