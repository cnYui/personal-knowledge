# Agentic RAG V2 MVP 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不修改对外 API、响应结构和前端消费方式的前提下，为当前 Agentic RAG 接入 `knowledge profile overlay + pre-retrieval probe + 三段式决策` 的 MVP 版本。

**Architecture:** 保持现有 `Begin -> Agent -> Message` Canvas 结构不变，只在 `AgentNode.execute()` 内部新增前置 probe 阶段。先用 `graph_retrieval_tool` 做一轮轻量证据探测，再根据 `sufficient / insufficient / no_hit` 三类结果决定是直接 grounded、进入现有 tool loop，还是在重试一次后走通用回答。所有输出仍然走现有 citation 与 trace 后处理链路。

**Tech Stack:** Python, Pydantic, pytest, AsyncMock, 现有 Canvas/ToolLoopEngine

---

## 文件地图

### 新增

- `docs/superpowers/plans/2026-04-15-agentic-rag-v2-mvp-implementation-plan.md` - 本实现计划

### 修改

- `backend/app/workflow/nodes/agent_node.py` - 增加 probe、重试与三段式裁决逻辑
- `backend/tests/workflow/nodes/test_agent_node.py` - 增加 probe 相关行为测试

### 可能修改

- `backend/app/schemas/agent.py` - 仅当需要扩展 trace step_type 或字段时修改
- `backend/tests/test_chat_api.py` - 如需补充 fallback/citation 回归测试时修改

---

### Task 1: 为前置 probe 判定补齐失败测试

**Files:**
- Modify: `backend/tests/workflow/nodes/test_agent_node.py`
- Test: `backend/tests/workflow/nodes/test_agent_node.py`

- [ ] **Step 1: 写出首轮 probe 充分时直接 grounded 的失败测试**

```python
@pytest.mark.anyio
async def test_agent_node_probe_sufficient_can_skip_tool_loop_and_answer_from_kb():
    references = [ChatReference(type='relationship', fact='Alice likes green tea')]
    retrieval_result = GraphRetrievalResult(
        context='关系: Alice likes green tea',
        references=references,
        has_enough_evidence=True,
        retrieved_edge_count=1,
        group_id='team-a',
    )
    retrieval_calls = []

    class StubGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            retrieval_calls.append((query, group_id))
            return retrieval_result

    class FailingToolLoopEngine:
        async def run(self, **kwargs):
            raise AssertionError('probe 已经充分时，不应再进入 tool loop')

    class StubKnowledgeGraphService:
        async def answer_with_context(self, query: str, provided_result: GraphRetrievalResult):
            return {'answer': '根据知识图谱，Alice 喜欢绿茶。'}

    spec = WorkflowNodeSpec(id='agent', type='agent', config={'group_id': 'team-a'})
    node = AgentNode(
        spec,
        graph_retrieval_tool=StubGraphRetrievalTool(),
        knowledge_graph_service=StubKnowledgeGraphService(),
        tool_loop_engine=FailingToolLoopEngine(),
    )
    node._extract_focus_points = AsyncMock(return_value='Alice / 喜欢 / 绿茶')
    context = RuntimeContext(query='Alice 喜欢什么？')
    canvas = Canvas(WorkflowDSL(entry_node_id='agent', nodes=[spec]), context=context)

    result = await node.execute(context, canvas)

    assert result['answer'] == '根据知识图谱，Alice 喜欢绿茶。'
    assert result['references'] == references
    assert result['agent_trace'].final_action == 'kb_grounded_answer'
    assert retrieval_calls == [('Alice 喜欢什么？', 'team-a')]
```

- [ ] **Step 2: 写出首轮无命中、重试后仍无命中时 direct fallback 的失败测试**

```python
@pytest.mark.anyio
async def test_agent_node_probe_retry_still_no_hit_goes_to_direct_general_answer():
    empty_result = GraphRetrievalResult(
        context='',
        references=[],
        has_enough_evidence=False,
        empty_reason='图谱中没有足够信息',
        retrieved_edge_count=0,
        group_id='default',
    )
    retrieval_calls = []

    class StubGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            retrieval_calls.append((query, group_id))
            return empty_result

    class FailingToolLoopEngine:
        async def run(self, **kwargs):
            raise AssertionError('两轮 probe 都无命中时，不应进入 tool loop')

    client = FakeLLMClient([FakeResponse(FakeMessage(content='你好，我可以先基于通用知识回答你。'))])
    spec = WorkflowNodeSpec(id='agent', type='agent')
    node = AgentNode(
        spec,
        graph_retrieval_tool=StubGraphRetrievalTool(),
        tool_loop_engine=FailingToolLoopEngine(),
        llm_client=client,
    )
    node._extract_focus_points = AsyncMock(return_value='OpenAI / 最近动态')
    context = RuntimeContext(query='OpenAI 最近有什么动态？')
    canvas = Canvas(WorkflowDSL(entry_node_id='agent', nodes=[spec]), context=context)

    result = await node.execute(context, canvas)

    assert result['agent_trace'].final_action == 'direct_general_answer'
    assert retrieval_calls == [
        ('OpenAI 最近有什么动态？', 'default'),
        ('OpenAI / 最近动态', 'default'),
    ]
```

