# Personal Knowledge Base Agentic RAG 需求与设计文档

## 1. 文档目的

本文档用于定义 `D:\CodeWorkSpace\personal-knowledge-base` 项目中第一版 Agentic RAG 的需求、设计边界、模块拆分、优先级和后续演进路线。目标不是照搬 RAGFlow 的完整 Canvas 体系，而是结合本项目现有的时序知识图谱与图谱 RAG，实现一个适合当前代码结构的“严格模式 Agentic RAG”。

本文档的重点是：

- 明确第一版要解决的问题
- 避免 MVP 做完后失去后续方向
- 将当前固定图谱 RAG 平滑升级为 Agentic RAG
- 明确 P0、P1、P2 的范围边界与优先级

---

## 2. 当前项目现状

当前项目已经具备良好的 Agentic RAG 底座，不需要从零重写：

- 聊天入口已经统一在 `ChatService`
- 主查询能力已经统一走 `KnowledgeGraphService.ask()` 与 `ask_stream()`
- 检索底层已经接入 Graphiti 时序知识图谱
- 当前回答流程已经是“图谱检索 -> 提取上下文 -> 调用 LLM -> 返回回答 + references”

按当前代码理解，现有系统并不是多路由结构，而是单一路径的图谱 RAG：

`用户问题 -> Graphiti 检索 -> 上下文构建 -> LLM 回答`

因此，本项目要做的不是“再发明一个 RAG”，而是：

**把当前固定图谱 RAG 升级为 Agent 可调度的图谱严格模式 Agentic RAG。**

---

## 3. 问题陈述

当前图谱 RAG 的能力虽然已经可用，但仍有结构性限制：

1. 检索路径被写死
   - 聊天请求进入后直接调用 `KnowledgeGraphService.ask()`
   - 系统没有显式的“决策层”

2. 检索与回答耦合在一起
   - 现在的 `KnowledgeGraphService` 同时负责：
     - 图谱搜索
     - 上下文提取
     - references 整理
     - 调用模型生成答案
   - 这会使未来增加 Agent 工具调用、多轮检索、Query Rewrite 等能力时边界不清晰

3. 无法平滑演化为 Agentic RAG
   - 当前没有标准工具接口
   - 没有单独的 Agent 控制层
   - 未来扩展第二个工具或第二轮检索会越来越难

4. MVP 后容易迷失方向
   - 如果只实现“先跑起来”的 Agent 版本，没有明确 P0/P1/P2 分层，后续非常容易进入随机迭代

---

## 4. 目标与非目标

### 4.1 第一版目标

第一版 Agentic RAG 的目标不是做一个复杂多工具平台，而是做一个：

**图谱严格模式、单知识源、单知识工具的 Agentic RAG。**

第一版需要满足：

- 聊天主流程由 Agent 控制层接管
- 图谱检索被封装为标准工具
- 非闲聊问题必须先经过图谱检索
- 回答必须严格基于检索结果与 references
- 外部 API 和前端返回结构尽量保持兼容
- 后续可平滑演进为多轮检索与多工具模式

### 4.2 非目标

第一版明确不做：

- 不做完整 Canvas/工作流引擎
- 不做多工具并行调度
- 不做外部 Web 搜索
- 不做多知识源融合
- 不做复杂 planner / reflector
- 不做无限轮工具调用
- 不做高复杂度的自主任务分解

这不是功能缩水，而是为了确保 MVP 有清晰边界、可稳定落地。

---

## 5. 总体方案选择

在前期头脑风暴阶段，一共讨论了三种方案：

1. 薄 Agent 包装层
2. 工具化图谱检索
3. 多步图谱 Agent

最终推荐方案为：

**方案 2：工具化图谱检索**

原因如下：

- 最接近 RAGFlow 的 Agentic RAG 核心结构
- 不需要引入完整 Canvas，也能建立 Agent -> Tool 的清晰边界
- 最大程度复用现有 `KnowledgeGraphService` 和 Graphiti 检索逻辑
- 能为后续第二轮检索、Query Rewrite、时间感知工具打下统一基础
- 风险、复杂度和收益之间平衡最好

---

## 6. 第一版总体架构

第一版建议采用以下调用关系：

