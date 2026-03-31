# RAGFlow Canvas Agentic RAG 复刻设计

## 1. 背景

当前 `personal-knowledge-base` 已经具备以下能力：

- 基于知识图谱的检索与回答
- 聊天入口、流式输出、trace 展示
- 一版简化的 Agent 路由与 fallback

但它和 RAGFlow 的 Agentic RAG 仍有本质差异。当前系统更像“聊天服务 + 检索服务 + 若干增强逻辑”，而不是一个真正的“工作流容器 + Agent 节点 + tool loop + 证据池 + citation 后处理”的统一运行时。

本次目标不是继续增强现有 `AgentService`，而是引入接近 RAGFlow 的完整运行模型，并在第一版先服务聊天 Agentic RAG 主链，同时保证底座未来可以承载更多节点和流程。

## 2. 目标

本次设计要在当前项目中建立一套第一版通用工作流底座，复刻 RAGFlow Agentic RAG 的关键结构：

1. 独立的 `tool loop`
2. 全局 retrieval 证据池
3. 回答后 citation 后处理
4. 真正的 `Agent Node` 抽象
5. 类似 RAGFlow `Canvas` 的工作流容器 / 节点编排能力

第一版的落点不是完整工作流平台，而是：

- 先做通用 `Canvas` 内核
- 先接一条聊天 Agentic RAG 主链
- 让聊天成为运行在 `Canvas` 上的一个 workflow，而不是继续写死在 `ChatService -> AgentService`

## 3. 非目标

本次不包含以下内容：

1. 不做完整可视化工作流编辑器
2. 不做大规模节点类型库
3. 不做多 Agent 协作
4. 不做 RAGFlow 全量 DSL 和全部节点
5. 不做并行分支调度优化器
6. 不做 MCP 全量接入
7. 不做完整工作流平台管理界面

## 4. 设计原则

### 4.1 先立运行时，再接业务

运行时模型是这次工作的核心。必须先定义清楚 `Canvas`、`Node`、`RuntimeContext`、`ReferenceStore`、`ToolLoopEngine` 的职责，再去接聊天主链。

### 4.2 通用底座优先，能力渐进落地

第一版要按“通用工作流底座”的方式设计，而不是写一个只服务聊天的临时控制器。即使 P0 只跑聊天 Agentic RAG，内部边界也必须适合未来扩更多节点。

### 4.3 证据和答案分离

检索结果不能只作为一次性字符串传给 LLM，必须沉淀进统一证据池。citation 不能和回答生成强耦合，而要在回答之后基于证据池做后处理。

### 4.4 不把所有逻辑塞进 AgentService

当前 `AgentService` 更适合被拆解，而不是继续承担更多运行时职责。后续它的能力会分散进入：

- `AgentNode`
- `ToolLoopEngine`
- `CitationPostProcessor`
- `Canvas` 事件流

## 5. RAGFlow 参考机制摘要

RAGFlow 的 Agentic RAG 可抽象为以下运行链：

```text
用户输入
-> Canvas 启动
-> Agent Node 组装 prompt / history / variables
-> Agent Node 绑定 Retrieval 等 tools
-> ToolLoopEngine 驱动 LLM tool-calling
-> Retrieval Tool 执行并写入全局 retrieval 证据池
-> Tool result 回填 history
-> LLM 判断是否继续 tool call
-> 生成最终回答
-> CitationPostProcessor 基于证据池补 citation
-> Message Node 输出
```

因此，本次复刻的核心不是单独拷贝 `Retrieval`，而是建立完整的运行机制。

## 6. 总体架构

### 6.1 推荐方案

采用“先做通用 Canvas 内核，再只接一条聊天 Agentic RAG 主链”的方案。

这意味着：

- 第一版就引入通用 `Canvas`
- 第一版就定义通用节点抽象
- 第一版就建立统一运行时与证据池
- 但第一版只落少量核心节点，让聊天主链跑通

### 6.2 运行链

第一版聊天主链定义为：

```text
BeginNode
-> AgentNode
-> MessageNode
```

其中 `AgentNode` 内部通过 `ToolLoopEngine` 绑定 `RetrievalNode` 作为 tool。

