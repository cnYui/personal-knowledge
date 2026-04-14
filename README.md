# Personal Knowledge Base

一个面向个人学习与知识沉淀的全栈项目，结合了个人知识库、知识图谱、基于检索增强生成（RAG）的智能问答能力，以及浏览器插件采集能力。你可以在这个系统里录入笔记、上传图文内容、管理记忆条目，并通过聊天界面基于已有知识进行检索和问答；也可以在常见 AI 平台中直接选中内容，保存到你的个人知识库。

## 项目用途

这个项目主要用于构建个人知识管理系统，覆盖以下场景：

- 记录和管理个人学习笔记、想法和知识片段
- 上传文本和图片内容，沉淀为可检索的记忆
- 将记忆内容进一步构建为知识图谱，提取实体与关系
- 在聊天页面中结合知识库与图谱进行问答
- 对已有记忆进行筛选、编辑、删除和可视化查看

## 技术栈

- 前端：React + TypeScript + Vite + Material UI
- 后端：FastAPI + SQLAlchemy
- 数据库：PostgreSQL
- 图谱能力：Neo4j + Graphiti
- 其他能力：OCR、图像处理、标题生成、RAG 问答

## 目录结构

```text
frontend/   前端项目（React + Vite）
backend/    后端项目（FastAPI + 数据层 + 图谱相关逻辑）
Chrome/     浏览器插件（AI 页面导航 + 知识采集）
docs/       设计文档与实现方案
```

当前项目已经按“代码与文档分离”的方式整理：

- 根目录保留项目入口说明和运行相关文件
- `frontend/` 存放前端应用代码
- `backend/` 存放后端服务代码与后端专项文档
- `Chrome/` 存放浏览器插件源码
- `docs/superpowers/specs/` 存放设计说明
- `docs/superpowers/plans/` 存放实现计划

## 启动前准备

建议本机先准备好以下环境：

- Node.js 20+
- Python 3.12+
- Docker Desktop

如果你要启用知识图谱和 Agentic RAG 相关功能，还需要准备可用的大模型 / OpenAI 兼容 API Key。

## 环境变量

### 根目录 `.env`

项目根目录的 `.env.example` 提供了 Docker Compose 级别的统一变量模板。首次启动前，建议复制一份：

```bash
cp .env.example .env
```

Windows 可直接运行：

```bat
copy .env.example .env
```

根目录 `.env` 主要负责：

- Docker 端口映射
- PostgreSQL / Neo4j 默认账号密码
- 前端构建时注入的 `VITE_API_BASE_URL`
- 后端容器运行时使用的数据库、图谱、模型配置

### 后端 `backend/.env.example`

`backend/.env.example` 保留了后端单独运行时的参考配置，适合不使用 Docker、直接在本机 Python 环境启动后端时参考。

换句话说：

- `/.env.example`：给 Docker Compose / 一键启动脚本用
- `backend/.env.example`：给纯后端本地运行用

如果你在 Docker 模式下运行，一般只需要维护根目录 `.env`。

## Docker 启动方式

### 1. 部署模式（默认，适合别人拉下来直接跑）

默认 `docker-compose.yml` 会启动：

- `postgres`
- `neo4j`
- `backend`
- `frontend`

首次启动：

```bash
docker compose up -d --build
```

查看状态：

```bash
docker compose ps
```

查看后端日志：

```bash
docker compose logs -f backend
```

停止服务：

```bash
docker compose down
```

连同数据卷一起删除：

```bash
docker compose down -v
```

> 注意：`docker compose down -v` 会清空 PostgreSQL 和 Neo4j 的持久化数据。

### 2. 开发模式（前后端热更新）

开发模式在默认 Compose 基础上叠加 `docker-compose.dev.yml`，让：

- 后端使用挂载目录 + `uvicorn --reload`
- 前端使用 Node 容器运行 `npm run dev`

启动命令：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

此模式下：

- 前端代码修改可热更新
- 后端 Python 代码修改可自动重载
- PostgreSQL / Neo4j 仍由同一套基础服务提供
- 由于 Compose 叠加时 `ports` 会追加而不是替换，开发模式前端额外暴露在 `http://localhost:5174`

## 一键启动脚本

仓库根目录提供了两个快捷脚本：

- `start.bat`：Windows
- `start.sh`：macOS / Linux

它们会在 `.env` 不存在时自动从 `.env.example` 复制，然后执行：

```bash
docker compose up -d --build
```

使用方式：

### Windows

```bat
start.bat
```

### macOS / Linux

```bash
chmod +x start.sh
./start.sh
```

## 默认访问地址