`Chat API -> ChatService -> AgentService -> graph_retrieval_tool -> LLM final answer`

与当前结构相比，变化点只有一个核心变化：

- 以前：`ChatService` 直接进入 `KnowledgeGraphService.ask()`
- 现在：`ChatService` 进入 `AgentService`

然后由 `AgentService` 决定：

- 是否属于明显闲聊
- 是否必须调用图谱工具
- 在拿到图谱工具结果后如何生成最终回答

在第一版里，Agent 的知识工具只有一个：

- `graph_retrieval_tool`

因此，第一版不是在多个知识源之间选路，而是在：

- 闲聊
- 严格图谱问答

之间做最小决策。

---

## 7. 设计原则

### 7.1 严格模式优先

除明显寒暄外，问题必须先走图谱检索，再回答。

### 7.2 先建“边界”，再建“能力”

第一版最重要的不是做出花哨的多轮 Agent，而是先把：

- 检索
- 工具调用
- 回答生成
- 返回结构

之间的边界建立清楚。

### 7.3 尽量复用现有代码

现有 Graphiti 搜索、references 提取与 SSE 输出能力都应复用，不应推翻。

### 7.4 向后兼容优先

前端、接口层、返回结构尽量保持不变，避免把项目变成大范围重构。

### 7.5 先把图谱优势放大

后续增强首先优先考虑“更会用图谱”，而不是“先加更多工具”。

---

## 8. 模块拆分设计

### 8.1 保留并复用的模块

- `ChatService`
- `KnowledgeGraphService`
- `GraphitiClient.search(...)`
- 现有 SSE 结构与前端 references 展示方式

### 8.2 新增模块

#### A. `AgentService`

职责：

- 接收用户问题
- 组装 Agent 系统提示词
- 驱动一次受控的 Agent 决策流程
- 调用 `graph_retrieval_tool`
- 基于工具结果生成最终回答
- 处理严格模式兜底逻辑

#### B. `graph_retrieval_tool`

职责：

- 接收 `query`
- 调用图谱搜索
- 整理 context
- 提取 references
- 返回标准结构化结果

#### C. `agent_schemas`

职责：

- 统一定义工具返回结构
- 避免工具输出是松散 dict，降低后续维护成本

建议至少定义以下字段：

- `context`
- `references`
- `has_enough_evidence`
- `empty_reason`
- `retrieved_edge_count`
- `group_id`

#### D. `agent_prompts`

职责：

- 统一维护严格模式 prompt
- 避免 prompt 文本散落在 service 中
- 为后续 A/B prompt 实验提供集中入口

---

## 9. 对现有 `KnowledgeGraphService` 的重构建议

当前 `KnowledgeGraphService.ask()` 同时负责检索与回答。为了支持工具化，建议将其拆为两层职责：

### 9.1 检索层

建议新增方法：

- `retrieve_graph_context(query, group_id='default')`

职责：

- 调用 Graphiti 搜索
- 整理实体、关系和上下文
- 构造 references
- 返回结构化检索结果

### 9.2 回答层

建议新增方法：

- `answer_with_context(query, context, references)`

职责：

- 基于已给定的 context 进行回答
- 不负责再做检索
- 明确回答阶段与检索阶段解耦

### 9.3 好处

这种拆分会带来明显收益：

- `graph_retrieval_tool` 可以直接复用检索层
- Agent 可以只控制工具调用与最终回答
- 后续做 Query Rewrite 或二次检索时，不需要反复改一个大方法
- 测试也更好写

---

## 10. Agent 运行方式设计

### 10.1 第一版 Agent 决策范围

第一版不做复杂 Planner，只做如下最小决策：

1. 判断是否为明显闲聊
2. 如果是闲聊，走轻量回答
3. 如果不是闲聊，必须调用 `graph_retrieval_tool`
4. 若工具返回无证据，则给出“图谱中没有足够信息”的受控回答
5. 若工具返回有证据，则基于 context + references 回答

### 10.2 为什么第一版不做完全自由的工具调用

原因有三点：

- 你当前只有一个知识工具，自由工具选择收益不大
- 过早放开自由决策，容易出现漏调工具
- 严格模式下，更重要的是“保证先检索再答”

