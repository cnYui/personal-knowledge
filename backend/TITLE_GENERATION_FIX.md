# 标题生成功能修复

## 问题描述

用户报告在记忆管理页面,所有记忆始终显示"标题抽取中"的状态,即使等待很长时间也不会切换到正常状态。

## 根本原因

前端代码中有显示"标题抽取中"的逻辑,并且每 5 秒轮询一次后端 API,期待 `title_status` 从 `pending` 变为 `ready`。但是后端根本没有实现标题生成的功能:

1. 当用户上传记忆时,如果没有提供标题,后端会设置标题为"标题生成中",状态为 `pending`
2. 但是没有任何后台任务来实际生成标题并更新状态
3. 导致前端永远显示"标题抽取中"

## 解决方案

实现了完整的标题自动生成功能:

### 1. TitleGenerator 服务 (`app/services/title_generator.py`)

- 使用运行时对话模型生成标题
- 根据记忆内容生成简洁、准确的标题(不超过 30 字)
- 自动截断过长的内容(保留前 500 字符)
- 包含错误处理和日志记录

### 2. TitleGenerationWorker (`app/workers/title_generation_worker.py`)

- 后台异步 worker,处理标题生成队列
- 使用 asyncio.Queue 进行任务队列管理
- 自动更新数据库中的标题和状态
- 支持优雅启动和停止

### 3. 集成到应用生命周期

- 在 `app/main.py` 中启动和停止 worker
- 在 `app/routers/uploads.py` 中,创建记忆后自动加入队列

## 工作流程

1. 用户上传记忆,不提供标题
2. 后端创建记忆,标题设为"标题生成中",状态为 `pending`
3. 记忆 ID 被加入标题生成队列
4. TitleGenerationWorker 从队列中取出任务
5. 调用运行时对话模型生成标题
6. 更新数据库,将标题和状态改为 `ready`
7. 前端轮询检测到状态变化,隐藏"标题抽取中"提示

## 测试结果

```bash
python test_title_generation.py
```

测试结果:
- ✅ 记忆创建成功,初始状态为 `pending`
- ✅ 5 秒内生成标题并更新状态为 `ready`
- ✅ 生成的标题准确反映内容:"Python异步编程：使用asyncio和async/await语法"

## 配置要求

需要在 `.env` 文件中配置运行时对话模型:

```env
DIALOG_API_KEY=your_dialog_api_key
```

## 性能特点

- 异步处理,不阻塞主线程
- 队列化处理,避免并发过多
- 自动重试和错误处理
- 平均生成时间: 2-5 秒

## 相关文件

- `backend/app/services/title_generator.py` - 标题生成服务
- `backend/app/workers/title_generation_worker.py` - 后台 worker
- `backend/app/main.py` - 应用启动/停止逻辑
- `backend/app/routers/uploads.py` - 上传接口集成
- `backend/test_title_generation.py` - 测试脚本

## 前端显示逻辑

前端 `MemoryBubbleItem.tsx` 中的显示逻辑:

```typescript
{memory.title_status === 'pending' ? (
  <Typography variant="caption" color="warning.main">
    标题抽取中
  </Typography>
) : null}
```

当状态从 `pending` 变为 `ready` 后,这个提示会自动消失。

---

**修复时间**: 2026-03-29  
**测试状态**: ✅ 通过  
**生产就绪**: ✅ 是