### 6.3 关键对象

#### Canvas

工作流运行容器，负责：

- 加载 workflow 定义
- 管理节点图和执行路径
- 持有运行期状态
- 输出节点事件流
- 协调节点执行

#### RuntimeContext

运行时上下文，负责：

- `sys.query`
- `sys.history`
- `sys.files`
- `sys.user_id`
- 全局变量
- workflow 级运行元数据

#### ReferenceStore

全局 retrieval 证据池，负责：

- 累积多轮检索结果
- 存放 chunk / graph evidence / doc aggregation
- 供回答阶段和 citation 阶段统一读取

#### Node

节点抽象基类。P0 先实现：

- `BeginNode`
- `AgentNode`
- `RetrievalNode`
- `MessageNode`

#### ToolLoopEngine

独立工具循环执行器，负责：

- 驱动 LLM tool-calling
- 执行 tool
- 将 tool result 追加到历史
- 控制 `max_rounds`
- 产出 tool trace

#### CitationPostProcessor

回答后引用处理器，负责：

- 读取最终答案
- 读取 `ReferenceStore`
- 组织 citation 所需的证据材料
- 输出带 citation 的最终回答或结构化 citation 数据

## 7. 模块划分

建议新增以下目录结构：

```text
backend/app/workflow/
  canvas.py
  runtime_context.py
  reference_store.py
  events.py
  dsl.py

backend/app/workflow/nodes/
  base.py
  begin_node.py
  agent_node.py
  retrieval_node.py
  message_node.py

backend/app/workflow/engine/
  tool_loop.py
  citation_postprocessor.py

backend/app/workflow/templates/
  chat_agentic_rag.json
```

## 8. 与现有代码的映射

### 8.1 可直接复用

- `KnowledgeGraphService`
- `GraphitiClient`
- 当前聊天 API 的流式返回方式
- 现有的图谱检索逻辑

### 8.2 需要拆解复用

`AgentService` 不应继续作为未来运行时主控制器。后续建议：

- 将 prompt 组织和节点行为移入 `AgentNode`
- 将工具循环逻辑移入 `ToolLoopEngine`
- 将 fallback 与回答策略拆成独立能力

### 8.3 必须新增

- `Canvas`
- `RuntimeContext`
- `ReferenceStore`
- `Node` 基类
- `ToolLoopEngine`
- `CitationPostProcessor`
- workflow 模板 / DSL 结构

## 9. 决策与回答策略

### 9.1 闲聊与查库策略

第一版 Agentic RAG 沿用当前确认过的用户策略：

- 明显闲聊：直接自然回复
- 非闲聊问题：默认先查知识库
- 用户明确要求“根据知识库/知识图谱回答”：强制查库
- 证据不足：允许通用模型补充
- 通用补充必须显式提示不是知识库结论

### 9.2 证据不足时的行为

当 `ReferenceStore` 中的本轮检索结果不足以支持回答时：

1. 保留已检索到的证据
2. 调用通用模型补充答案
3. 在最终内容前显式提示：

`知识库中未找到充分证据，以下内容为通用模型补充回答。`

4. 不允许把补充内容伪装为知识库结论

## 10. Trace 与事件流

P0 需要统一事件流，而不是继续把 trace 只当成聊天专属结构。

建议至少包含：

- `workflow_started`
- `node_started`
- `node_finished`
- `tool_call_started`
- `tool_call_finished`
- `message`
- `message_end`
- `workflow_finished`

对于 Agent 路径，trace 需要能体现：

- 进入哪个节点
- 调用了哪个 tool
- 检索轮次
- 证据是否充分
- 是否进入 fallback
- 是否执行 citation post-process

## 11. DSL / 模板

P0 不做可视化编辑器，但必须定义最小 workflow JSON 结构。

第一版模板建议只先支持：

- 节点定义
- 节点类型
- 上下游关系
- 节点参数

首个内置模板：

- `chat_agentic_rag.json`

该模板用于驱动聊天主链：

```text
BeginNode -> AgentNode -> MessageNode
```

## 12. P0 范围

### 12.1 P0 必做