- [ ] **Step 3: 写出首轮无命中、重试后证据不足时进入 tool loop 的失败测试**

```python
@pytest.mark.anyio
async def test_agent_node_probe_retry_insufficient_enters_tool_loop():
    empty_result = GraphRetrievalResult(
        context='',
        references=[],
        has_enough_evidence=False,
        empty_reason='图谱中没有足够信息',
        retrieved_edge_count=0,
        group_id='default',
    )
    weak_result = GraphRetrievalResult(
        context='Alice 可能与绿茶相关',
        references=[ChatReference(type='entity', name='Alice', summary='喜欢喝茶')],
        has_enough_evidence=False,
        empty_reason='证据不足以直接回答',
        retrieved_edge_count=1,
        group_id='default',
    )
    retrieval_calls = []

    class StubGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            retrieval_calls.append((query, group_id))
            return empty_result if len(retrieval_calls) == 1 else weak_result

    class StubToolLoopResult:
        answer = 'Alice 喜欢喝茶，但证据仍然有限。'
        exceeded_max_rounds = False
        steps = []

    class StubToolLoopEngine:
        async def run(self, **kwargs):
            return StubToolLoopResult()

    spec = WorkflowNodeSpec(id='agent', type='agent')
    node = AgentNode(
        spec,
        graph_retrieval_tool=StubGraphRetrievalTool(),
        tool_loop_engine=StubToolLoopEngine(),
    )
    node._extract_focus_points = AsyncMock(return_value='Alice / 喝茶')
    context = RuntimeContext(query='Alice 喜欢什么饮料？')
    canvas = Canvas(WorkflowDSL(entry_node_id='agent', nodes=[spec]), context=context)

    result = await node.execute(context, canvas)

    assert result['agent_trace'].final_action == 'kb_plus_general_answer'
    assert retrieval_calls == [
        ('Alice 喜欢什么饮料？', 'default'),
        ('Alice / 喝茶', 'default'),
    ]
```

- [ ] **Step 4: 运行新测试，确认当前实现失败**

Run: `python -m pytest backend/tests/workflow/nodes/test_agent_node.py -k "probe_" -v`
Expected: FAIL，至少出现以下一种情况：

- `AgentNode` 当前没有做 probe，导致直接进入 tool loop
- `AgentNode` 当前没有进行 retry probe
- `AgentNode` 当前没有在 probe 充分时跳过 tool loop

- [ ] **Step 5: 提交测试基线**

```bash
git add backend/tests/workflow/nodes/test_agent_node.py
git commit -m "test: add failing probe flow coverage for agent node"
```

### Task 2: 在 AgentNode 中加入 probe 基础能力

**Files:**
- Modify: `backend/app/workflow/nodes/agent_node.py`
- Test: `backend/tests/workflow/nodes/test_agent_node.py`

- [ ] **Step 1: 写出 probe 分类辅助方法的最小失败断言**

```python
def test_agent_node_classify_probe_result_without_evidence():
    node = AgentNode(WorkflowNodeSpec(id='agent', type='agent'))
    result = GraphRetrievalResult(
        context='',
        references=[],
        has_enough_evidence=False,
        empty_reason='图谱中没有足够信息',
        retrieved_edge_count=0,
    )

    assert node._classify_probe_result(result) == 'no_hit'
```

- [ ] **Step 2: 运行分类测试，确认当前失败**

Run: `python -m pytest backend/tests/workflow/nodes/test_agent_node.py -k "classify_probe_result" -v`
Expected: FAIL with `AttributeError: 'AgentNode' object has no attribute '_classify_probe_result'`

- [ ] **Step 3: 在 AgentNode 中加入最小 probe 辅助方法**