```text
前端: http://localhost:5173
开发模式前端: http://localhost:5174
后端健康检查: http://localhost:8000/health
Neo4j Browser: http://localhost:7474
PostgreSQL: localhost:5432
```

## 数据持久化说明

Docker 默认使用如下 volumes 持久化数据：

- `postgres_data`
- `neo4j_data`
- `neo4j_logs`

这意味着：

- 正常执行 `docker compose down` 不会删除数据库数据
- 只有执行 `docker compose down -v` 才会清空这些持久化卷

## 非 Docker 本地启动方式

如果你更习惯直接在本机运行前后端，也可以继续使用传统方式。

### 启动基础依赖

```bash
docker compose up -d postgres neo4j
```

### 启动后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

说明：

- 真实应用入口是 `backend/app/main.py`
- `backend/start.py` 是兼容包装，内部仍启动 `uvicorn app.main:app`
- 运行时数据库默认应使用 PostgreSQL，不再推荐 SQLite

### 启动前端

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

如需局域网访问：

```bash
npm run dev -- --host 0.0.0.0
```

## 项目主要功能

### 记忆管理

- 浏览、搜索、筛选已有记忆
- 编辑和删除记忆内容
- 查看记忆详情

### 内容上传

- 上传文本内容
- 上传图片并进行处理
- 支持后续 OCR / 多模态扩展

### 知识图谱

- 将记忆加入知识图谱
- 抽取实体、关系和上下文
- 查看图谱可视化结果

### 智能问答

- 基于已有记忆做聊天问答
- 支持 RAG 检索增强
- 结合图谱结果提升上下文关联能力

### 每日回顾

- 提供“今日推荐回顾 / 最近主题聚焦 / 最近已沉淀进知识图谱 / 待继续整理”等分区
- 适合用于快速回看当天最值得复习的记忆与最近持续出现的主题
- 支持查看推荐条目的详情内容与时间信息

### 浏览器插件

- 在 `Chrome/` 目录中提供浏览器插件
- 支持在 ChatGPT、Gemini、Kimi、通义千问、豆包等 AI 平台中注入侧边面板
- 支持快速导航、收藏、选中文本采集
- 支持将选中的单段文本或勾选的整组问答直接保存到个人知识库的 `记忆管理` 页面
- 支持将选中的 AI 对话内容直接保存为个人知识库里的普通记忆

## 常用开发命令

### 前端

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
npm run build
```

### 后端

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pytest tests -v
```

### 整体测试

```bash
python -m pytest backend/tests -v
```

### Docker

```bash
docker compose up -d --build
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
docker compose ps
docker compose logs -f backend
docker compose down
docker compose down -v
```

## 常见问题

### 1. 前端打开后没有数据

优先检查：

- 后端是否已经启动
- `VITE_API_BASE_URL` 是否指向 `http://localhost:8000`
- 浏览器控制台是否有接口报错

### 2. 后端启动时报数据库连接错误

优先检查：

- `DATABASE_URL` 配置是否正确
- PostgreSQL 容器是否已经启动
- `pkb-postgres` 是否监听 `5432`
- 如果你修改过数据库用户名或密码，记得同步更新根目录 `.env`

### 3. 知识图谱功能不可用

优先检查：

- Neo4j 是否运行在 `7687`
- `NEO4J_URI`、用户名和密码是否正确
- 模型 API Key 是否已经配置

### 4. Docker 模式下 backend 启动失败

优先检查：

- `docker compose logs -f backend`
- 根目录 `.env` 中的数据库、Neo4j、模型配置是否完整
- PostgreSQL 与 Neo4j 是否已先成功启动

### 5. 开发模式前端访问地址不对

如果你使用的是：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

请优先访问：

- `http://localhost:5174`：Vite 开发服务器
- `http://localhost:5173`：基础 Compose 中的 Nginx 前端容器映射

### 6. 模型能力不可用

如果 `DIALOG_API_KEY` / `KNOWLEDGE_BUILD_API_KEY` 未配置，应用中的依赖模型能力的功能可能无法正常工作，例如：

- 标题生成
- 图谱构建
- 部分聊天 / RAG 相关能力

但不依赖模型的基础页面、容器启动、数据库连接和部分本地功能仍可验证。

## 补充说明

- 如果只验证基础前后端联通，可以先不深度使用图谱能力
- 如果要完整体验知识图谱与 RAG，建议保留 `docker compose` 启动的 PostgreSQL 与 Neo4j
- 后端图谱集成的更多细节可查看 `backend/README_GRAPHITI.md`
- 浏览器插件的加载目录是 `Chrome/`，可在 `chrome://extensions/` 中以“加载已解压的扩展程序”方式使用
