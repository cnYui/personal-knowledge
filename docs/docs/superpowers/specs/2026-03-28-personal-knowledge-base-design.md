# 个人知识库管理界面设计文档

## 1. 项目概述

### 1.1 目标
构建一个前后端分离的个人知识库管理 Web 应用，面向个人学习笔记场景。用户可以上传文本和图片形式的学习内容，在浏览器中管理记忆，并通过对话界面与基于知识图谱和 RAG 的后端系统进行交互。

### 1.2 范围
本期范围包含 3 个前端页面和对应后端接口：

1. 记忆管理页面
2. 记忆上传页面
3. 知识库对话页面

### 1.3 非目标
以下内容不在本期范围内：

- 富文本编辑器
- 多用户系统
- 权限管理
- 实时 WebSocket 对话
- 知识图谱可视化页面
- 复杂复习系统或闪卡功能

## 2. 用户场景

### 2.1 目标用户
单个用户，主要用于个人学习笔记与已掌握知识的整理。

### 2.2 核心使用流程

#### 场景 A：上传新知识
1. 用户进入记忆上传页面。
2. 粘贴学习笔记文本。
3. 可选上传一张或多张相关图片。
4. 填写标题、标签、重要程度。
5. 提交后由后端保存文本、图片，并提取图片文字与语义描述。
6. 处理完成后，该知识可以被后续 RAG 对话检索使用。

#### 场景 B：管理历史记忆
1. 用户进入记忆管理页面。
2. 浏览、搜索、筛选已有记忆。
3. 修改标题、内容、标签等字段。
4. 删除错误或过期记忆。
5. 更新后的内容同步影响后续知识图谱关系构建。

#### 场景 C：知识库对话
1. 用户进入知识库对话页面。
2. 输入问题。
3. 后端调用现有知识图谱 + RAG 系统。
4. 返回基于已有学习内容的回答。
5. 用户继续追问，形成简单连续对话。

## 3. 总体架构

### 3.1 架构选择
采用前后端分离方案。

- 前端：React 18 + TypeScript + Material UI
- 后端：FastAPI + SQLAlchemy + PostgreSQL
- 文件存储：本地文件系统（开发阶段）
- 图片理解：OCR + 多模态模型描述
- 知识问答：对接现有知识图谱 / RAG 后端服务

### 3.2 架构图（逻辑）

1. 浏览器前端负责页面展示、表单交互、文件上传、对话交互。
2. FastAPI 后端负责 REST API、文件接收、数据持久化、图片处理调度。
3. PostgreSQL 存储记忆元数据与图片衍生文本。
4. 文件系统存储原始图片。
5. 知识图谱后端提供记忆同步与问答能力。

## 4. 前端设计

### 4.1 技术栈
- React 18
- TypeScript
- Vite
- React Router v6
- Material UI v5
- Axios
- TanStack Query（React Query）

### 4.2 前端项目结构

```text
frontend/
  src/
    app/
      router.tsx
      providers.tsx
    components/
      layout/
        AppLayout.tsx
        SideNav.tsx
        TopBar.tsx
      memory/
        MemoryCard.tsx
        MemoryFilterBar.tsx
        MemoryEditDialog.tsx
      upload/
        ImageUploadPanel.tsx
        UploadForm.tsx
      chat/
        ChatMessageList.tsx
        ChatInput.tsx
        EmptyChatState.tsx
      common/
        PageHeader.tsx
        LoadingState.tsx
        ConfirmDialog.tsx
        ErrorState.tsx
    pages/
      MemoryManagementPage.tsx
      MemoryUploadPage.tsx
      KnowledgeChatPage.tsx
    services/
      http.ts
      memoryApi.ts
      chatApi.ts
      uploadApi.ts
    hooks/
      useMemories.ts
      useUploadMemory.ts
      useChat.ts
    types/
      memory.ts
      chat.ts
      upload.ts
    utils/
      format.ts
      constants.ts
    App.tsx
    main.tsx
```

### 4.3 路由设计
- `/memories`：记忆管理页面
- `/upload`：记忆上传页面
- `/chat`：知识库对话页面
- `/`：默认重定向到 `/memories`

### 4.4 共享布局设计
整个系统使用统一后台式布局：

- 左侧导航栏：三个页面入口
- 顶部区域：页面标题与简要操作说明
- 主内容区：承载页面主体内容

该布局保证后续新增页面时可继续扩展。

## 5. 页面设计

### 5.1 记忆管理页面

#### 5.1.1 页面目标
提供记忆浏览、检索、编辑、删除能力。

#### 5.1.2 页面组成
- 页面标题区
- 搜索输入框
- 标签筛选区
- 记忆列表区
- 编辑对话框
- 删除确认弹窗

#### 5.1.3 列表项展示字段
每条记忆显示：
- 标题
- 内容摘要
- 标签
- 重要程度
- 创建时间
- 更新时间
- 图片数量