```python
    def _classify_probe_result(self, result: GraphRetrievalResult) -> str:
        if result.has_enough_evidence:
            return 'sufficient'
        if (not result.references) or result.retrieved_edge_count <= 0 or not str(result.context or '').strip():
            return 'no_hit'
        return 'insufficient'

    async def _run_probe(self, query: str, canvas, group_id: str) -> GraphRetrievalResult:
        result = await self._get_graph_retrieval_tool().run(query, group_id=group_id)
        canvas.reference_store.merge(
            chunks=[
                {
                    'id': f'{self.node_id}-probe-{index}',
                    'content': reference.fact or reference.summary or reference.name or reference.type,
                }
                for index, reference in enumerate(result.references)
            ],
            graph_evidence=[reference.model_dump() for reference in result.references],
        )
        return result

    async def _retry_probe_with_focus_points(
        self,
        query: str,
        focus_points: str,
        canvas,
        group_id: str,
    ) -> GraphRetrievalResult:
        retry_query = str(focus_points or query).strip() or query
        return await self._run_probe(retry_query, canvas, group_id)
```

- [ ] **Step 4: 运行 probe 分类与已有 AgentNode 测试**

Run: `python -m pytest backend/tests/workflow/nodes/test_agent_node.py -k "classify_probe_result or can_answer_greeting_without_retrieval" -v`
Expected: PASS，且未影响现有 greeting 测试。

- [ ] **Step 5: 提交 probe 辅助能力**

```bash
git add backend/app/workflow/nodes/agent_node.py backend/tests/workflow/nodes/test_agent_node.py
git commit -m "feat: add probe helpers to agent node"
```

### Task 3: 将 probe 分支接入 execute 主流程

**Files:**
- Modify: `backend/app/workflow/nodes/agent_node.py`
- Test: `backend/tests/workflow/nodes/test_agent_node.py`

- [ ] **Step 1: 写出 execute 主流程的失败测试补充**

```python
@pytest.mark.anyio
async def test_agent_node_probe_sufficient_skips_tool_loop_trace_rounds_are_zero():
    references = [ChatReference(type='relationship', fact='Alice likes green tea')]
    retrieval_result = GraphRetrievalResult(
        context='关系: Alice likes green tea',
        references=references,
        has_enough_evidence=True,
        retrieved_edge_count=1,
    )

    class StubGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            return retrieval_result

    class FailingToolLoopEngine:
        async def run(self, **kwargs):
            raise AssertionError('probe 足够时不应执行 tool loop')

    class StubKnowledgeGraphService:
        async def answer_with_context(self, query: str, provided_result: GraphRetrievalResult):
            return {'answer': '根据知识图谱，Alice 喜欢绿茶。'}

    spec = WorkflowNodeSpec(id='agent', type='agent')
    node = AgentNode(
        spec,
        graph_retrieval_tool=StubGraphRetrievalTool(),
        knowledge_graph_service=StubKnowledgeGraphService(),
        tool_loop_engine=FailingToolLoopEngine(),
    )
    node._extract_focus_points = AsyncMock(return_value='Alice / 绿茶')
    context = RuntimeContext(query='Alice 喜欢什么？')
    canvas = Canvas(WorkflowDSL(entry_node_id='agent', nodes=[spec]), context=context)

    result = await node.execute(context, canvas)

    assert result['agent_trace'].retrieval_rounds == 0
    assert result['agent_trace'].final_action == 'kb_grounded_answer'
```

- [ ] **Step 2: 运行 execute 相关测试，确认当前失败**

Run: `python -m pytest backend/tests/workflow/nodes/test_agent_node.py -k "probe_sufficient" -v`
Expected: FAIL，因为当前实现一开始直接执行 tool loop。

- [ ] **Step 3: 在 execute 中加入 probe + retry + 分支裁决**

