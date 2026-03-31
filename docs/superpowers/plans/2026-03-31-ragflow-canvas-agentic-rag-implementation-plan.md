# RAGFlow Canvas Agentic RAG Implementation Plan

> Goal: 在 `personal-knowledge-base` 中落地第一版 RAGFlow 风格的 Agentic RAG 运行时，先建立通用 `Canvas` 内核，再让聊天主链运行在该内核之上。

## 1. 实施原则

1. 先立运行时，再接聊天业务
2. 先落最小节点集，不扩节点库
3. 先让后端执行语义稳定，再对接前端 trace / citation 展示
4. 不继续把逻辑堆进旧 `AgentService`
5. 每个阶段都要求有可验证产物

## 2. P0 总目标

P0 完成后，系统应满足：

- 存在通用 `Canvas`
- 存在通用 `RuntimeContext`
- 存在全局 `ReferenceStore`
- 存在独立 `ToolLoopEngine`
- 存在 `AgentNode / RetrievalNode / MessageNode / BeginNode`
- 聊天主链已切到 `Canvas.run()`
- 最终回答支持 citation 后处理
- trace 能展示节点与 tool 调用过程

## 3. 文件结构目标

### 新增目录

```text
backend/app/workflow/
backend/app/workflow/nodes/
backend/app/workflow/engine/
backend/app/workflow/templates/
backend/tests/workflow/
```

### 核心文件

```text
backend/app/workflow/canvas.py
backend/app/workflow/runtime_context.py
backend/app/workflow/reference_store.py
backend/app/workflow/events.py
backend/app/workflow/dsl.py

backend/app/workflow/nodes/base.py
backend/app/workflow/nodes/begin_node.py
backend/app/workflow/nodes/agent_node.py
backend/app/workflow/nodes/retrieval_node.py
backend/app/workflow/nodes/message_node.py

backend/app/workflow/engine/tool_loop.py
backend/app/workflow/engine/citation_postprocessor.py

backend/app/workflow/templates/chat_agentic_rag.json
```

## 4. 阶段拆分

### 阶段 1：Canvas 基础内核

**目标：** 建立通用工作流运行容器和上下文对象。

**新增文件：**

- `backend/app/workflow/runtime_context.py`
- `backend/app/workflow/reference_store.py`
- `backend/app/workflow/events.py`
- `backend/app/workflow/dsl.py`
- `backend/app/workflow/canvas.py`

**任务：**

- 定义 `RuntimeContext`
  - `sys.query`
  - `sys.history`
  - `sys.files`
  - `sys.user_id`
  - `globals`
- 定义 `ReferenceStore`
  - chunks
  - doc aggs
  - graph evidence
  - add / merge / clear / snapshot
- 定义最小 workflow DSL 数据结构
- 定义 `Canvas`
  - 加载模板
  - 节点注册
  - 顺序执行
  - 事件输出

**测试：**

- `backend/tests/workflow/test_runtime_context.py`
- `backend/tests/workflow/test_reference_store.py`
- `backend/tests/workflow/test_canvas_basic.py`

**完成标准：**

- `Canvas` 能顺序执行一个最小 workflow
- 节点间能共享上下文
- `ReferenceStore` 能独立增删读写

### 阶段 2：节点抽象与基础节点

**目标：** 建立通用节点模型，并让最小聊天主链可以被表达。

**新增文件：**

- `backend/app/workflow/nodes/base.py`
- `backend/app/workflow/nodes/begin_node.py`
- `backend/app/workflow/nodes/retrieval_node.py`
- `backend/app/workflow/nodes/message_node.py`

**任务：**

- 定义 `Node` 基类
  - `execute()`
  - `validate()`
  - `to_event_payload()`
- 实现 `BeginNode`
  - 注入 query / history / files
- 实现 `RetrievalNode`
  - 复用现有图谱检索能力
  - 将证据写入 `ReferenceStore`
- 实现 `MessageNode`
  - 读取最终答案
  - 输出 message / message_end 所需结构

**测试：**

- `backend/tests/workflow/nodes/test_begin_node.py`
- `backend/tests/workflow/nodes/test_retrieval_node.py`
- `backend/tests/workflow/nodes/test_message_node.py`

**完成标准：**

- `Begin -> Retrieval -> Message` 可以作为最小 workflow 执行
- `RetrievalNode` 确实向 `ReferenceStore` 写入证据

### 阶段 3：独立 ToolLoopEngine

**目标：** 将工具循环从旧 Agent 逻辑中独立出来，形成通用能力。

**新增文件：**

- `backend/app/workflow/engine/tool_loop.py`

**任务：**

- 封装 LLM tool-calling 循环
- 支持：
  - tools 注册
  - 多轮 tool call
  - tool result 回填 history
  - `max_rounds`
  - tool trace
- 将现有 `AgentService` 中与 tool loop 相关的能力迁移到这里

**测试：**

- `backend/tests/workflow/engine/test_tool_loop.py`

**完成标准：**

- 能模拟：
  - 无 tool call 直接回答
  - 一轮 tool call 后回答
  - 多轮 tool call 后回答
  - 超过 `max_rounds` 兜底

### 阶段 4：AgentNode

**目标：** 建立真正的 `AgentNode` 抽象，让 Agent 变成工作流节点，而不是服务层私有逻辑。

**新增文件：**

- `backend/app/workflow/nodes/agent_node.py`

**任务：**

- `AgentNode` 负责：
  - 组装 prompt
  - 读取 `RuntimeContext`
  - 注册 tools
  - 调用 `ToolLoopEngine`
  - 将中间结果写回上下文