#### 5.1.4 交互行为
- 支持关键字搜索标题和内容
- 支持按标签筛选
- 点击卡片查看详细内容
- 点击编辑按钮打开弹窗修改
- 点击删除按钮后确认删除

#### 5.1.5 编辑范围
编辑弹窗支持修改：
- 标题
- 文本内容
- 标签
- 重要程度

本期不支持在编辑弹窗中重新上传或替换图片，避免范围膨胀。图片编辑可留待后续版本。

### 5.2 记忆上传页面

#### 5.2.1 页面目标
让用户快速上传文本和图片形式的学习内容。

#### 5.2.2 页面组成
- 标题输入框
- 文本内容输入区
- 标签输入组件
- 重要程度选择器
- 图片上传区
- 上传按钮
- 处理状态提示

#### 5.2.3 上传规则
- 文本内容必填
- 标题可选；若未填写，可由后端根据内容截取或生成默认标题
- 图片可选，可上传多张
- 支持常见图片格式：PNG、JPG、JPEG、WEBP

#### 5.2.4 上传成功后的行为
- 提示上传成功
- 清空表单或引导跳转到记忆管理页面
- 新记忆可立即被列表查询到
- 图片的 OCR 与多模态描述处理结果应最终进入检索语料

### 5.3 知识库对话页面

#### 5.3.1 页面目标
提供简单文本对话入口，让用户基于已存知识进行问答。

#### 5.3.2 页面组成
- 页面标题区
- 对话消息列表
- 输入框
- 发送按钮
- 清空对话按钮

#### 5.3.3 交互行为
- 用户输入文本问题并发送
- 展示发送中状态
- 返回 AI 回答后追加到对话区
- 对话按时间顺序展示
- 支持清空当前会话记录

#### 5.3.4 本期限制
本期先实现简单文本问答：
- 不支持上传附件进行对话
- 不支持 markdown 增强渲染之外的复杂富媒体
- 不支持图谱可视化

## 6. 后端设计

### 6.1 技术栈
- FastAPI
- SQLAlchemy
- Pydantic
- PostgreSQL
- Alembic
- python-multipart
- Pillow
- pytesseract
- httpx

### 6.2 后端项目结构

```text
backend/
  app/
    main.py
    core/
      config.py
      database.py
    models/
      memory.py
      chat.py
    schemas/
      memory.py
      chat.py
      upload.py
    routers/
      memories.py
      uploads.py
      chat.py
    services/
      memory_service.py
      image_processing_service.py
      multimodal_service.py
      knowledge_graph_service.py
      chat_service.py
    repositories/
      memory_repository.py
      chat_repository.py
    utils/
      file_storage.py
      time.py
  uploads/
    images/
  requirements.txt
```

### 6.3 数据模型设计

#### 6.3.1 Memory
字段：
- `id`: UUID
- `title`: string
- `content`: text
- `tags`: JSON 数组
- `importance`: integer，范围 1-5
- `created_at`: datetime
- `updated_at`: datetime

#### 6.3.2 MemoryImage
字段：
- `id`: UUID
- `memory_id`: UUID，外键
- `original_file_name`: string
- `stored_path`: string
- `ocr_text`: text，可为空
- `image_description`: text，可为空
- `created_at`: datetime

#### 6.3.3 ChatMessage
字段：
- `id`: UUID
- `role`: string，`user` 或 `assistant`
- `content`: text
- `created_at`: datetime

### 6.4 为什么保留时间字段
时间属性是核心需求之一，因为知识图谱中的关系存在演进：

- 新学习内容可能覆盖旧认知
- 更新后的记忆需要通过 `updated_at` 体现知识的新鲜度
- 图谱构建时可基于时间戳判断关系优先级或有效性

因此，记忆和相关衍生内容必须保留清晰时间信息。

## 7. API 设计

### 7.1 记忆管理 API

#### `GET /api/memories`
功能：分页查询记忆列表，支持搜索和标签过滤。

查询参数：
- `keyword`：可选
- `tag`：可选
- `page`：可选
- `page_size`：可选

#### `GET /api/memories/{memory_id}`
功能：获取单条记忆详情。

#### `PUT /api/memories/{memory_id}`
功能：更新记忆。

请求体包含：
- `title`
- `content`
- `tags`
- `importance`

#### `DELETE /api/memories/{memory_id}`
功能：删除记忆及其关联图片元数据。

### 7.2 上传 API

#### `POST /api/uploads/memories`
功能：上传一条新记忆及其图片。

表单字段：
- `title`
- `content`
- `tags`
- `importance`
- `images[]`

返回：
- 新建 memory 的基础信息
- 图片处理状态

### 7.3 对话 API

#### `POST /api/chat/messages`
功能：发送一条用户消息并获取助手回答。

请求体：
- `message`

返回：
- `answer`
- 可选 `references`（后期可扩展返回命中的记忆）

#### `GET /api/chat/messages`
功能：获取当前简单会话历史。

