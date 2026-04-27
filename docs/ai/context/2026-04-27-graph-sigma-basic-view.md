# 2026-04-27 Graph 页面切换为 Sigma 基础版

## 背景

原知识图谱页面使用 React Flow 渲染，适合流程图和节点编辑，但不适合持续扩大的知识图谱网络。用户希望图谱风格向 sigma.js 示例靠拢，优先获得更接近网络图的视觉和交互体验。

## 本次实现

- 前端 graph 可视化组件从 `reactflow` 重写为 `sigma + graphology`。
- 前端依赖层同时移除 `reactflow`，避免 graph 页面出现双渲染栈并存。
- 保留页面层接口不变：仍然消费同一个 `GraphData`，仍通过 `selectedNodeId` 和 `onNodeClick` 驱动右侧详情面板。
- 基础版先实现：
  - 节点与边的网络图渲染
  - 实体 / 情节 / 孤立节点三类视觉区分
  - 节点点击选中
  - hover 与 selected 的邻域高亮
  - 视图缩放与重置
  - 基于 `graphology-layout-forceatlas2` 的同步力导布局
- 暂未实现：
  - 自定义 node image program
  - 自定义 shader 渐变节点
  - 力导 worker 布局
  - 复杂 tooltip、边筛选、搜索

## 取舍

- 先做 Sigma 基础版而不是一步上 shader，是为了先验证数据结构、事件模型、页面交互和渲染性能边界。
- 当前图谱数据来自后端 `GraphData`，节点只有 `entity / episode` 两类，没有图片资源或更细的语义分类；直接照搬 sigma 示例的 image/gradient program 会把渲染样式先于数据模型硬编码。
- 当前布局采用“环形种子坐标 + ForceAtlas2 同步迭代”的方式，优先解决知识图谱全量节点的聚团与交叉问题，同时避免先引入 worker 布局的调试复杂度。

## 后续建议

- 如果确认 sigma 方案可接受，下一步再引入 `@sigma/node-image` 和自定义 node program，按节点语义升级渲染样式。
- 若图谱继续扩大，应补搜索、邻域展开和主题筛选，而不是仅依赖缩放与全量标签显示。