- 将 `RetrievalNode` 以 tool 形式挂给 `AgentNode`
- 沿用当前闲聊 / 默认查库 / 证据不足 fallback 策略

**测试：**

- `backend/tests/workflow/nodes/test_agent_node.py`

**完成标准：**

- `Begin -> Agent -> Message` 能执行
- `AgentNode` 能驱动 `RetrievalNode` 作为 tool
- 非闲聊问题默认进入检索路径

### 阶段 5：CitationPostProcessor

**目标：** 将“回答生成”和“引用整理”拆开，复刻 RAGFlow 的 citation 后处理模式。

**新增文件：**

- `backend/app/workflow/engine/citation_postprocessor.py`

**任务：**

- 读取最终答案
- 读取 `ReferenceStore`
- 生成 citation 上下文
- 产出：
  - 带 citation 的文本
  - 或结构化 citation 数据
- 明确 fallback 回答和知识库引用的边界

**测试：**

- `backend/tests/workflow/engine/test_citation_postprocessor.py`

**完成标准：**

- citation 不依赖单次 retrieval 的即时返回
- 多轮 retrieval 证据能统一进入 citation 阶段

### 阶段 6：聊天主链接入 Canvas

**目标：** 将现有聊天主执行入口切到 `Canvas`。

**修改文件：**

- `backend/app/services/chat_service.py`
- `backend/app/routers/chat.py`
- 可能新增：
  - `backend/app/workflow/templates/chat_agentic_rag.json`
  - `backend/app/workflow/canvas_factory.py`

**任务：**

- 定义聊天 workflow 模板：
  - `BeginNode -> AgentNode -> MessageNode`
- 在聊天请求进入时创建 `Canvas`
- 通过 `Canvas.run()` 驱动整个流程
- 保持现有 API 结构尽量兼容

**测试：**

- `backend/tests/test_chat_api.py`
- `backend/tests/workflow/test_chat_canvas_integration.py`

**完成标准：**

- 聊天主链不再直接以旧 `AgentService` 为唯一执行入口
- 流式返回仍能正常工作

### 阶段 7：Trace 与前端对接

**目标：** 让新的运行模型可以被看到、被解释。

**后端修改：**

- 将节点事件、tool 事件、citation 事件统一暴露

**前端修改：**

- 复用当前 trace 面板
- 新增：
  - 节点执行信息
  - tool loop 信息
  - citation post-process 信息

**测试：**

- API 事件序列测试
- 页面级手动验证

**完成标准：**

- 用户能在前端分清：
  - 哪个节点执行了
  - 是否调用了 retrieval
  - 是否走了 fallback
  - citation 是否来自证据池

## 5. P1 扩展顺序

P0 完成后，P1 按以下顺序推进：

1. `LLMNode`
2. `ConditionNode`
3. `LoopNode`
4. `FallbackNode`
5. `MemoryNode`
6. 分支与条件跳转
7. 证据融合增强
8. citation 精细化
9. 通用 tool registry
10. workflow 模板库
11. 更强的调试面板

## 6. 需要复用与拆解的现有能力

### 直接复用

- `KnowledgeGraphService`
- `GraphitiClient`
- 现有聊天 API
- 现有流式返回机制

### 拆解迁移

- 旧 `AgentService`
  - prompt 组织逻辑迁入 `AgentNode`
  - tool loop 逻辑迁入 `ToolLoopEngine`
  - fallback 策略保留，但移到新运行时中

## 7. 风险控制

### 风险 1：范围失控

**控制：**
- P0 只落 4 个基础节点
- 不引入工作流编辑器

### 风险 2：旧链路与新链路行为不一致

**控制：**
- 在聊天切换到 `Canvas` 前，先完成独立 workflow 集成测试

### 风险 3：citation 与 fallback 语义混乱

**控制：**
- fallback 内容必须显式标识
- citation 只引用真实证据池内容

### 风险 4：重构期调试困难

**控制：**
- 每阶段都保留可运行测试
- trace 先后端统一，再前端渲染

## 8. 推荐提交节奏

建议按阶段提交，而不是一次性大提交：

1. `feat: add canvas runtime core`
2. `feat: add workflow base nodes`
3. `feat: add tool loop engine`
4. `feat: add agent node for canvas workflows`
5. `feat: add citation post processor`
6. `refactor: route chat flow through canvas runtime`
7. `feat: expose canvas trace and citation events`

## 9. 验收清单

- [ ] `Canvas` 可加载并执行最小 workflow
- [ ] `ReferenceStore` 能累积多轮 retrieval 证据
- [ ] `ToolLoopEngine` 支持多轮 tool call
- [ ] `AgentNode` 能绑定 `RetrievalNode` 作为 tool
- [ ] `CitationPostProcessor` 可在回答后补引用
- [ ] 聊天主链运行在 `Canvas.run()` 上
- [ ] trace 可展示节点 / tool / citation 流程
- [ ] fallback 与知识库回答边界清晰

## 10. 结论

本计划不追求在 P0 做成完整 RAGFlow 替代品，而是优先建立：

- 通用 `Canvas`
- 通用节点系统
- 独立 `ToolLoopEngine`
- 全局 `ReferenceStore`
- 回答后 citation

并让聊天 Agentic RAG 成为运行在该底座上的第一条 workflow。

这既能最大程度贴近 RAGFlow 的核心机制，又能控制落地风险，避免把现有项目拖入一次不可收敛的大重构。