1. `Canvas`
2. `RuntimeContext`
3. `ReferenceStore`
4. `Node` 基类
5. `BeginNode`
6. `AgentNode`
7. `RetrievalNode`
8. `MessageNode`
9. `ToolLoopEngine`
10. `CitationPostProcessor`
11. 最小 workflow DSL / 模板
12. 将聊天主链切到 `Canvas.run()`
13. 统一事件流和 trace

### 12.2 P0 不做

1. 可视化 workflow 编辑器
2. 大量节点类型
3. 并行分支调度
4. 多 Agent 协作
5. MCP 全量支持
6. 完整工作流平台 UI
7. 复杂 planner / reflection 体系

## 13. P1 范围

### 13.1 P1 优先项

1. 更多节点类型
   - `LLMNode`
   - `ConditionNode`
   - `LoopNode`
   - `FallbackNode`
   - `MemoryNode`

2. 分支与条件跳转

3. 多轮检索证据融合增强
   - 去重
   - merge
   - doc-level aggregation
   - graph evidence normalization

4. citation 精细化
   - 句级引用
   - 分段引用
   - 前端引用映射

5. 通用 tool registry

6. 可复用 workflow 模板库

7. 更强的 trace / 调试面板

### 13.2 为什么这样排序

P0 解决“运行底座是否存在”的问题。  
P1 才解决“工作流表达能力和可观测性是否强”的问题。

## 14. 实施顺序

### 阶段 1：底座

先实现：

- `RuntimeContext`
- `ReferenceStore`
- `Canvas`
- `Node` 基类
- 事件定义

### 阶段 2：基础节点

接入：

- `BeginNode`
- `RetrievalNode`
- `MessageNode`

先验证 `Canvas` 能执行最小节点链，且上下文可以在节点间传递。

### 阶段 3：ToolLoopEngine

将现有 Agent 工具循环逻辑抽成独立引擎，形成真正的 tool loop。

### 阶段 4：AgentNode

让 `AgentNode` 负责：

- 组装 prompt
- 绑定 tools
- 调用 `ToolLoopEngine`
- 将结果写回 `RuntimeContext`

### 阶段 5：ReferenceStore + CitationPostProcessor

补齐：

- 检索结果入池
- 回答后补 citation

### 阶段 6：聊天主链接入

将当前聊天链路改为：

```text
Chat API -> ChatService -> CanvasFactory -> Canvas.run()
```

### 阶段 7：前端和 trace 对接

最后再做：

- trace 面板升级
- citation 展示增强
- workflow 运行信息前端渲染

## 15. 验收标准

满足以下条件视为 P0 完成：

1. 聊天主链已经不再直接依赖旧的单体 `AgentService` 作为主执行入口
2. 系统存在可独立运行的 `Canvas`
3. 系统存在可独立运行的 `ToolLoopEngine`
4. `RetrievalNode` 可以把证据写入统一 `ReferenceStore`
5. `AgentNode` 可以绑定 tool 并驱动 tool loop
6. 最终回答支持 citation 后处理
7. 流式 trace 可以展示节点执行与 tool 调用过程
8. 第一版 workflow 模板能够稳定驱动聊天 Agentic RAG

## 16. 风险与控制

### 16.1 风险

1. 一次性重构范围过大
2. 旧聊天链路与新 Canvas 链路共存时语义不一致
3. trace、citation、fallback 三者的事件时序容易混乱
4. 把运行时逻辑继续堆进旧服务层会导致二次技术债

### 16.2 控制策略

1. 严格按 P0 / P1 切分
2. 先立后端运行模型，再接前端
3. 先落最小节点集，不扩节点库
4. 让聊天成为 `Canvas` 的一个模板实例，而不是继续写死

## 17. 推荐结论

推荐按以下原则推进：

- 第一版就建立通用 `Canvas` 底座
- 第一版只落聊天 Agentic RAG 主链
- 第一版必须带上 `tool loop + ReferenceStore + citation post-process + AgentNode`
- 不把本次工作降级成“加强版 AgentService”

这条路线既能接近 RAGFlow 的核心机制，又不会在 P0 阶段把项目拉成一个尚未收敛的全量工作流平台。
