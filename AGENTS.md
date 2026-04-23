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

## 当前决策记忆

- 2026-04-19：确认前端 API 收敛方案采用“单一 HTTP client + 按领域拆分 `*Api.ts` 模块”，先收口 `services/` 内部边界，不改 hooks 对外接口
- 2026-04-23：合并 `feature/graph-history-v2-v3` 到 `main` 时，保留 `relation_topic` 的 minimal 模式，同时并入实体历史增强与测试并集，避免功能回退