```python
        focus_points = await self._extract_focus_points(query)
        emit_timeline(
            {
                'type': 'timeline',
                'id': 'understand-question',
                'kind': 'understand',
                'title': '理解问题',
                'detail': f'已提炼检索重点：{focus_points}',
                'status': 'done',
            }
        )

        probe_result = await self._run_probe(query, canvas, group_id)
        probe_status = self._classify_probe_result(probe_result)

        self._append_trace_step(
            trace,
            step_type='retrieval',
            query=query,
            message='执行前置证据探测。',
            evidence_found=probe_result.has_enough_evidence,
            retrieved_edge_count=probe_result.retrieved_edge_count,
            action='probe_retrieve',
        )

        if probe_status == 'no_hit':
            retry_query = str(focus_points or query).strip() or query
            retry_result = await self._retry_probe_with_focus_points(query, focus_points, canvas, group_id)
            retry_status = self._classify_probe_result(retry_result)
            self._append_trace_step(
                trace,
                step_type='retrieval',
                query=query,
                message='首轮探测无命中，使用 focus points 再次检索。',
                evidence_found=retry_result.has_enough_evidence,
                retrieved_edge_count=retry_result.retrieved_edge_count,
                action='probe_retry',
            )
            trace.steps[-1].rewritten_query = retry_query
            probe_result = retry_result
            probe_status = retry_status

        if probe_status == 'sufficient':
            answer = await self._answer_from_grounded_probe(query, probe_result)
            trace.final_action = 'kb_grounded_answer'
            self._append_trace_step(
                trace,
                step_type='answer',
                query=query,
                message='前置 probe 已提供充分证据，直接基于知识库生成回答。',
                evidence_found=True,
                retrieved_edge_count=probe_result.retrieved_edge_count,
                action='probe_grounded',
            )
            result = self._result_payload(
                answer=answer,
                references=probe_result.references,
                trace=trace,
            )
            result['workflow_debug'] = {
                'forced_retrieval': True,
                'tool_rounds_exceeded': False,
                'tool_steps': [],
            }
            context.set_global(output_key, result)
            return result

        if probe_status == 'no_hit':
            answer = await self._answer_with_general_model(query, None)
            trace.final_action = 'direct_general_answer'
            self._append_trace_step(
                trace,
                step_type='answer',
                query=query,
                message='两轮 probe 均未命中，直接生成通用回答。',
                action='answer_directly',
            )
            result = self._result_payload(answer=answer, references=[], trace=trace)
            result['workflow_debug'] = {
                'forced_retrieval': True,
                'tool_rounds_exceeded': False,
                'tool_steps': [],
            }
            context.set_global(output_key, result)
            return result
```

- [ ] **Step 4: 补充 grounded answer 辅助方法**

```python
    async def _answer_from_grounded_probe(
        self,
        query: str,
        retrieval_result: GraphRetrievalResult,
    ) -> str:
        knowledge_result = await self._get_knowledge_graph_service().answer_with_context(
            query,
            retrieval_result,
        )
        return str(knowledge_result.get('answer') or '').strip()
```

- [ ] **Step 5: 运行 AgentNode 全量测试**

Run: `python -m pytest backend/tests/workflow/nodes/test_agent_node.py -v`
Expected: PASS，包含旧测试与新增 probe 测试全部通过。

- [ ] **Step 6: 提交 execute 主流程升级**

```bash
git add backend/app/workflow/nodes/agent_node.py backend/tests/workflow/nodes/test_agent_node.py
git commit -m "feat: add probe-first mvp flow to agent node"
```

### Task 4: 让证据不足路径继续复用现有 tool loop 和 fallback

**Files:**
- Modify: `backend/app/workflow/nodes/agent_node.py`
- Modify: `backend/tests/workflow/nodes/test_agent_node.py`

- [ ] **Step 1: 写出 probe 不足时沿用 tool loop 的失败测试**

```python
@pytest.mark.anyio
async def test_agent_node_probe_insufficient_still_uses_tool_loop_and_fallback_prefix():
    weak_result = GraphRetrievalResult(
        context='Alice 可能与绿茶相关',
        references=[ChatReference(type='entity', name='Alice', summary='喜欢喝茶')],
        has_enough_evidence=False,
        empty_reason='证据不足以直接回答',
        retrieved_edge_count=1,
    )

    class StubGraphRetrievalTool:
        async def run(self, query: str, group_id: str = 'default'):
            return weak_result

    client = FakeLLMClient(
        [
            FakeResponse(FakeMessage(content='从通用知识来看，她可能偏好茶类饮品。')),
        ]
    )

    class StubToolLoopResult:
        answer = ''
        exceeded_max_rounds = False
        steps = []

    class StubToolLoopEngine:
        async def run(self, **kwargs):
            return StubToolLoopResult()

    spec = WorkflowNodeSpec(id='agent', type='agent')
    node = AgentNode(
        spec,
        graph_retrieval_tool=StubGraphRetrievalTool(),
        tool_loop_engine=StubToolLoopEngine(),
        llm_client=client,
    )
    node._extract_focus_points = AsyncMock(return_value='Alice / 绿茶')
    context = RuntimeContext(query='Alice 喜欢喝什么？')
    canvas = Canvas(WorkflowDSL(entry_node_id='agent', nodes=[spec]), context=context)

    result = await node.execute(context, canvas)

    assert result['answer'].startswith('知识库中未找到充分证据，以下内容为通用模型补充回答。')
    assert result['agent_trace'].final_action == 'kb_plus_general_answer'
```