因此，第一版建议是：

**Agent 拥有工具接口，但策略上仍受强约束。**

这比“固定 RAG”更先进，但又比“自由智能体”更稳。

---

## 11. Prompt 设计原则

第一版 prompt 必须表达清楚以下规则：

1. 你是基于个人知识库图谱回答问题的知识助手
2. 除明显寒暄外，必须先通过 `graph_retrieval_tool` 获取证据
3. 如果工具返回无证据，不允许凭空补全事实
4. 回答应尽量引用具体实体、关系或时间线信息
5. 回答必须与 references 一致

### 11.1 严格模式的价值

严格模式的作用不是让 Agent 更“聪明”，而是让它更“可靠”。

在当前阶段，这比复杂能力更重要。

---

## 12. 请求流与返回流设计

### 12.1 请求流

建议保持外部接口不变：

1. 前端发送聊天请求
2. `ChatService` 调用 `AgentService`
3. `AgentService` 判断是否闲聊
4. 非闲聊则调用 `graph_retrieval_tool`
5. 根据结果生成最终回答
6. 返回 `answer + references`

### 12.2 流式返回

第一版建议保持现有 SSE 结构兼容，至少保留：

- `references`
- `content`
- `done`
- `error`

推荐流式顺序为：

1. 执行 `graph_retrieval_tool`
2. 先发送 references
3. 再流式发送回答内容
4. 最后发送 done

这样前端交互几乎不需要大改。

---

## 13. 错误处理设计

第一版建议将错误分为三类：

### 13.1 检索为空

这是正常业务分支，不视为异常。返回：

- 受控回答
- 空 references
- 可解释说明

### 13.2 工具执行失败

例如：

- Graphiti 搜索失败
- Neo4j 连接异常
- 数据结构解析错误

这类情况应：

- 返回稳定错误信息
- 记录详细日志
- 避免前端收到无结构的异常

### 13.3 LLM 回答失败

这类情况应：

- 保留已获取的 references
- 返回统一兜底文案
- 便于后续定位到底是检索层还是生成层出错

---

## 14. 可观测性与调试要求

第一版必须具备最基本可观测性，否则后续无法稳定迭代。

至少记录以下日志：

- 本次请求是否走入 Agent
- 是否被判定为闲聊
- 是否调用 `graph_retrieval_tool`
- 工具检索命中数量
- 是否命中空结果分支
- 最终回答是否成功生成

如果资源允许，推荐增加 trace 信息：

- 本次 tool 输入 query
- context 长度
- references 数量
- 最终使用模型名称

---

## 15. 测试要求

第一版至少要覆盖以下测试：

### 15.1 单元测试

- `graph_retrieval_tool` 在有结果时返回结构完整
- `graph_retrieval_tool` 在无结果时返回空证据状态
- `AgentService` 在非闲聊时会调用图谱工具
- `AgentService` 在闲聊时不会误走图谱检索

### 15.2 集成测试

- 聊天接口仍然返回 `answer + references`
- 流式接口仍然可以正常返回 `references -> content -> done`
- 图谱无结果时返回稳定文案

### 15.3 回归测试

- 原有图谱 RAG 基础能力不退化
- references 前端可继续正常展示

---

## 16. 范围控制：第一版刻意不做的事情

为了确保 MVP 可交付，第一版明确不做以下内容：

- 多工具并行
- 多轮反复检索
- 自动 Query Rewrite
- 外部联网检索
- 多知识源融合
- Agent Planner / Reflector
- Canvas 式节点编排
- 长期 memory ranking

这些内容将被移动到 P1/P2。

---

## 17. 优先级规划

### P0：MVP 必做

P0 目标：让系统从固定图谱 RAG 升级为“严格模式、单工具”的 Agentic RAG。

P0 包含：

1. 新增 `AgentService`
2. 将聊天主流程切换到 `AgentService`
3. 将图谱检索能力抽为 `graph_retrieval_tool`
4. 拆分 `KnowledgeGraphService` 为“检索层 + 回答层”
5. 定义统一工具返回 schema
6. 编写严格模式 prompt
7. 保持 API 返回结构兼容
8. 保持 SSE 结构兼容
9. 添加基础日志
10. 补齐单元测试与基础集成测试