#### `DELETE /api/chat/messages`
功能：清空当前会话历史。

## 8. 图片处理设计

### 8.1 处理策略
采用“原图保留 + 单模态文本衍生”的混合方案：

- 保留原图，供后续查看和追溯
- 提取 OCR 文本
- 生成图像语义描述
- 将 OCR 文本和图像描述一并纳入可检索文本

### 8.2 原因
这种方案兼顾：
- 用户回看原始学习资料的需求
- 检索系统对文本语料的适配能力
- 后续如果更换向量化策略或图像理解模型，仍可复用原图

### 8.3 处理流程
1. 上传图片并保存原图。
2. 使用 OCR 提取图片中文字。
3. 调用多模态模型生成图片语义描述。
4. 保存结果到 `MemoryImage`。
5. 将文本结果同步到知识图谱 / RAG 建库流程。

### 8.4 错误处理
- OCR 失败不应导致整条记忆创建失败
- 多模态描述失败不应阻塞文本记忆入库
- 后端需要返回可见状态，让前端提示“图片处理部分失败，但记忆已保存”

## 9. 知识图谱集成设计

### 9.1 集成边界
本项目不实现知识图谱算法与 RAG 核心逻辑，只定义接口边界。

### 9.2 后端职责
本系统后端负责：
- 标准化记忆数据
- 管理图片衍生文本
- 将记忆及相关文本同步到知识图谱系统
- 在聊天接口中转发查询请求并返回答案

### 9.3 依赖的外部能力
需要现有知识图谱系统提供至少两类能力：
- 记忆写入或更新接口
- 问答检索接口

### 9.4 推荐外部接口
- `POST /kg/memories`
- `PUT /kg/memories/{id}`
- `DELETE /kg/memories/{id}`
- `POST /kg/query`

本项目后端不直接依赖具体实现，只通过配置的 API Base URL 对接。

## 10. 状态管理与错误处理

### 10.1 前端状态管理
- 服务端数据使用 React Query 管理
- 页面局部交互状态使用 React state
- 全局只保留最小共享状态，不引入额外复杂状态库

### 10.2 常见错误场景
- 上传文件格式不合法
- 图片处理失败
- 知识图谱服务不可用
- 获取记忆列表失败
- 对话请求超时

### 10.3 前端反馈原则
- 操作成功使用轻量提示
- 删除操作使用确认弹窗
- 加载中显示明确状态
- API 失败显示可读错误信息

## 11. 测试策略

### 11.1 前端测试
- 组件单元测试：核心交互组件
- 页面集成测试：上传、编辑、删除、发送消息
- 至少覆盖关键表单校验和主要状态流转

### 11.2 后端测试
- API 测试：增删改查、上传、聊天接口
- 服务层测试：图片处理、知识图谱调用封装
- 数据模型测试：字段约束与序列化

### 11.3 验证重点
- 文本记忆能成功创建
- 图片上传能成功保存
- OCR / 多模态失败时系统仍能保存主体数据
- 记忆修改后更新时间正确刷新
- 对话接口能正确透传知识图谱回答

## 12. 部署与配置

### 12.1 开发环境
- 前端本地运行于 Vite 开发服务器
- 后端本地运行于 FastAPI Uvicorn
- 前端通过环境变量配置 API Base URL

### 12.2 必要配置项
前端：
- `VITE_API_BASE_URL`

后端：
- `DATABASE_URL`
- `UPLOAD_DIR`
- `OCR_ENABLED`
- `MULTIMODAL_PROVIDER`
- `MULTIMODAL_API_KEY`
- `KNOWLEDGE_GRAPH_BASE_URL`

### 12.3 安全注意事项
- API Key 不写入前端
- 上传文件类型与大小需要校验
- 后端对文件名进行安全处理

## 13. 分阶段实现建议

### 阶段 1
- 初始化前后端项目
- 完成页面框架和基础路由
- 完成记忆 CRUD API

### 阶段 2
- 完成记忆上传和图片保存
- 接入 OCR 与多模态处理

### 阶段 3
- 完成知识库对话页面与聊天 API
- 打通知识图谱问答接口

## 14. 验收标准

满足以下条件即可认为本期完成：

1. 前端存在 3 个可访问页面。
2. 用户可创建、查看、编辑、删除文本记忆。
3. 用户可上传文本与图片记忆。
4. 后端可保存原图，并保存 OCR / 图像描述文本结果。
5. 用户可在对话页面发送问题并收到后端返回回答。
6. 记忆数据包含时间信息，供知识图谱关系演进使用。

## 15. 开放问题

以下点先采用默认方案，不阻塞实施：

- 图片数量限制：默认单次最多 5 张
- 单张图片大小限制：默认 10MB
- 标题为空时：默认由内容前若干字符生成
- 会话历史存储：本期先存数据库，按简单单用户模式处理

这些默认值可以在实施阶段通过配置项细化。
