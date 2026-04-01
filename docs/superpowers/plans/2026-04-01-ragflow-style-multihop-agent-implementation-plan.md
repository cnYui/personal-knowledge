# RAGFlow Style Multi-Hop Agent Implementation Plan

> Goal: 在 `personal-knowledge-base` 中移除当前折中的 `keyword shortcut + planner + partial tool loop` 结构，重构为最接近 RAGFlow 的单工具、真 tool loop、多轮自主检索 Agent。

## 1. 实施原则

1. 先改后端运行机制，再改前端 trace 呈现
2. 先让 `AgentNode` 真正只依赖 tool loop，再清理遗留 prompt / rule
3. 先保证 `ReferenceStore` 与 citation 不被打坏，再去掉 planner 分支
4. 不继续扩工具，第一版只保留 `graph_retrieval_tool`
5. 每个阶段都必须有清晰的测试或手工验证产物

## 2. P0 总目标

P0 完成后，系统应满足：

- 主聊天链路不再依赖 `CHITCHAT_PREFIXES`
- 主聊天链路不再依赖 `QUESTION_PLANNING_SYSTEM_PROMPT`
- `AgentNode` 的主控制路径改为 `ToolLoopEngine`
- `graph_retrieval_tool` 成为唯一知识工具
- 模型可以在多轮中自主决定是否继续检索
- 每轮检索结果都会写入 `ReferenceStore`
- 最终答案继续经过 `CitationPostProcessor`
- trace 能展示真实 tool loop 行为，而不是 planner 分支

## 3. 文件结构目标

### 重点修改文件

```text
backend/app/workflow/nodes/agent_node.py
backend/app/workflow/engine/tool_loop.py
backend/app/services/agent_prompts.py
backend/app/services/chat_service.py
backend/app/workflow/engine/citation_postprocessor.py

backend/tests/workflow/nodes/test_agent_node.py
backend/tests/workflow/engine/test_tool_loop.py
backend/tests/test_chat_api.py

frontend/src/components/chat/ChatMessageList.tsx
frontend/src/types/chat.ts
frontend/src/services/chatApi.ts
frontend/src/hooks/useChat.ts
```

### 预计基本保持不动的文件

```text
backend/app/workflow/canvas.py
backend/app/workflow/runtime_context.py
backend/app/workflow/reference_store.py
backend/app/workflow/canvas_factory.py
backend/app/workflow/templates/chat_agentic_rag.json
backend/app/services/agent_tools/graph_retrieval_tool.py
```

## 4. 阶段拆分

### 阶段 1：去掉本地关键词短路

**目标：** 移除当前 Agent 主链上的本地规则路由，让所有输入都进入真正的 Agent 决策路径。

**修改文件：**

- `backend/app/workflow/nodes/agent_node.py`
- `backend/app/services/agent_prompts.py`

**任务：**

- 删除或停用：
  - `CHITCHAT_PREFIXES`
  - `FORCE_KB_TRIGGER_PHRASES`
  - `is_obvious_chitchat()`
  - `is_force_kb_query()`
  - `_build_chitchat_answer()`
- 确保所有输入都先进入 `AgentNode` 的统一决策链
- 保证“你好 / 你是谁”这类问题仍能自然回答，但不再依赖本地关键词短路

**测试：**

- 更新 `backend/tests/workflow/nodes/test_agent_node.py`
- 增加：
  - 问候语进入 agent decision path 的测试
  - 身份类问题可自然回答但不依赖关键词表的测试

**完成标准：**

- 聊天主链不再先看本地关键词表
- 问候语与身份类问题仍然可正常回答

### 阶段 2：去掉显式 planner JSON 路由

**目标：** 移除 `direct / retrieve / decompose` 这套 planner-first 结构。

**修改文件：**

- `backend/app/workflow/nodes/agent_node.py`
- `backend/app/services/agent_prompts.py`
- `backend/app/schemas/agent.py`

**任务：**

- 删除或停用：
  - `QUESTION_PLANNING_SYSTEM_PROMPT`
  - `_plan_question()`
  - `_answer_directly()`
  - `_merge_retrieval_results()`
  - planner 相关 trace 结构
- 清理 `AgentQuestionPlan` 在主流程中的使用
- 把 `AgentNode` 从“显式分支执行器”收敛成“tool loop 容器”

**测试：**

- 删除/更新依赖 planner 的单测
- 增加：
  - 没有 planner JSON 也能完成 direct answer
  - 没有 planner JSON 也能完成 retrieval answer

**完成标准：**

- 主聊天运行路径中不再有 `direct / retrieve / decompose` JSON route
- 主流程由 tool loop 驱动

### 阶段 3：增强 ToolLoopEngine 成为核心执行器

**目标：** 让 `ToolLoopEngine` 成为真正的多轮工具决策核心，最接近 RAGFlow。

**修改文件：**

- `backend/app/workflow/engine/tool_loop.py`
- `backend/tests/workflow/engine/test_tool_loop.py`

**任务：**

- 保证每一轮都完整保留：
  - assistant message
  - tool call
  - tool result
  - updated history
- 支持同一工具多轮重复调用
- 明确 `max_rounds` 上限行为
- 输出更完整的 loop trace：
  - round index
  - tool name
  - args
  - result summary
  - stop reason
  - exceeded max rounds

**测试：**

- 直接回答，无 tool call
- 一轮 retrieval 后回答
- 多轮 retrieval 后回答
- 超过 `max_rounds` 后受控结束

**完成标准：**

- `ToolLoopEngine` 可以独立支撑“检索 -> 再检索 -> 回答”的多跳行为
- 不再需要 `AgentNode` 自己在外部写多轮逻辑

