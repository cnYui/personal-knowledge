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

## 推荐启动方式

- 日常本地开发默认使用：后端 Docker + 前端宿主机 Vite
- 原因：后端依赖数据库和 Neo4j，放 Docker 更稳；前端宿主机启动更快，避免 dev 容器每次 `npm ci`

### 标准步骤

- 先确认 `5173` 和 `8000` 没有被旧容器或旧进程占用；优先用 `docker ps --format "table {{.Names}}\t{{.Ports}}"` 定位占用者
- 后端启动：`docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps --force-recreate backend`
- 前端启动：`cd frontend && npm install && npm run dev -- --host 127.0.0.1 --port 5173`
- 启动完成后必须验证：
- 前端：`curl.exe -i --max-time 20 http://127.0.0.1:5173`
- 后端：`curl.exe -i --max-time 20 http://127.0.0.1:8000/health`

### 必要前提

- `docker-compose.dev.yml` 的 `frontend` 端口覆盖必须保持宿主机 `5173 -> Vite 5173`
- 修改 `docker-compose.yml` 或 `docker-compose.dev.yml` 后，必须重建受影响容器
- 如果本地前端缺依赖，先执行 `npm install`，不要切到 `5174/5180/5181`

### 详细排障

- 详细启动排障见：
- `docs/ai/context/2026-04-29-local-main-startup-troubleshooting.md`
- 启动慢原因和后端加速方案见：
- `docs/ai/context/2026-04-29-startup-performance-analysis.md`

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
- 2026-04-27：Graph 页面布局不再使用固定环形坐标，当前采用 `ForceAtlas2` 力导布局；环形坐标仅作为初始种子位置
- 2026-04-27：Graph 节点视觉权重默认按 `degree` 做 `log2(degree + 1)` 尺寸映射，标签显示按相机缩放分三档控制 `top 10% / 25% / 50%` 分位数，`degree <= 1` 节点默认不常显标签
- 2026-04-27：Graph 自动刷新联动优先采用“memories 轮询状态 + 前端协调层触发 `invalidateQueries(['graph-data'])`”方案，覆盖“graph 页已打开自动刷新”和“之后进入 graph 页直接看到最新图谱”，当前不引入 SSE / WebSocket
- 2026-04-27：Graph 自动刷新协调层最终拆为 `useGraphRefreshCoordinator + graphRefreshTracker`；其中 memories 轮询只能在存在 tracked memory 时启用，禁止因全局 provider 挂载而产生常驻轮询
- 2026-04-27：已修正 `docker-compose.dev.yml` 的前端端口覆盖方式，开发叠加模式下宿主机 `5173` 直接映射到 Vite `5173`，不再保留 `5174` 作为默认开发入口
- 2026-04-27：环境变量收敛到根目录 `.env` 作为唯一运行时配置源；已移除 `backend/.env.example`，后端设置页和 Docker 后端都读写同一份根目录 `.env`
- 2026-04-27：Graphiti 入图 worker 必须维护 memory 级别的排队/执行去重，禁止同一 memory 在 `pending` 期间重复入队；本地 sentence-transformers embedding 必须放到线程池执行，不能直接阻塞 FastAPI 事件循环
- 2026-04-29：本地重启 `main` 分支时确认端口占用优先从 Docker 容器定位；`poco-claw-backend-1` 可占用 `8000`，旧 `pkb-frontend-dev` 可占用 `5173`。重启当前分支时必须确保数据库容器和后端/frontend 处于同一个 compose 网络，否则后端无法解析 `postgres/neo4j`
- 2026-04-29：本地开发默认启动方式改为“后端 Docker + 前端宿主机 Vite”；`pkb-frontend-dev` 只保留给需要容器化前端时使用，不再作为日常默认入口
- 2026-04-29：后端慢启动的根因是图谱相关客户端初始化时机过早：`graph` 路由模块级 `GraphVisualizationService()` 会在 import 阶段触发 `GraphitiClient -> LocalEmbedder`，而 `GraphitiIngestWorker` 在 startup step 1 里也会再次初始化图谱客户端。后续优化必须优先改成懒加载，而不是继续接受启动期同步加载 embedding 模型
- 2026-04-29：后端启动懒加载已落地：`graph` 路由不再模块级持有 `GraphVisualizationService`，`GraphVisualizationService` 默认不再创建 `GraphitiClient`，`GraphitiIngestWorker` 改为首次入图时才初始化图谱客户端，startup 顺序也调整为“先恢复 pending 队列、先起标题 worker、最后再启动图谱 worker 消费循环”
- 2026-04-29：Chat 页面新消息自动滚动放在 `ChatMessageList` 内部，通过列表底部锚点在 `messages.length` 增加时触发；初次渲染不滚动，流式内容增量不触发滚动，避免打断用户阅读
- 2026-04-29：Chat 流式失败收尾问题先按“结构化 SSE error + 前端稳定结束 loading”收口，范围只覆盖主流程与后台 task 异常的统一传递，不在本轮设计中扩展上游 `502` 重试/退避/降级策略
- 2026-04-29：`chat` 页面清空聊天记录统一复用 `useClearChatMessages + ConfirmDialog`，危险操作放在页面顶部操作区，并在发送中或清空中禁用，避免误触和流式竞态
- 2026-04-29：Chat 分层协议剩余实现不能只补 `tool_use/tool_result` 内联卡片；必须同时修复三项行为：无命中时隐藏参考引用、`probe-retrieval` 类 timeline 必须补完成态、带有序列表或强调语法的回答必须继续走 Markdown 渲染，不能误降级到句子模式
