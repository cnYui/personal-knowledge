# Docker 双模式交付与前端构建修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复前端当前构建错误，补齐前后端 Docker 交付能力、开发/部署双模式 compose、一键启动脚本、README 文档，并完成本地启动验证与 GitHub 推送准备。

**Architecture:** 采用双模式 Docker 结构：默认 `docker-compose.yml` 负责“别人拉下来一键启动”的部署模式，`docker-compose.dev.yml` 负责本地开发覆盖。前端使用 Vite 构建并由 Nginx 托管静态资源，后端使用 Python + Uvicorn 提供 API。前端构建错误通过稳定的 MUI `sx` 组合方式修复，避免 `SxProps` 展开导致的类型推断问题。

**Tech Stack:** React 18, TypeScript, Vite, MUI, FastAPI, Python 3.12, Uvicorn, PostgreSQL, Neo4j, Docker, Docker Compose, Nginx

---

### File Map

**Modify:**
- `frontend/src/components/memory/MemoryBubbleItem.tsx` — 修复 `Paper sx` 类型推断错误
- `frontend/src/pages/DailyReviewPage.tsx` — 保留“删除搜索框”结果，并修复 `Paper sx` 类型推断错误
- `docker-compose.yml` — 扩展为默认部署模式，纳入 frontend/backend
- `.env.example` — 补充 Docker Compose 级别配置示例
- `.gitignore` — 忽略本地测试数据库文件与 Docker 运行中间产物（如有必要）
- `README.md` — 补充双模式 Docker、脚本、环境变量与排障说明

**Create:**
- `frontend/Dockerfile` — 前端多阶段构建
- `frontend/nginx.conf` — Nginx 静态站点与 SPA 回退配置
- `backend/Dockerfile` — 后端镜像构建文件
- `docker-compose.dev.yml` — 开发模式覆盖配置
- `start.bat` — Windows 一键启动脚本
- `start.sh` — Mac/Linux 一键启动脚本

**Verify / Run:**
- `frontend/package.json` — 使用现有 `build` 命令
- `backend/.env.example` — 参考后端运行时变量
- `backend/app/main.py` — 确认后端启动入口和健康检查

---

### Task 1: 修复前端构建错误

**Files:**
- Modify: `frontend/src/components/memory/MemoryBubbleItem.tsx`
- Modify: `frontend/src/pages/DailyReviewPage.tsx`
- Verify: `frontend/src/styles/cardStyles.ts`

- [ ] **Step 1: 先写出目标改法，避免在代码里使用 `as any`**

将两个 `Paper` 组件的 `sx` 从对象展开改为数组组合形式，类似：

```tsx
sx={[
  unifiedCardSx,
  unifiedCardHoverSx,
  {
    px: 2,
    py: 1.65,
    cursor: 'pointer',
    maxWidth: { xs: '100%', md: '82%' },
  },
]}
```

并把依赖状态的边框色、hover 覆盖项放在最后一个局部对象内。

- [ ] **Step 2: 修改 `frontend/src/components/memory/MemoryBubbleItem.tsx`**

把：

```tsx
sx={{
  ...unifiedCardSx,
  ...unifiedCardHoverSx,
  px: 2,
  py: 1.65,
  cursor: 'pointer',
  maxWidth: { xs: '100%', md: '82%' },
  border: '1px solid',
  borderColor: memory.graph_status === 'added' ? 'rgba(120, 140, 93, 0.42)' : 'divider',
  bgcolor: unifiedCardMutedBackground,
  '&:hover': {
    borderColor: 'rgba(20, 20, 19, 0.28)',
    bgcolor: unifiedCardMutedBackground,
  },
}}
```

改为：

```tsx
sx={[
  unifiedCardSx,
  unifiedCardHoverSx,
  {
    px: 2,
    py: 1.65,
    cursor: 'pointer',
    maxWidth: { xs: '100%', md: '82%' },
    border: '1px solid',
    borderColor: memory.graph_status === 'added' ? 'rgba(120, 140, 93, 0.42)' : 'divider',
    bgcolor: unifiedCardMutedBackground,
    '&:hover': {
      borderColor: 'rgba(20, 20, 19, 0.28)',
      bgcolor: unifiedCardMutedBackground,
    },
  },
]}
```

- [ ] **Step 3: 修改 `frontend/src/pages/DailyReviewPage.tsx`**

把 `ReviewCard` 内的：