### 阶段 4：重写 AgentNode 为纯 tool-loop Agent

**目标：** 让 `AgentNode` 只负责组装会话与调用 `ToolLoopEngine`。

**修改文件：**

- `backend/app/workflow/nodes/agent_node.py`
- `backend/tests/workflow/nodes/test_agent_node.py`

**任务：**

- `AgentNode` 只做：
  - 组装 system prompt
  - 组装 history
  - 注册 `graph_retrieval_tool`
  - 调 `ToolLoopEngine`
  - 根据 loop 结果输出 answer / references / trace
- 不再自己做分支式 direct / retrieve / decompose
- 把“是否继续检索、是否改写 query、何时停止”交给模型在 tool loop 中决定

**测试：**

- 问候类问题：可自然回答，且由 loop/LLM 决定
- 单知识问题：可触发单轮检索
- 复杂问题：可触发多轮检索
- 证据不足：可回退通用补充回答

**完成标准：**

- `AgentNode` 成为纯 tool-loop agent
- 代码里不再存在 planner-first 主控制路径

### 阶段 5：保留并强化 ReferenceStore / Citation 路径

**目标：** 保证多轮检索证据持续累积，并继续在最终回答后补 citation。

**修改文件：**

- `backend/app/workflow/nodes/agent_node.py`
- `backend/app/workflow/engine/citation_postprocessor.py`
- `backend/app/services/chat_service.py`

**任务：**

- 确保每轮 `graph_retrieval_tool` 调用都写入 `ReferenceStore`
- 验证多轮检索时证据不会丢失
- 继续在最终答案后做 citation
- citation 基于整场会话证据池，而不是最后一轮结果

**测试：**

- 多轮 retrieval 后 `ReferenceStore` 包含累积证据
- citation 输出与证据池一致
- fallback 回答仍能正确标识是否使用了通用补充

**完成标准：**

- `ReferenceStore` 在多轮 tool loop 中稳定累积
- citation 仍然工作且基于全局证据池

### 阶段 6：trace 改为真实 tool-loop 语义

**目标：** 让后端 trace 和前端思维链展示反映真实的 loop，而不是 planner 阶段。

**修改文件：**

- `backend/app/services/chat_service.py`
- `frontend/src/components/chat/ChatMessageList.tsx`
- `frontend/src/types/chat.ts`
- `frontend/src/hooks/useChat.ts`
- `frontend/src/services/chatApi.ts`

**任务：**

- 后端 trace 去掉 planner-first 描述
- 前端生成中摘要改为：
  - 正在决定是否检索
  - 第 N 轮检索中
  - 正在评估证据是否充足
  - 正在组织最终回答
- 最终展开面板展示真实 tool loop 轨迹

**测试：**

- 手动验证聊天页思考过程
- API trace 结构验证

**完成标准：**

- UI 可见的思考过程与真实 runtime 一致
- 不再展示 planner 风格步骤

### 阶段 7：主链联调与回归验证

**目标：** 确保完整重构后聊天、引用、图谱证据与设置页不被打坏。

**任务：**

- 跑通关键接口：
  - `/api/chat/rag`
  - `/api/chat/stream`
- 覆盖场景：
  - `你好`
  - `你是谁`
  - 单知识问题
  - 多轮检索问题
  - 知识不足 fallback 问题
- 确保：
  - `ReferenceStore` 正常
  - citation 正常
  - 前端可展示思维链与最终轨迹

**测试：**

- `backend/tests/test_chat_api.py`
- 页面级手工验证

**完成标准：**

- 主链稳定可用
- 不再依赖本地关键词和 planner
- 行为接近 RAGFlow 的单工具多跳 agent

## 5. P1 扩展顺序

P0 完成后，P1 建议按以下顺序推进：

1. 调优主 Agent prompt，减少无效检索
2. 改善 query rewrite 的自然性和命中率
3. 前端思维链展示进一步贴近真实轮次
4. 将 citation 与具体 round 建立更细的对应关系
5. 为未来第二个工具预留 registry 抽象

## 6. 需要复用与拆解的现有能力

### 直接复用

- `Canvas`
- `RuntimeContext`
- `ReferenceStore`
- `CitationPostProcessor`
- `GraphRetrievalTool`
- `CanvasFactory`
- 现有聊天 API 入口

### 需要拆解迁移

- `AgentNode` 当前的 planner-first 逻辑
- `agent_prompts.py` 当前的 keyword/planner 规则
- 前端当前基于 planner 的思维链文案

## 7. 风险控制

1. 去掉 planner 后，模型行为短期内可能更不稳定
2. Prompt 调整会直接影响检索轮数与停止时机
3. 多轮 tool loop 更容易暴露 trace 与 UI 不一致问题
4. 如果 `max_rounds` 和提示词不平衡，可能出现过检索或欠检索

控制策略：

- 每个阶段先补测试再切换主路径
- 先只保留一个工具，降低自由度
- 保留 `max_rounds` 作为强兜底
- 每次变更后都做真实接口 smoke test

## 8. 完成定义

整个 P0 算完成，必须同时满足：

- `CHITCHAT_PREFIXES` 不再作为主链路控制器
- `QUESTION_PLANNING_SYSTEM_PROMPT` 不再作为主链路控制器
- `AgentNode` 的核心路径是 `ToolLoopEngine`
- 模型可以在同一问题下进行多轮 `graph_retrieval_tool` 调用
- 多轮结果稳定进入 `ReferenceStore`
- 最终回答继续经过 citation 后处理
- 前端思维链能解释真实 loop 行为
- `你是谁 / 你好 / 单知识问题 / 多轮问题 / fallback 问题` 都能跑通