P0 完成标准：

- 非闲聊问题进入 Agent 后，会调用图谱工具
- 回答严格基于图谱检索结果
- 空结果时有稳定兜底文案
- 前端无需大改即可继续使用

### P1：MVP 完成后优先增强

P1 目标：让 Agent 不只是“会调用图谱工具”，而是“更会用图谱”。

P1 包含：

1. 闲聊识别从纯 prompt 升级为显式规则或轻量分类
2. 支持最多 2 轮受控检索
3. 支持 Query Rewrite 后重检索
4. 工具返回增加更多信号：
   - 命中数量
   - 时间相关性
   - 实体覆盖度
5. 回答阶段增强引用约束
6. 增加前端标识：
   - 是否使用图谱检索
   - 命中 references 数量
7. 增加 trace/debug endpoint

P1 完成标准：

- 对复杂问题，Agent 可以在受控范围内做一次补充检索
- Query Rewrite 能提升部分问题的命中率
- 开发者能明显看见 Agent 的决策痕迹

### P2：中长期方向

P2 目标：从“单图谱工具 Agent”逐步演进到更完整的 Agentic RAG 平台。

P2 可考虑：

1. 图谱检索 + 文档向量检索双工具
2. 时间感知专用检索工具
3. 多工具编排
4. 更完整的多轮工具调用循环
5. planner / reflection
6. 类似 RAGFlow 的工作流化能力
7. 外部 Web 搜索

注意：

P2 不进入当前 MVP 范围，只作为未来方向保留。

---

## 18. 为什么这个优先级合理

这个优先级设计的核心思想是：

### 18.1 先立架构，再加复杂度

没有 `AgentService + Tool` 边界之前，做再多“智能”功能都容易变成继续堆在 `KnowledgeGraphService.ask()` 里。

### 18.2 先放大图谱优势，而不是盲目加工具

你的项目最大优势不是工具多，而是：

- 图谱结构化
- 有实体关系
- 有时间维度

所以第一批增强应该优先围绕“更好地使用图谱”。

### 18.3 保持前端和接口稳定

如果第一版就大改 API 或前端，成本会显著升高，也不利于快速验证 Agentic RAG 的真实收益。

---

## 19. 风险与缓解策略

### 风险 1：Agent 不调用工具

缓解：

- 第一版使用严格模式 prompt
- 将非闲聊必须先检索写入显式规则
- 在代码路径上增加守卫，必要时强制执行工具

### 风险 2：检索与回答重构导致现有功能退化

缓解：

- 仅拆职责，不改底层检索逻辑
- 保留原有测试与回归测试
- 先完成结构重构，再切换入口

### 风险 3：MVP 做成半自由 Agent，结果不稳定

缓解：

- 第一版只做单知识工具
- 禁止无限轮调用
- 不引入复杂 planner

### 风险 4：做完 P0 后缺少方向

缓解：

- 文档中明确 P1、P2 演进路线
- 后续迭代优先围绕图谱增强，而不是无边界扩展

---

## 20. MVP 验收标准

以下条件全部满足，才可视为 P0 完成：

1. 聊天主流程已经进入 Agent 控制层
2. 图谱检索已被工具化
3. 非闲聊问题会先走图谱检索
4. 回答严格基于检索结果
5. references 可继续返回给前端
6. SSE 输出兼容
7. 有基础日志与测试覆盖
8. 现有用户体验没有明显退化

---

## 21. 最终结论

本项目非常适合实现第一版 Agentic RAG，但推荐的落地方式不是照搬 RAGFlow 的完整 Canvas，而是：

**以当前 Graphiti 图谱 RAG 为底座，新增 Agent 控制层，并将图谱检索包装成唯一知识工具。**

第一版的正确目标不是“做一个很聪明的大智能体”，而是：

**做一个边界清晰、行为稳定、可持续演进的图谱严格模式 Agentic RAG。**

当 P0 完成后，P1 的重点不是增加更多工具，而是让 Agent 更会利用图谱，尤其是时间维度、二次检索与 Query Rewrite。

这条路径能最大程度复用现有系统，同时为后续真正的多工具 Agentic RAG 打下稳定基础。
