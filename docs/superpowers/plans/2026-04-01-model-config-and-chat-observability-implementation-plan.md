# 模型配置与对话可观测性 Implementation Plan

> Goal: 在 `personal-knowledge-base` 中落地全局模型配置中心、设置页、统一模型错误治理，以及聊天页灰色执行轨迹摘要框，并保证 `.env` 持久化后立即热更新生效。

## 1. 实施原则

1. 先立后端配置中心，再接前端设置页
2. 先统一模型配置读取入口，再做错误映射
3. 先保证保存后立即生效，再做体验层优化
4. 不继续在各个 service 中散落读取 `settings.*_api_key`
5. 每个阶段都要求有明确测试或手动验证产物

## 2. P0 总目标

P0 完成后，系统应满足：

- 存在统一的 `ModelConfigService`
- 存在安全的 `.env` 读写能力
- 存在 `GET /api/settings/model-config`
- 存在 `PUT /api/settings/model-config`
- 对话链路从配置中心读取 API Key
- 知识库构建链路从配置中心读取 API Key
- DeepSeek / 上游错误被统一映射为稳定错误码
- 聊天页生成中显示灰色执行轨迹摘要框
- 设置页可掩码展示、查看、编辑并保存两个 API Key

## 3. 文件结构目标

### 新增文件

```text
backend/app/core/env_store.py
backend/app/core/model_errors.py
backend/app/schemas/settings.py
backend/app/services/model_config_service.py
backend/app/routers/settings.py

frontend/src/pages/SettingsPage.tsx
frontend/src/services/settingsApi.ts
frontend/src/hooks/useSettings.ts
frontend/src/components/settings/ModelConfigForm.tsx
frontend/src/components/chat/StreamingTraceSummary.tsx
```

### 重点修改文件

```text
backend/app/core/config.py
backend/app/main.py
backend/app/services/knowledge_graph_service.py
backend/app/services/graphiti_client.py
backend/app/services/text_optimizer.py
backend/app/services/title_generator.py
backend/app/services/chat_service.py
backend/app/routers/chat.py

frontend/src/app/router.tsx
frontend/src/components/layout/SideNav.tsx
frontend/src/pages/KnowledgeChatPage.tsx
frontend/src/components/chat/ChatMessageList.tsx
frontend/src/services/chatApi.ts
frontend/src/hooks/useChat.ts
frontend/src/types/chat.ts
```

## 4. 阶段拆分

### 阶段 1：后端配置中心

**目标：** 建立统一的模型运行时配置入口，并将 `.env` 作为持久化来源。

**新增文件：**

- `backend/app/core/env_store.py`
- `backend/app/schemas/settings.py`
- `backend/app/services/model_config_service.py`

**任务：**

- 定义逻辑配置模型：
  - `dialog_api_key`
  - `knowledge_build_api_key`
- 定义掩码输出结构
- 实现 `.env` 读写工具：
  - 读取键值
  - 更新已有键
  - 缺失时追加
- 实现运行时配置服务：
  - 启动加载
  - 读取当前生效配置
  - 保存并刷新
  - 掩码化输出

**测试：**

- `backend/tests/services/test_model_config_service.py`
- `backend/tests/core/test_env_store.py`

**完成标准：**

- 保存配置能写回 `.env`
- 新配置在同一进程内立即可读
- 掩码输出不泄漏完整 Key

### 阶段 2：设置 API

**目标：** 提供前端可用的全局模型设置接口。

**新增文件：**

- `backend/app/routers/settings.py`

**修改文件：**

- `backend/app/main.py`

**任务：**

- 新增：
  - `GET /api/settings/model-config`
  - `PUT /api/settings/model-config`
- 接入请求校验
- 接入运行时配置刷新
- 统一返回掩码配置和保存状态

**测试：**

- `backend/tests/test_settings_api.py`

**完成标准：**

- 设置页能读到当前配置状态
- 保存配置后接口返回立即生效状态

### 阶段 3：模型调用改接配置中心

**目标：** 收口模型配置读取入口，消除明显硬编码。

**修改文件：**

- `backend/app/services/knowledge_graph_service.py`
- `backend/app/services/graphiti_client.py`
- `backend/app/services/text_optimizer.py`
- `backend/app/services/title_generator.py`
- 必要时补充对话相关 service

**任务：**

- 识别当前直接读取：
  - `settings.openai_api_key`
  - `settings.deepseek_api_key`
  - `settings.openai_base_url`
  - `settings.deepseek_base_url`
  的位置
- 改为通过 `ModelConfigService` 获取运行时配置
- 保持原有 provider 兼容能力
- 避免在业务 service 中继续直接依赖历史字段名

**测试：**

- 更新对应 service 的单测
- 增加配置切换后的运行时读取测试

**完成标准：**

- 对话与知识构建链路都不再散落直接读取 API Key
- 保存设置后新请求能命中新配置

### 阶段 4：统一模型错误映射

**目标：** 把上游 provider 错误收口为稳定的后端错误语义。

**新增文件：**

- `backend/app/core/model_errors.py`

**任务：**

- 定义统一错误类型：
  - `MODEL_API_KEY_MISSING`
  - `MODEL_API_QUOTA_EXCEEDED`
  - `MODEL_API_AUTH_FAILED`
  - `MODEL_API_RATE_LIMITED`
  - `MODEL_API_UPSTREAM_ERROR`
  - `MODEL_API_NETWORK_ERROR`
