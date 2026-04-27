# 项目约定

## 文档与上下文

- 所有改动、上下文、tradeoff、背景信息统一记录到 `docs/ai/context/`
- 设计、重构、技术选型先补上下文，再落代码

## 前端 API 约定

- 前端只保留一个底层 HTTP client，统一处理 `baseURL`、错误归一化、JSON 请求和查询参数
- `frontend/src/services/*Api.ts` 负责表达业务语义，不负责各自实现一套请求基座
- 普通接口禁止继续新增 `axios + buildApiUrl` 或 `fetch(buildApiUrl(...))` 直连写法
- 流式接口可以保留传输层特例，但必须复用统一的 URL 规范和错误规范
- hooks 和页面层默认只消费领域 API，不直接发后端请求

## 本地与 Docker 端口约定

- 前端固定使用 `5173`：本地开发、Docker 映射、文档说明和联调入口都必须以 `http://127.0.0.1:5173` 或 `http://localhost:5173` 为准
- 后端固定使用 `8000`：本地开发、Docker 映射、前端 `VITE_API_BASE_URL` 默认值和联调入口都必须以 `http://127.0.0.1:8000` 或 `http://localhost:8000` 为准
- 不要把前端临时启动到 `5174/5180/5181` 作为交付入口；这些端口只能作为短时排障备用，排障后必须停止
- 如果 `5173` 或 `8000` 被占用，先确认是否已有项目 Docker 服务在运行；不要绕到新端口交付，除非用户明确批准
- Docker Compose 默认端口必须保持 `FRONTEND_PORT=5173`、`BACKEND_PORT=8000`，避免后端、Docker 和浏览器入口不一致
- 后端 CORS 放行列表必须覆盖 `http://localhost:5173` 和 `http://127.0.0.1:5173`，5173 是前端唯一默认联调端口

## 环境变量约定

- 根目录 `.env` 是唯一运行时配置源；不要再创建或维护 `backend/.env`、`frontend/.env` 作为第二套配置
- 设置页保存模型配置时必须写回根目录 `.env`
- 后端本地运行默认读取根目录 `.env`；Docker 后端通过 `PKB_ENV_FILE=/workspace/.env` 挂载并读取同一份文件
- Docker 容器内的 `DATABASE_URL` 和 `NEO4J_URI` 由 Compose 注入容器网络地址；模型配置仍以根目录 `.env` 为准
- 根目录 `.env.example` 是唯一环境变量模板；新增变量时只更新这一份模板

## 启动避坑

- `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` 必须保证前端最终直接映射到宿主机 `5173`
- `docker-compose.dev.yml` 已用 `ports: !override` 覆盖基础 `frontend` 端口，开发模式下 `5173` 应直接指向 Vite，而不是基础 Nginx 容器
- 开发模式的正确验收入口只有 `http://127.0.0.1:5173`
- 如果 `5173` 已被旧的 `pkb-frontend-dev` 或其他历史进程占用，先停掉旧容器或旧进程，再重新执行 compose 启动；不要改用 `5174/5180/5181` 交付
- 修改 `docker-compose.yml` 或 `docker-compose.dev.yml` 后，必须重建受影响容器；例如后端环境挂载变化后执行：`docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps --force-recreate backend`
- 如果设置页返回的模型配置和根目录 `.env` 不一致，优先检查 `docker inspect pkb-backend` 是否已经挂载 `/.env -> /workspace/.env`，旧容器可能仍保留历史环境变量覆盖项
- 如果只想本地跑前端，也允许保留后端 Docker，再在当前工作区执行：`cd frontend && npm install && npm run dev -- --host 127.0.0.1 --port 5173`
- 如果前端命令报 `vite is not recognized as an internal or external command`，说明本地依赖没有装完整；先执行 `npm install`，必要时直接用 `frontend/node_modules/.bin/vite.cmd --host 127.0.0.1 --port 5173 --strictPort`
- 启动完成后必须同时验证：
- 前端首页：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8000/health`

## 当前决策记忆

- 2026-04-19：确认前端 API 收敛方案采用“单一 HTTP client + 按领域拆分 `*Api.ts` 模块”，先收口 `services/` 内部边界，不改 hooks 对外接口
- 2026-04-23：合并 `feature/graph-history-v2-v3` 到 `main` 时，保留 `relation_topic` 的 minimal 模式，同时并入实体历史增强与测试并集，避免功能回退
- 2026-04-25：设置页模型配置扩展为可编辑 `provider/base_url/model/reasoning_effort/api_key` 全量字段；公网转发预设默认使用 `cliproxyapi + https://api.aaccx.pw/v1 + gpt-5.4 + xhigh`，真实密钥仅允许落本地环境文件
- 2026-04-25：设置页后续交互采用“模型厂商下拉作为预设模板 + API URL 可覆盖 + API Key 可选 + 推理强度作为高级参数”的设计，`provider` 不作为硬编码能力开关
- 2026-04-25：本地 OpenAI 兼容模型允许 API Key 留空；后端用 `not-needed` 占位初始化客户端，云端鉴权错误交给上游响应和统一错误归一化处理
- 2026-04-25：确认 memories 页入图调用 `POST /api/memories/{id}/add-to-graph` 正常，chat 页对话调用 `POST /api/chat/stream` 正常；路由级测试禁止启动真实 lifespan worker
- 2026-04-27：后端模型 API 配置统一收敛到 `ModelRuntimeGateway`；chat/标题/文本优化/引用/知识画像使用 `dialog` runtime，Graphiti 入图和 reranker 使用 `knowledge_build` runtime，业务流程不直接读取模型配置字段
- 2026-04-27：模型 API 运行时收敛到 `ModelRuntimeGateway`，chat 使用 `dialog` runtime，memories 入图使用 `knowledge_build` runtime；后续 API URL/Key/model/reasoning 参数变化优先改运行时网关
- 2026-04-27：确认项目默认联调端口固定为前端 `5173`、后端 `8000`；不得用 `5174/5180/5181` 作为交付入口
- 2026-04-27：知识图谱页面默认加载上限统一为 `1000` 条关系；后端图谱可视化先按 `group_id` 返回节点再返回稳定排序后的边，避免孤立节点因无关系被隐藏
- 2026-04-27：知识图谱前端渲染层切换优先走 `sigma + graphology` 基础版，先保留现有 `GraphData` 和详情侧栏交互，再逐步迭代图片节点、自定义 shader 和布局 worker
- 2026-04-27：Graph 页面已移除 `reactflow` 依赖与残留组件，知识图谱展示统一收敛到 `sigma + graphology` 一条渲染链路
- 2026-04-27：已修正 `docker-compose.dev.yml` 的前端端口覆盖方式，开发叠加模式下宿主机 `5173` 直接映射到 Vite `5173`，不再保留 `5174` 作为默认开发入口
- 2026-04-27：环境变量收敛到根目录 `.env` 作为唯一运行时配置源；已移除 `backend/.env.example`，后端设置页和 Docker 后端都读写同一份根目录 `.env`