```tsx
sx={{
  ...unifiedCardSx,
  ...unifiedCardHoverSx,
  px: 2,
  py: 1.65,
  cursor: 'pointer',
  maxWidth: { xs: '100%', md: '82%' },
  border: refinementTone ? '1px dashed rgba(217, 119, 87, 0.32)' : '1px solid',
  borderColor: refinementTone ? 'rgba(217, 119, 87, 0.32)' : item.graph_status === 'added' ? 'rgba(120, 140, 93, 0.42)' : 'divider',
  bgcolor: unifiedCardMutedBackground,
  '&:hover': {
    ...((unifiedCardHoverSx as { '&:hover'?: object })['&:hover'] ?? {}),
    borderColor: refinementTone ? 'rgba(217, 119, 87, 0.46)' : 'rgba(20, 20, 19, 0.28)',
    bgcolor: unifiedCardMutedBackground,
  },
}}
```

改为：

```tsx
sx={[
  unifiedCardSx,
  unifiedCardHoverSx,
  {
    px: 2,
    py: 1.65,
    cursor: 'pointer',
    maxWidth: { xs: '100%', md: '82%' },
    border: refinementTone ? '1px dashed rgba(217, 119, 87, 0.32)' : '1px solid',
    borderColor: refinementTone
      ? 'rgba(217, 119, 87, 0.32)'
      : item.graph_status === 'added'
        ? 'rgba(120, 140, 93, 0.42)'
        : 'divider',
    bgcolor: unifiedCardMutedBackground,
    '&:hover': {
      borderColor: refinementTone ? 'rgba(217, 119, 87, 0.46)' : 'rgba(20, 20, 19, 0.28)',
      bgcolor: unifiedCardMutedBackground,
    },
  },
]}
```

注意：这里不再通过 `as { '&:hover'?: object }` 去读取共享 hover 对象，避免再次引入类型噪音。

- [ ] **Step 4: 运行前端构建验证**

Run:

```bash
cmd /c "cd /d d:\CodeWorkSpace\personal-knowledge-base\frontend && npm run build"
```

Expected: `tsc -b && vite build` 成功，输出 `dist/` 构建结果，无 TS2769 报错。

- [ ] **Step 5: 提交这一小步**

```bash
git add frontend/src/components/memory/MemoryBubbleItem.tsx frontend/src/pages/DailyReviewPage.tsx
git commit -m "fix: resolve frontend mui sx build errors"
```

---

### Task 2: 为前端补齐 Docker 打包能力

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Verify: `frontend/package.json`

- [ ] **Step 1: 新建 `frontend/Dockerfile`**

写入：

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 2: 新建 `frontend/nginx.conf`**

写入：

```nginx
server {
  listen 80;
  server_name _;

  root /usr/share/nginx/html;
  index index.html;

  location / {
    try_files $uri $uri/ /index.html;
  }

  location /assets/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
  }
}
```

- [ ] **Step 3: 构建前端 Docker 镜像**

Run:

```bash
docker build -t pkb-frontend-test -f d:\CodeWorkSpace\personal-knowledge-base\frontend\Dockerfile d:\CodeWorkSpace\personal-knowledge-base\frontend
```

Expected: 镜像构建成功，无 `npm run build` 错误。

- [ ] **Step 4: 提交这一小步**

```bash
git add frontend/Dockerfile frontend/nginx.conf
git commit -m "feat: add frontend docker packaging"
```

---

### Task 3: 为后端补齐 Docker 打包能力

**Files:**
- Create: `backend/Dockerfile`
- Verify: `backend/requirements.txt`
- Verify: `backend/app/main.py`

- [ ] **Step 1: 新建 `backend/Dockerfile`**

写入：

```dockerfile
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libpq-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 构建后端 Docker 镜像**

Run:

```bash
docker build -t pkb-backend-test -f d:\CodeWorkSpace\personal-knowledge-base\backend\Dockerfile d:\CodeWorkSpace\personal-knowledge-base\backend
```

Expected: 依赖安装成功，镜像构建完成。

- [ ] **Step 3: 提交这一小步**

```bash
git add backend/Dockerfile
git commit -m "feat: add backend docker packaging"
```

---

### Task 4: 扩展默认 Compose 为部署模式

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.env.example`
- Verify: `backend/.env.example`

- [ ] **Step 1: 更新根目录 `.env.example`，补齐 Compose 所需变量**

将现有内容替换为以 Docker 为中心的示例，例如：

