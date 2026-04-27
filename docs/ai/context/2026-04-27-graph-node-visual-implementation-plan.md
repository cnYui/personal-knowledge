# Graph 节点视觉规则实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Graph 页面中的 sigma 节点按连接数做对数放大，并按缩放等级与连接数分位数渐进显示标签，提升大图可读性。

**Architecture:** 保持现有 `sigma + graphology` 渲染链路不变，只调整前端图构建与 reducer 逻辑。节点大小在建图阶段按 `degree` 计算，标签显示在 reducer 阶段结合相机缩放比例、分位数阈值、悬停与选中状态动态决定。

**Tech Stack:** React 18、TypeScript、sigma、graphology、graphology-layout-forceatlas2、Vitest

---

## 文件结构

- 修改 `frontend/src/components/graph/KnowledgeGraphVisualization.tsx`
  - 收敛节点大小计算
  - 增加 `degree` 分位数阈值计算
  - 增加基于相机缩放的标签显示规则
  - 将相机状态变化接入 renderer 刷新
- 新增 `frontend/src/components/graph/graphVisualRules.ts`
  - 收敛纯规则 helper，避免测试依赖 WebGL 渲染环境
- 新增 `frontend/src/components/graph/KnowledgeGraphVisualization.test.tsx`
  - 覆盖权重映射与阈值计算的纯函数行为
- 修改 `docs/ai/context/2026-04-27-graph-node-visual-rules.md`
  - 固定默认参数与交互规则
- 修改 `AGENTS.md`
  - 同步默认公式与标签分层记忆

## 已执行结果

- 纯规则 helper 已拆到 `graphVisualRules.ts`
- 节点大小已按 `log2(degree + 1)` 接入
- 标签显示已按 `top 10% / 25% / 50%` + 缩放等级接入
- `degree <= 1` 节点默认不常显标签
- `hover / selected / neighborhood` 交互已兼容新规则

## 验证命令

- `cd frontend && npm run test -- src/components/graph/KnowledgeGraphVisualization.test.tsx`
- `cd frontend && npm run build`
