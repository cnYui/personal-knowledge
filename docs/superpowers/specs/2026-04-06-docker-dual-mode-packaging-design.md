# Docker 双模式交付与前端构建修复设计

日期：2026-04-06

## 背景

当前项目已经具备前后端代码、数据库依赖（PostgreSQL / Neo4j）以及基础 `docker-compose.yml`，但还存在以下问题：

1. `docker-compose.yml` 目前只覆盖 `postgres` 和 `neo4j`，尚未纳入前端与后端服务，无法实现“别人拉下代码后一键启动整个系统”。
2. 项目缺少前端与后端的 Dockerfile，也缺少适用于 Windows / Mac / Linux 的一键启动脚本。
3. 前端当前存在两个 TypeScript 构建错误，导致 `frontend` 目录下的 `npm run build` 无法通过。
4. README 尚未系统说明开发模式、部署模式、环境变量准备、数据持久化和一键启动方式。

本次设计目标是在尽量不打乱现有项目结构的前提下，同时满足：

- **你自己本地继续开发方便**
- **别人拉仓库后尽量接近一键启动即可使用**

## 目标

### 功能目标

- 修复前端当前已知的两个构建错误，使 `frontend` 下 `npm run build` 可通过。
- 为前端与后端补齐 Dockerfile。
- 将默认 `docker-compose.yml` 扩展为“部署模式”入口，支持启动：
  - frontend
  - backend
  - postgres
  - neo4j
- 新增开发模式覆盖配置，使本地开发时可挂载源码并保留开发体验。
- 提供一键启动脚本：
  - `start.bat`
  - `start.sh`
- 更新 README，明确两种启动模式、环境变量准备方式、数据持久化方式和常见问题。
- 完成本地验证，至少确认：
  - 前端 build 通过
  - Docker Compose 配置可启动
  - 关键服务能成功运行

### 非目标

- 本次不实现生产级编排（如 Kubernetes / Helm / Swarm）。
- 本次不引入云端托管数据库或外部托管 Neo4j。
- 本次不处理 CI/CD 自动发版。
- 本次不导出或分发你的个人真实数据库数据。

## 方案选型

### 方案 A：仅部署模式 Docker

做法：只提供镜像化后的 frontend / backend + compose 一键启动。

优点：

- 交付给别人最简单。
- 文档与脚本更少。

缺点：

- 本地开发效率较差。
- 每次改代码都要重建镜像，不适合你持续迭代。

### 方案 B：仅开发模式 Docker

做法：只提供挂载源码的开发 compose。

优点：

- 本地开发方便。

缺点：

- 不适合作为对外“一键可用”的交付方式。
- 对别人来说需要理解更多开发细节。

### 方案 C：开发 / 部署双模式并存（推荐）

做法：

- `docker-compose.yml` 作为默认部署模式。
- `docker-compose.dev.yml` 作为开发模式覆盖层。
- 前后端均提供 Dockerfile。
- 一键启动脚本默认走部署模式，开发者可选择使用开发模式。

优点：

- 同时满足“你自己开发”和“别人一键启动”的诉求。
- 风险低，结构清晰。
- 与当前仓库结构兼容，不需要大幅重构。

缺点：

- 配置文件会比单模式稍多。
- 需要在 README 中清晰区分两种模式。

**结论：采用方案 C。**

## 设计详情

## 1. 前端构建修复

当前已知构建错误位于：

- `frontend/src/components/memory/MemoryBubbleItem.tsx`
- `frontend/src/pages/DailyReviewPage.tsx`

错误本质：

- MUI `sx` 对象与共享样式对象展开时，TypeScript 在某些对象合并场景下推断失稳，导致 `Paper` 的 `sx` 类型不匹配。

修复策略：

- 保持现有视觉样式不变。
- 将 `sx={{ ...a, ...b, ... }}` 这种高风险写法改为更稳定的 MUI `sx` 组合方式（如数组组合或显式局部对象整理）。
- 避免为了绕过类型问题使用粗暴 `as any`。

成功标准：

- `cd frontend && npm run build` 通过。

## 2. Docker 文件设计

### 2.1 前端 Dockerfile

前端采用多阶段构建：

1. **build 阶段**
   - 基于 Node 镜像
   - 安装依赖
   - 执行 `npm run build`
2. **runtime 阶段**
   - 基于 Nginx 镜像
   - 提供静态资源
   - 暴露 HTTP 端口

原因：

- Vite 项目最终产物是静态文件，使用 Nginx 作为运行时更轻量。
- 能把构建依赖与运行时隔离，减小镜像体积。

### 2.2 后端 Dockerfile

后端采用 Python 基础镜像：

- 安装 `backend/requirements.txt`
- 复制后端代码
- 配置工作目录与必要环境变量
- 默认使用 `uvicorn app.main:app --host 0.0.0.0 --port 8000`

原因：

- 与当前项目结构兼容。
- 便于在 compose 中统一接入数据库和图谱服务。

## 3. Compose 设计

### 3.1 默认部署模式：`docker-compose.yml`