```env
FRONTEND_PORT=5173
BACKEND_PORT=8000
POSTGRES_PORT=5432
NEO4J_HTTP_PORT=7474
NEO4J_BOLT_PORT=7687

POSTGRES_DB=personal_knowledge_base
POSTGRES_USER=pkb_user
POSTGRES_PASSWORD=pkb_password

NEO4J_USER=neo4j
NEO4J_PASSWORD=password

VITE_API_BASE_URL=http://localhost:8000

DATABASE_URL=postgresql+psycopg://pkb_user:pkb_password@postgres:5432/personal_knowledge_base
UPLOAD_DIR=backend/uploads/images
OCR_ENABLED=true
MULTIMODAL_PROVIDER=mock
MULTIMODAL_API_KEY=
KNOWLEDGE_GRAPH_BASE_URL=http://localhost:8001
NEO4J_URI=bolt://neo4j:7687
DIALOG_PROVIDER=deepseek
DIALOG_BASE_URL=https://api.deepseek.com/v1
DIALOG_MODEL=deepseek-chat
DIALOG_API_KEY=
KNOWLEDGE_BUILD_PROVIDER=deepseek
KNOWLEDGE_BUILD_BASE_URL=https://api.deepseek.com/v1
KNOWLEDGE_BUILD_MODEL=deepseek-chat
KNOWLEDGE_BUILD_API_KEY=
```

- [ ] **Step 2: 更新 `docker-compose.yml` 为完整部署模式**

将文件调整为类似结构：

```yaml
services:
  postgres:
    image: postgres:15-alpine
    container_name: pkb-postgres
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-personal_knowledge_base}
      POSTGRES_USER: ${POSTGRES_USER:-pkb_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-pkb_password}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-pkb_user} -d ${POSTGRES_DB:-personal_knowledge_base}"]
      interval: 10s
      timeout: 5s
      retries: 5

  neo4j:
    image: neo4j:5.26.0
    container_name: pkb-neo4j
    ports:
      - "${NEO4J_HTTP_PORT:-7474}:7474"
      - "${NEO4J_BOLT_PORT:-7687}:7687"
    environment:
      NEO4J_AUTH: ${NEO4J_USER:-neo4j}/${NEO4J_PASSWORD:-password}
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: pkb-backend
    depends_on:
      postgres:
        condition: service_healthy
      neo4j:
        condition: service_started
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      UPLOAD_DIR: ${UPLOAD_DIR:-backend/uploads/images}
      OCR_ENABLED: ${OCR_ENABLED:-true}
      MULTIMODAL_PROVIDER: ${MULTIMODAL_PROVIDER:-mock}
      MULTIMODAL_API_KEY: ${MULTIMODAL_API_KEY:-}
      KNOWLEDGE_GRAPH_BASE_URL: ${KNOWLEDGE_GRAPH_BASE_URL:-http://localhost:8001}
      NEO4J_URI: ${NEO4J_URI:-bolt://neo4j:7687}
      NEO4J_USER: ${NEO4J_USER:-neo4j}
      NEO4J_PASSWORD: ${NEO4J_PASSWORD:-password}
      DIALOG_PROVIDER: ${DIALOG_PROVIDER:-deepseek}
      DIALOG_BASE_URL: ${DIALOG_BASE_URL:-https://api.deepseek.com/v1}
      DIALOG_MODEL: ${DIALOG_MODEL:-deepseek-chat}
      DIALOG_API_KEY: ${DIALOG_API_KEY:-}
      KNOWLEDGE_BUILD_PROVIDER: ${KNOWLEDGE_BUILD_PROVIDER:-deepseek}
      KNOWLEDGE_BUILD_BASE_URL: ${KNOWLEDGE_BUILD_BASE_URL:-https://api.deepseek.com/v1}
      KNOWLEDGE_BUILD_MODEL: ${KNOWLEDGE_BUILD_MODEL:-deepseek-chat}
      KNOWLEDGE_BUILD_API_KEY: ${KNOWLEDGE_BUILD_API_KEY:-}
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        VITE_API_BASE_URL: ${VITE_API_BASE_URL:-http://localhost:8000}
    container_name: pkb-frontend
    depends_on:
      backend:
        condition: service_started
    ports:
      - "${FRONTEND_PORT:-5173}:80"
    restart: unless-stopped

volumes:
  neo4j_data:
  neo4j_logs:
  postgres_data:
```

- [ ] **Step 3: 验证 Compose 配置可解析**

Run:

