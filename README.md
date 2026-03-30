# Personal Knowledge Base

一个面向个人学习与知识沉淀的全栈项目，结合了个人知识库、知识图谱和基于检索增强生成（RAG）的智能问答能力。你可以在这个系统里录入笔记、上传图文内容、管理记忆条目，并通过聊天界面基于已有知识进行检索和问答。

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
- 数据库：SQLite 或 PostgreSQL
- 图谱能力：Neo4j + Graphiti
- 其他能力：OCR、图像处理、标题生成、RAG 问答

## 目录结构

```text
frontend/   前端项目（React + Vite）
backend/    后端项目（FastAPI + 数据层 + 图谱相关逻辑）
docs/       设计文档与实现方案
```

当前项目已经按“代码与文档分离”的方式整理：

- 根目录保留项目入口说明和运行相关文件
- `frontend/` 存放前端应用代码
- `backend/` 存放后端服务代码与后端专项文档
- `docs/superpowers/specs/` 存放设计说明
- `docs/superpowers/plans/` 存放实现计划

## 启动前准备

建议本机先准备好以下环境：

- Node.js 18+
- Python 3.12+
- Docker Desktop（用于 PostgreSQL 和 Neo4j）

如果你只想快速跑起基础前后端，数据库可以先使用 SQLite。

如果你要启用知识图谱相关功能，建议同时启动：

- PostgreSQL
- Neo4j
- 对应的大模型 / OpenAI 兼容 API Key

## 环境变量

### 前端

根目录的 `.env.example` 提供了前端侧常用变量示例：

```env
VITE_API_BASE_URL=http://localhost:8000
```

前端默认会请求 `http://localhost:8000` 的后端接口。

### 后端

后端环境变量建议参考：

- `backend/.env.example`
- 本地实际运行可使用 `backend/.env`

一个最小可运行示例：

```env
DATABASE_URL=sqlite:///./app.db
UPLOAD_DIR=backend/uploads/images
OCR_ENABLED=true
MULTIMODAL_PROVIDER=mock
MULTIMODAL_API_KEY=
KNOWLEDGE_GRAPH_BASE_URL=http://localhost:8001
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.stepfun.com/v1
```

## 前后端启动方式

### 1. 启动基础依赖（推荐）

如果你希望项目完整运行，先在项目根目录启动 PostgreSQL 和 Neo4j：

```bash
docker compose up -d
```

启动后默认端口如下：

- PostgreSQL：`5432`
- Neo4j Browser：`7474`
- Neo4j Bolt：`7687`

查看容器状态：

```bash
docker compose ps
```

### 2. 启动后端

进入后端目录：

```bash
cd backend
```

安装依赖：

```bash
pip install -r requirements.txt
```

启动方式一：使用项目自带启动脚本

```bash
python start.py
```

这个脚本会先初始化数据库，再启动 FastAPI 服务。

启动方式二：直接使用 uvicorn

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端默认访问地址：

- API 根地址：`http://localhost:8000`
- 健康检查：`http://localhost:8000/health`

### 3. 启动前端

打开另一个终端，进入前端目录：

```bash
cd frontend
```

安装依赖：

```bash
npm install
```

启动开发服务器：

```bash
npm run dev
```

如需局域网访问，可使用：

```bash
npm run dev -- --host 0.0.0.0
```

前端默认访问地址：

```text
http://localhost:5173
```

## 推荐启动顺序

为了减少报错，建议按照下面顺序启动：

1. 在项目根目录执行 `docker compose up -d`
2. 在 `backend/` 中执行 `python start.py`
3. 在 `frontend/` 中执行 `npm run dev`

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

## 常用开发命令

### 前端

```bash
cd frontend
npm run dev
npm run build
```

### 后端

```bash
cd backend
python start.py
pytest tests -v
```

### 整体测试

```bash
python -m pytest backend/tests -v
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
- 如果只是本地调试，可先切换到 SQLite

### 3. 知识图谱功能不可用

优先检查：

- Neo4j 是否运行在 `7687`
- `NEO4J_URI`、用户名和密码是否正确
- 模型 API Key 是否已经配置

## 补充说明

- 如果只验证基础前后端联通，可以先不深度使用图谱能力
- 如果要完整体验知识图谱与 RAG，建议保留 `docker compose` 启动的 PostgreSQL 与 Neo4j
- 后端图谱集成的更多细节可查看 `backend/README_GRAPHITI.md`