默认部署模式包含以下服务：

- `postgres`
- `neo4j`
- `backend`
- `frontend`

要求：

- PostgreSQL / Neo4j 使用官方镜像。
- frontend / backend 使用本仓库 Dockerfile 构建。
- backend 依赖 `postgres` 与 `neo4j`。
- frontend 依赖 `backend`。
- 使用 volume 持久化数据库数据。

数据持久化策略：

- PostgreSQL：`postgres_data`
- Neo4j：`neo4j_data`、`neo4j_logs`

这样做的结果是：

- 容器删除后，只要 volume 不删，数据库数据依然保留。
- 别人启动的是自己本机上的独立数据库实例，而不是你的个人数据库副本。

### 3.2 开发模式：`docker-compose.dev.yml`

开发模式作为覆盖层，基于默认 compose 增加：

- 前端源码挂载，运行开发命令
- 后端源码挂载，运行开发命令
- 暴露更适合调试的端口与命令

建议使用方式：

- `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`

目标：

- 你在本地开发时无需反复重建生产镜像。
- 对外默认交付仍保持部署模式简单清晰。

## 4. 环境变量设计

### 4.1 根目录 `.env`

根目录 `.env` 用于 Docker Compose 级别参数，例如：

- Postgres 用户名 / 密码 / 库名
- Neo4j 用户名 / 密码
- 前后端对外端口

### 4.2 后端运行时环境变量

后端仍保留 `backend/.env.example` 作为详细配置参考。

在 Docker 场景下，compose 需要显式为 backend 注入至少这些关键项：

- `DATABASE_URL`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- 模型 API 相关变量（如用户需要启用）

策略：

- 尽量复用现有 `.env.example` 含义。
- README 里明确说明：不开启模型能力时，某些变量可留空或使用 mock / 降级配置（若现有代码允许）。

## 5. 一键启动脚本设计

### 5.1 `start.bat`

面向 Windows 用户：

1. 检查根目录 `.env` 是否存在
2. 若不存在，则从 `.env.example` 复制一份
3. 执行 `docker compose up -d --build`
4. 输出主要访问地址与后续操作提示

### 5.2 `start.sh`

面向 Mac / Linux 用户：

执行逻辑与 `start.bat` 保持一致。

### 5.3 脚本边界

脚本只负责：

- 准备 compose 运行所需的最小入口
- 启动服务
- 给出结果提示

脚本不负责：

- 自动安装 Docker 本体
- 自动注册系统服务
- 自动导入你的真实数据

## 6. 本地测试与验证设计

至少执行以下验证：

1. **前端构建验证**
   - `cd frontend && npm run build`

2. **Compose 配置验证**
   - `docker compose config`

3. **部署模式启动验证**
   - `docker compose up -d --build`
   - 检查 `postgres`、`neo4j`、`backend`、`frontend` 是否正常运行

4. **必要健康检查 / 日志检查**
   - backend 至少应能启动并监听端口
   - frontend 容器应能提供静态页面

如果验证过程中发现外部依赖限制（例如模型 API Key 缺失、后端必须依赖未配置服务），则需要：

- 尽量为本地验证提供最小可运行配置
- 若无法完全规避，则在 README 中明确说明启动前置条件

## 7. README 更新范围

README 需新增或修订以下内容：

- Docker 部署模式启动方式
- Docker 开发模式启动方式
- 根目录 `.env` 的作用
- backend `.env` / API Key 配置说明
- 数据库 volume 持久化说明
- Windows / Mac / Linux 一键启动脚本用法
- 常见问题：
  - 容器起来但后端无法连数据库
  - Neo4j 密码不匹配
  - 模型能力未配置导致部分功能不可用

## 风险与边界

### 1. 后端真实运行依赖较多

如果后端当前在启动时强依赖某些模型配置或外部服务，本次不会重构整套配置体系，只会：

- 采用尽量小的兼容配置
- 在 README 中明确最小运行条件

### 2. 前端构建错误修复应保持最小变更

本次只修复已知类型问题，不做无关 UI 重构。

### 3. 不提交测试数据库文件

当前仓库中存在：

- `backend/test_graph_retrieval.db`
- `test_graph_retrieval.db`

这类本地测试产物不应纳入最终提交，需要排除。

## 实施范围

### 包含内容

- 修复前端两个构建错误
- 删除 daily-review 搜索框（已确认需求）
- 新增前端 Dockerfile
- 新增后端 Dockerfile
- 扩展默认 `docker-compose.yml`
- 新增 `docker-compose.dev.yml`
- 新增 `start.bat` / `start.sh`
- 更新 README
- 本地验证构建与 Docker 启动

### 不包含内容

- 云部署脚本
- 生产监控 / 日志系统
- 自动化发布流水线
- 个人数据库内容导出与分发

## 成功标准

- 前端 `npm run build` 通过。
- Docker 默认模式可启动完整服务栈。
- 开发模式配置存在且可用于本地源码挂载开发。
- README 能让新用户理解如何一键启动与如何持久化数据。
- 相关变更可整理后提交并推送到 GitHub。