```bash
docker compose -f d:\CodeWorkSpace\personal-knowledge-base\docker-compose.yml --env-file d:\CodeWorkSpace\personal-knowledge-base\.env.example config
```

Expected: 输出完整合并后的配置，无 YAML 或变量解析错误。

- [ ] **Step 4: 提交这一小步**

```bash
git add docker-compose.yml .env.example
git commit -m "feat: add deploy docker compose stack"
```

---

### Task 5: 新增开发模式 Compose 覆盖层

**Files:**
- Create: `docker-compose.dev.yml`

- [ ] **Step 1: 新建 `docker-compose.dev.yml`**

写入：

```yaml
services:
  backend:
    volumes:
      - ./backend:/app
    command: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    image: node:20-alpine
    container_name: pkb-frontend-dev
    working_dir: /app
    depends_on:
      backend:
        condition: service_started
    volumes:
      - ./frontend:/app
    command: sh -c "npm ci && npm run dev -- --host 0.0.0.0 --port 5173"
    environment:
      VITE_API_BASE_URL: ${VITE_API_BASE_URL:-http://localhost:8000}
    ports:
      - "${FRONTEND_PORT:-5173}:5173"
```

注意：该文件只覆盖开发必需项，不重复声明 postgres / neo4j。

- [ ] **Step 2: 验证开发模式 Compose 配置**

Run:

```bash
docker compose -f d:\CodeWorkSpace\personal-knowledge-base\docker-compose.yml -f d:\CodeWorkSpace\personal-knowledge-base\docker-compose.dev.yml --env-file d:\CodeWorkSpace\personal-knowledge-base\.env.example config
```

Expected: 配置可解析，frontend 服务被开发模式覆盖。

- [ ] **Step 3: 提交这一小步**

```bash
git add docker-compose.dev.yml
git commit -m "feat: add docker compose dev override"
```

---

### Task 6: 新增一键启动脚本

**Files:**
- Create: `start.bat`
- Create: `start.sh`

- [ ] **Step 1: 新建 `start.bat`**

写入：

```bat
@echo off
setlocal

if not exist .env (
  copy .env.example .env >nul
  echo [INFO] .env not found, created from .env.example
)

docker compose up -d --build
if errorlevel 1 (
  echo [ERROR] docker compose up failed
  exit /b 1
)

echo.
echo [OK] Services are starting.
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000/health
echo Neo4j:    http://localhost:7474
```

- [ ] **Step 2: 新建 `start.sh`**

写入：

```sh
#!/usr/bin/env sh
set -eu

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[INFO] .env not found, created from .env.example"
fi

docker compose up -d --build

echo
echo "[OK] Services are starting."
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000/health"
echo "Neo4j:    http://localhost:7474"
```

- [ ] **Step 3: 验证脚本最小可用性**

Run:

```bash
cmd /c "cd /d d:\CodeWorkSpace\personal-knowledge-base && start.bat"
```

Expected: 若 `.env` 不存在则自动创建，然后触发 `docker compose up -d --build`。

- [ ] **Step 4: 提交这一小步**

```bash
git add start.bat start.sh
git commit -m "feat: add one-click docker startup scripts"
```

---