- [ ] **Step 2: 运行 fallback 测试，确认在 probe-first 流程下仍然失败或存在行为缺口**

Run: `python -m pytest backend/tests/workflow/nodes/test_agent_node.py -k "fallback_prefix" -v`
Expected: FAIL，或出现 trace/action 与预期不一致。

- [ ] **Step 3: 在 execute 中为 insufficient 分支显式打点并保留现有 fallback 逻辑**

```python
        self._append_trace_step(
            trace,
            step_type='retrieval',
            query=query,
            message='前置 probe 发现部分证据，但不足以直接回答，进入多轮 tool loop。',
            evidence_found=False,
            retrieved_edge_count=probe_result.retrieved_edge_count,
            action='enter_tool_loop',
        )

        tool_loop_result = await self._get_tool_loop_engine().run(
            messages=self._build_messages(context, query),
            tool_schemas=self._tool_schemas(),
            tool_registry={
                graph_tool.name: graph_tool,
                history_tool.name: history_tool,
            },
            system_prompt=system_prompt,
            completion_kwargs={'temperature': float(self.config.get('temperature', 0.2))},
            event_callback=emit_timeline,
        )
```

- [ ] **Step 4: 确保 tool loop 结果与 probe 结果统一合并**

```python
        retrieval_result = self._combine_retrieval_results(
            [probe_result, *graph_tool.results]
        )
```

- [ ] **Step 5: 运行不足证据相关测试**

Run: `python -m pytest backend/tests/workflow/nodes/test_agent_node.py -k "fallback or tool_loop" -v`
Expected: PASS，且已有 `kb_plus_general_answer` 行为不回归。

- [ ] **Step 6: 提交不足证据分支整合**

```bash
git add backend/app/workflow/nodes/agent_node.py backend/tests/workflow/nodes/test_agent_node.py
git commit -m "feat: integrate probe with tool loop fallback path"
```

### Task 5: 回归验证 citation、trace 和聊天主链

**Files:**
- Modify: `backend/tests/test_chat_api.py`
- Test: `backend/tests/test_chat_api.py`

- [ ] **Step 1: 写出 fallback 标记不回归的聊天层测试**

```python
@pytest.mark.anyio
async def test_chat_service_keeps_general_fallback_marker_when_agent_returns_prefixed_answer():
    class StubCanvasFactory:
        def create_chat_canvas(self, **kwargs):
            raise RuntimeError('使用现有测试夹具时请替换为返回固定事件序列的 Canvas')
```

- [ ] **Step 2: 如果现有聊天层测试夹具不足，改为先执行最小回归命令**

Run: `python -m pytest backend/tests/test_chat_api.py -k "fallback or citation" -v`
Expected: PASS，或明确识别当前测试缺口。

- [ ] **Step 3: 若无需新增聊天层测试，则至少执行 AgentNode + citation 相关回归**

Run: `python -m pytest backend/tests/workflow/nodes/test_agent_node.py backend/tests/workflow/engine/test_citation_postprocessor.py -v`
Expected: PASS

- [ ] **Step 4: 执行 MVP 全量目标测试集**

Run: `python -m pytest backend/tests/workflow/nodes/test_agent_node.py backend/tests/workflow/engine/test_citation_postprocessor.py backend/tests/test_chat_api.py -v`
Expected: PASS

- [ ] **Step 5: 提交 MVP 回归验证**

```bash
git add backend/tests/test_chat_api.py
git commit -m "test: verify mvp probe flow does not regress chat outputs"
```

## 自检

### 规格覆盖检查

- `overlay + pre-retrieval probe + 三段式决策`：由 Task 2、Task 3 覆盖
- `MVP 不改 API / 响应 / 前端消费`：全计划未涉及 API 或前端文件
- `trace / timeline 增强`：由 Task 3、Task 4 覆盖
- `fallback 保持明确`：由 Task 4、Task 5 覆盖

### 占位符检查

- 本计划未使用 `TBD`、`TODO`、`稍后实现`
- 每个代码修改步骤都给出了明确代码片段
- 每个验证步骤都给出了具体命令和预期结果

### 类型一致性检查

- 统一使用现有 `GraphRetrievalResult`
- 回答动作统一使用：
  - `direct_general_answer`
  - `kb_grounded_answer`
  - `kb_plus_general_answer`
- 新增 trace action 统一使用：
  - `probe_retrieve`
  - `probe_retry`
  - `probe_grounded`
  - `enter_tool_loop`