- 增加 DeepSeek / OpenAI-compatible 错误到统一错误类型的映射
- 在对话与知识构建调用点统一抛出/返回该错误结构

**测试：**

- `backend/tests/core/test_model_errors.py`
- service 层错误映射单测

**完成标准：**

- `402`、未配置 Key、鉴权失败、429、5xx、网络错误都能稳定映射

### 阶段 5：前端设置页

**目标：** 让用户可以在页面中管理两个全局 API Key。

**新增文件：**

- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/services/settingsApi.ts`
- `frontend/src/hooks/useSettings.ts`
- `frontend/src/components/settings/ModelConfigForm.tsx`

**修改文件：**

- `frontend/src/app/router.tsx`
- `frontend/src/components/layout/SideNav.tsx`

**任务：**

- 新增设置页路由和导航入口
- 实现两个 API Key 字段：
  - 掩码显示
  - 查看 / 隐藏
  - 编辑
  - 保存
- 保存成功后提示“立即生效”
- 保存失败时就地高亮并给出错误提示

**测试：**

- 前端组件单测如已有测试基础则补
- 否则至少做页面级手动验证说明

**完成标准：**

- 用户可在设置页成功保存两个 Key
- 保存后重新发起请求能使用新 Key

### 阶段 6：聊天页灰色过程摘要框

**目标：** 用可解释摘要替换“AI 正在思考...”。

**新增文件：**

- `frontend/src/components/chat/StreamingTraceSummary.tsx`

**修改文件：**

- `frontend/src/pages/KnowledgeChatPage.tsx`
- `frontend/src/components/chat/ChatMessageList.tsx`
- `frontend/src/services/chatApi.ts`
- `frontend/src/hooks/useChat.ts`
- `frontend/src/types/chat.ts`

**任务：**

- 把生成中的占位状态改成灰色摘要框
- 复用当前 trace 数据：
  - canvas
  - tool loop
  - citation
  - reference store
- 将原始技术字段映射成短中文摘要
- 保留生成完成后的详细 trace 面板

**测试：**

- 前端构建通过
- 手动验证：
  - 发送消息时先看到灰色摘要框
  - 回答完成后灰色框消失/过渡到最终消息
  - 最终 trace 面板仍可展开

**完成标准：**

- 页面不再显示单一的“AI 正在思考...”
- 用户能看到生成中执行摘要

### 阶段 7：错误弹窗与交互收口

**目标：** 前端统一消费后端错误语义，稳定弹窗提示。

**任务：**

- 在聊天页接入统一错误提醒
- 在设置页接入保存失败提醒
- 在知识构建相关入口接入“未配置 API Key”提醒
- 增加错误码到中文文案映射

**测试：**

- 前端手动验证：
  - 未配置 Key
  - `402`
  - 鉴权失败
  - 网络错误

**完成标准：**

- 用户能稳定看到可理解的错误弹窗
- 不再直接暴露上游原始报错文案

## 5. P1 扩展顺序

P0 完成后，P1 建议按以下顺序推进：

1. 设置页增加 API 连接测试按钮
2. 支持更多 provider 配置项
3. 支持 base_url / model 可编辑
4. 更细的字段级错误校验
5. 更细粒度的灰色过程动画与阶段切换

## 6. 需要复用与拆解的现有能力

### 直接复用

- 当前 `.env` 配置体系
- 现有聊天 trace 数据
- 现有 `Canvas` / `AgentNode` 运行时
- 现有前端聊天页与 trace 面板

### 需要拆解迁移

- 各 service 中直接读取 `settings.*_api_key` 的逻辑
- 现有零散错误处理
- 现有“AI 正在思考...”占位状态

## 7. 风险控制

### 风险 1：写 `.env` 导致配置文件损坏

**控制：**

- 所有 `.env` 修改只允许通过 `env_store.py`
- 增加 `.env` 读写单测

### 风险 2：保存后并未真正热更新

**控制：**

- 模型调用统一通过 `ModelConfigService`
- 增加保存后立即读取验证

### 风险 3：错误码统一后前端未正确消费

**控制：**

- 后端定义稳定 `error_code`
- 前端建立统一错误文案映射

### 风险 4：灰色摘要框与最终 trace 面板冲突

**控制：**

- 摘要框只负责生成中状态
- 最终详细面板继续沿用现有结构

## 8. 推荐提交节奏

建议按阶段提交：

1. `feat: add runtime model config service`
2. `feat: add settings api for model config`
3. `refactor: route model clients through config service`
4. `feat: normalize upstream model errors`
5. `feat: add settings page for global api keys`
6. `feat: replace thinking placeholder with streaming trace summary`
7. `feat: add unified frontend error toasts for model failures`

## 9. 验收清单

- [ ] `.env` 可被安全更新
- [ ] 配置保存后后端无需重启即可生效
- [ ] 聊天与知识构建链路从统一配置中心读取 Key
- [ ] 存在设置页并支持掩码查看/编辑
- [ ] DeepSeek `402` 有稳定错误弹窗
- [ ] 未配置 Key 有稳定警告
- [ ] 聊天页生成中显示灰色执行轨迹摘要框
- [ ] 最终详细 trace 面板仍然保留
- [ ] 明显的模型配置硬编码入口被统一收口

## 10. 结论

本计划优先解决：

- 配置能否统一管理
- 配置能否立即生效
- 错误能否稳定提示
- 对话过程能否更可解释

而不是先做更重的 provider 平台化设计。这样最符合当前项目“本地个人项目、全局配置、快速稳定落地”的目标。