### Task 7: 更新忽略规则与 README

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`

- [ ] **Step 1: 更新 `.gitignore`，忽略测试数据库文件**

在文件末尾追加：

```gitignore
backend/test_graph_retrieval.db
test_graph_retrieval.db
```

- [ ] **Step 2: 更新 `README.md` 的运行说明结构**

补充以下内容：

1. Docker 部署模式启动
2. Docker 开发模式启动
3. 一键启动脚本使用方法
4. 数据持久化（volumes）说明
5. `.env` 与 `backend/.env.example` 的关系
6. 模型 API 未配置时的影响说明

建议加入的关键命令：

```bash
docker compose up -d --build
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
docker compose ps
docker compose logs -f backend
docker compose down
docker compose down -v
```

- [ ] **Step 3: 在 README 中明确访问地址与排障信息**

写明：

```text
前端: http://localhost:5173
后端健康检查: http://localhost:8000/health
Neo4j Browser: http://localhost:7474
```

以及：

- 若 backend 启动失败，优先看 `docker compose logs -f backend`
- 若数据库密码改过，注意同步更新 `.env`
- 若执行 `docker compose down -v`，数据库持久化数据会被清空

- [ ] **Step 4: 提交这一小步**

```bash
git add .gitignore README.md
git commit -m "docs: add docker usage and persistence guide"
```

---

### Task 8: 执行本地验证并整理提交

**Files:**
- Verify: `docker-compose.yml`
- Verify: `docker-compose.dev.yml`
- Verify: `README.md`
- Verify: `frontend/src/components/memory/MemoryBubbleItem.tsx`
- Verify: `frontend/src/pages/DailyReviewPage.tsx`

- [ ] **Step 1: 重新运行前端构建**

Run:

```bash
cmd /c "cd /d d:\CodeWorkSpace\personal-knowledge-base\frontend && npm run build"
```

Expected: build 成功。

- [ ] **Step 2: 验证部署模式配置**

Run:

```bash
docker compose -f d:\CodeWorkSpace\personal-knowledge-base\docker-compose.yml --env-file d:\CodeWorkSpace\personal-knowledge-base\.env.example config
```

Expected: config 成功输出。

- [ ] **Step 3: 验证开发模式配置**

Run:

```bash
docker compose -f d:\CodeWorkSpace\personal-knowledge-base\docker-compose.yml -f d:\CodeWorkSpace\personal-knowledge-base\docker-compose.dev.yml --env-file d:\CodeWorkSpace\personal-knowledge-base\.env.example config
```

Expected: config 成功输出。

- [ ] **Step 4: 本地启动默认部署模式**

Run:

```bash
cmd /c "cd /d d:\CodeWorkSpace\personal-knowledge-base && if not exist .env copy .env.example .env >nul && docker compose up -d --build"
```

Expected: `postgres`、`neo4j`、`backend`、`frontend` 容器创建并启动。

- [ ] **Step 5: 检查服务状态**

Run:

```bash
docker compose -f d:\CodeWorkSpace\personal-knowledge-base\docker-compose.yml ps
```

Expected: 看到 4 个服务处于 `running` 或健康状态。

- [ ] **Step 6: 检查后端健康接口**

Run:

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

- [ ] **Step 7: 若服务异常，查看关键日志并修复后重试**

Run:

```bash
docker compose logs --no-color backend
docker compose logs --no-color frontend
```

Expected: 仅在需要时使用这些日志定位问题，然后返回修正对应文件。

- [ ] **Step 8: 清理不应提交的测试数据库文件**

Run:

```bash
cmd /c "del /f /q d:\CodeWorkSpace\personal-knowledge-base\test_graph_retrieval.db 2>nul & del /f /q d:\CodeWorkSpace\personal-knowledge-base\backend\test_graph_retrieval.db 2>nul"
```

Expected: 两个 `.db` 文件被删除，不进入提交。

- [ ] **Step 9: 查看最终变更**

Run:

```bash
git status --short --branch
git diff -- README.md .env.example .gitignore docker-compose.yml docker-compose.dev.yml frontend/Dockerfile frontend/nginx.conf backend/Dockerfile frontend/src/components/memory/MemoryBubbleItem.tsx frontend/src/pages/DailyReviewPage.tsx start.bat start.sh
```

Expected: 只包含本次预期文件与用户之前保留的改动。

- [ ] **Step 10: 合并提交**

```bash
git add README.md .env.example .gitignore docker-compose.yml docker-compose.dev.yml frontend/Dockerfile frontend/nginx.conf backend/Dockerfile frontend/src/components/memory/MemoryBubbleItem.tsx frontend/src/pages/DailyReviewPage.tsx start.bat start.sh docs/superpowers/specs/2026-04-06-docker-dual-mode-packaging-design.md docs/superpowers/plans/2026-04-06-docker-dual-mode-packaging-implementation-plan.md
git commit -m "feat: add dual-mode docker packaging and startup flow"
```

- [ ] **Step 11: 推送到 GitHub**

```bash
git push origin feature/personal-knowledge-base
```

Expected: 推送成功。

---

### Self-Review

**Spec coverage check:**
- 前端构建修复：Task 1
- 前端 Dockerfile：Task 2
- 后端 Dockerfile：Task 3
- 默认部署模式 compose：Task 4
- 开发模式 compose：Task 5
- 一键启动脚本：Task 6
- README / 持久化 / 排障：Task 7
- 本地启动测试 / GitHub 推送：Task 8

**Placeholder scan:**
- 未使用 TBD / TODO / “自行实现”等占位描述。
- 每个关键代码步骤均给出明确内容或命令。

**Type consistency check:**
- 前端构建修复统一使用 MUI `sx` 数组组合。
- Docker 相关文件路径均与当前仓库结构一致。
- 提交与验证命令均使用当前仓库绝对路径。