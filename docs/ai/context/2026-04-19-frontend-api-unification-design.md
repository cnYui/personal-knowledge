# 前端 API 封装统一设计

日期：2026-04-19

## 背景

当前前端已经有 `services/` 目录，但底层请求能力分裂成多套实现：

- `http.ts` 用 `axios.create({ baseURL })`
- `apiClient.ts` 用 `fetch + buildApiUrl + requestJson`
- 部分领域模块直接 `axios.get(buildApiUrl(...))`

页面和 hooks 没有直接到处拼完整 URL，但 `services` 层内部仍然在重复决定以下事情：

- 用 `fetch` 还是 `axios`
- 错误对象怎么归一化
- URL 前缀在哪里拼
- 查询参数、JSON 请求、`FormData` 请求分别怎么发

这会让后续新增接口和排查请求问题越来越难维护。

## 目标

- 保留按领域拆分的 `*Api.ts` 模块
- 底层只保留一个统一 HTTP client
- 统一 `baseURL`、错误归一化、请求方法风格
- 不让 hooks 和页面层感知底层请求实现
- 为后续新增 API 提供稳定、低心智负担的调用方式

## 非目标

- 这次不引入 OpenAPI 代码生成
- 这次不改 hooks 的对外接口
- 这次不重构页面组件的业务逻辑
- 这次不把所有 endpoint 抽成全局常量表

## 方案比较

### 方案一：保留现状，只补一个通用 request 工具

优点：

- 改动最小

缺点：

- `http.ts`、`apiClient.ts`、裸 `axios/fetch` 仍然会并存
- 新旧写法会继续扩散
- 没有真正解决维护边界混乱的问题

### 方案二：统一到单一 HTTP client，保留领域 API 模块

优点：

- 底层实现统一，页面和 hooks 不受影响
- 各领域模块仍保持语义清晰
- 改动范围可控，能直接解决维护问题

缺点：

- 需要迁移现有 `services` 文件
- SSE/流式请求需要作为特例处理

### 方案三：做成 endpoint 常量 + 生成式 SDK

优点：

- 一致性最高

缺点：

- 对当前项目体量偏重
- 会把这次本来很直接的问题扩成工具链建设

## 结论

采用方案二。

## 设计

### 1. 单一请求基座

以 `frontend/src/services/http.ts` 作为唯一底层请求入口，统一承接这些职责：

- `baseURL` 读取
- 请求前缀规范
- 通用错误归一化
- JSON 请求与返回处理
- `FormData` 请求透传
- 查询参数传递

`frontend/src/services/apiClient.ts` 中现有的可复用能力需要并入这一层，迁移后不再作为第二套基座继续存在。

### 2. 领域模块只表达业务语义

保留并整理这些文件的职责：

- `chatApi.ts`
- `dailyReviewApi.ts`
- `graphApi.ts`
- `memoryApi.ts`
- `promptApi.ts`
- `settingsApi.ts`
- `textApi.ts`
- `uploadApi.ts`

这些模块只负责：

- 暴露领域语义函数
- 传入 endpoint、参数、请求体
- 返回明确类型

这些模块不再负责：

- 手动拼接完整 URL
- 自己决定使用 `fetch` 还是 `axios`
- 自己实现一套错误转换

### 3. 流式接口单独保留，但遵守统一规范

`chatApi.ts` 的流式接口仍可使用 `fetch` 直接读取流，因为 `axios` 对浏览器原生流式 SSE/分块读取并不合适。

但它需要遵守同一套边界：

- URL 生成走统一入口
- 错误对象归一化走统一入口
- 非流式请求不再特判

也就是说，`chatApi.ts` 可以是传输层特例，但不能是规范例外。

### 4. 迁移策略

按低风险顺序迁移：

1. 先增强 `http.ts`，补齐统一请求能力
2. 迁移 `settingsApi.ts`、`dailyReviewApi.ts` 这类简单 JSON 接口
3. 迁移 `promptApi.ts`、`graphApi.ts`
4. 保持 `memoryGateway.ts`、`uploadApi.ts`、`textApi.ts` 与新规范一致
5. 最后收口 `chatApi.ts` 中共享的 URL 与错误处理逻辑
6. 删除或瘦身已失效的旧辅助函数

### 5. 对外兼容边界

本次重构默认保持以下边界不变：

- hooks 签名不变
- 页面调用方式不变
- React Query 的 query key 和 mutation 入口不变

这样可以把改动限制在 `services/` 内，避免把一次基础设施整理升级成页面层回归风险。

## 风险与取舍

### 风险

- 如果同时改 hooks 或页面层，回归面会明显扩大
- 如果强行把流式请求也塞进统一 JSON 工具，会损坏聊天流式能力
- 如果保留两套基座共存，后续很快会再次分叉

### 取舍

- 接受 `chatApi.ts` 在传输实现上是特例，但要求它继续复用统一 URL 和错误规范
- 不在本次引入 endpoint 常量中心化，先解决真正的维护主矛盾
- 不追求一步到位的大型 SDK 化，优先把底层边界收口

## 实施验收

完成后需要满足：

- `frontend/src/services` 中只保留一套底层 HTTP 基座
- 普通 JSON 接口都通过统一 client 发起
- 不再出现新的 `axios + buildApiUrl` 组合
- 不再出现新的普通 `fetch(buildApiUrl(...))` JSON 请求
- 现有 hooks 和页面无需同步修改调用方式
- 前端构建通过

## 后续实现提示

- 可以把统一错误归一化保留为独立函数，避免流式和非流式逻辑重复
- 如果 `apiClient.ts` 最终只剩下流式辅助或错误处理，应按职责重命名；如果职责完全并入 `http.ts`，则直接删除
- 新增 API 时，默认步骤应为：先在领域 `*Api.ts` 增加函数，再由 hooks 或页面消费，禁止直接在页面里写请求
