# Anthropic 风格前端品牌化重构设计

日期：2026-04-03

## 目标

将当前 `personal-knowledge-base` 前端从现有的蓝灰色后台工作台风格，重构为更接近 `brand-guidelines` 中 Anthropic 风格的浅色、克制、编辑型知识工作台。

本次重构重点覆盖：

- 全局配色
- 字体体系
- 按钮、输入框、卡片、提示条等基础控件
- 左侧导航、顶部栏、页面外壳
- 五个核心页面的视觉统一

本次重构不修改：

- 路由结构
- 数据流与后端接口
- 聊天、上传、图谱等业务能力本身
- 图谱可视化内核逻辑

## 视觉方向

### 品牌基调

采用 `brand-guidelines` 中的 Anthropic 风格作为视觉参考，整体保持：

- 浅色单主题
- 暖白纸面背景
- 深墨文字
- 极少强调色
- 更像研究、写作、知识整理工具，而不是典型 SaaS 管理后台

### 色彩系统

主要颜色：

- 深色文本与深背景：`#141413`
- 主背景浅色：`#faf9f5`
- 中灰：`#b0aea5`
- 浅灰层次：`#e8e6dc`

强调色仅作极少量局部辅助：

- 橙色：`#d97757`
- 蓝色：`#6a9bcc`
- 绿色：`#788c5d`

强调色不会像现有方案那样大面积主导按钮和导航，只用于：

- 成功/完成状态轻提示
- 少量可交互高亮
- 引用、步骤状态或轻微装饰

### 字体系统

遵循技能建议：

- 标题：`Poppins, Arial, sans-serif`
- 正文：`Lora, Georgia, serif`

同时考虑产品可用性：

- 页面大标题、模块标题、品牌标题采用更克制的 `Poppins`
- 大段正文、说明、回答内容使用更有阅读感的 `Lora`
- 导航、按钮、输入框标签保持无衬线可读性，但整体仍在同一品牌语境中

## 布局与外壳

### 左侧导航

当前左侧深色导航将被替换为浅色纸面式竖向导航。

目标变化：

- 从深色块状产品壳，改为浅暖色工作区边栏
- 保留现有导航信息架构
- 当前页高亮改为浅底或细边框高亮
- 品牌区只保留“个人知识库”，不再呈现英文强品牌块感

### 顶部栏

顶部栏保留当前“页面标题 + 页面说明”的信息结构，但视觉会转为更像文档页眉：

- 更浅的背景
- 更弱的分隔线
- 减弱玻璃感和 app shell 感
- 保持当前每个页面独立的标题与说明文案

### 内容区

内容区的整体策略是：

- 减少“重阴影卡片堆叠”的后台感
- 提高留白与文本节奏
- 使用纸面感容器和柔和边框来组织内容
- 用排版秩序而不是强对比块感来划分区域

## 页面级改造范围

### 记忆管理

定位为知识条目浏览与维护页：

- 搜索框改为更接近文稿搜索入口
- 记忆卡片改为更轻、更像目录条目
- 图谱状态标签弱化成更自然的注释式状态

### 记忆上传

定位为资料整理工作台：

- 提示词编辑器更像编辑区，而不是后台配置面板
- 上传区域更像文稿投递或资料导入入口
- 统一提示词内容字体与正文风格

### 知识对话

定位为研究助理式对话界面：

- 保留现有聊天结构
- 思考过程卡片更像可展开注释
- 回答卡片更像稿件或研究回复
- 引用更像脚注系统

### 知识图谱

定位为图谱浏览工作台：

- 图谱外层容器纸面化
- 节点详情更像注释栏
- 弱化当前的后台控制面板感

### 设置

定位为最简洁的配置页：

- 保留 API Key 卡片
- 删除多余的品牌说明块
- 让表单更安静、更聚焦于编辑行为本身

## 主题与组件层改动

### 主题层

核心文件：

- `frontend/src/app/providers.tsx`

将统一调整：

- palette
- typography
- shape
- MuiButton
- MuiOutlinedInput
- MuiPaper
- MuiAlert
- MuiChip
- MuiAccordion
- MuiCssBaseline

### 布局层

核心文件：

- `frontend/src/components/layout/AppLayout.tsx`
- `frontend/src/components/layout/SideNav.tsx`
- `frontend/src/components/layout/TopBar.tsx`

此层负责建立 Anthropic 风格的第一眼印象。

### 高影响组件

重点组件：

- `frontend/src/components/chat/ChatMessageList.tsx`
- `frontend/src/components/memory/MemoryFilterBar.tsx`
- `frontend/src/components/memory/MemoryBubbleItem.tsx`
- `frontend/src/components/upload/PromptEditor.tsx`
- `frontend/src/components/upload/UploadForm.tsx`
- `frontend/src/components/graph/NodeDetailPanel.tsx`

这些组件负责把品牌语言落实到实际页面观感。

### 页面容器

重点页面：

- `frontend/src/pages/MemoryManagementPage.tsx`
- `frontend/src/pages/MemoryUploadPage.tsx`
- `frontend/src/pages/KnowledgeChatPage.tsx`
- `frontend/src/pages/KnowledgeGraphPage.tsx`
- `frontend/src/pages/SettingsPage.tsx`

主要调整间距、留白、按钮位置、内容区节奏，不改业务行为。

## 实施顺序

1. 调整主题层
2. 调整外壳与导航
3. 调整高影响页面与核心组件
4. 统一收口并构建验证

## 验收标准

重构完成后应满足：

- 全站从蓝灰后台感转为 Anthropic 风格的浅色单主题
- 左侧导航、顶部栏、按钮、输入框、卡片语气统一
- 五个页面视觉一致但各自保留角色感
- 聊天、上传、图谱、设置等功能行为不受影响
- 前端构建通过

## 风险与边界

主要风险：

- 字体切换后可能影响现有中文内容的观感与密度
- `Lora` 在中文环境下会回退到系统字体，需要通过层级和配色弥补质感
- 图谱页视觉重构不能影响图谱容器可用性

明确边界：

- 不新增复杂动画系统
- 不重做页面信息架构
- 不引入新的页面或交互流程

本次是品牌化前端重构，不是功能重构。
