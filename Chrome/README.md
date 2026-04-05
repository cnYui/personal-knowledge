# 个人知识库浏览器插件

这是一个与 `personal-knowledge-base` 配套使用的浏览器插件，用于提升多模型长对话场景下的浏览与定位效率，并支持将 AI 页面中的选中文本直接保存到个人知识库，适用于 ChatGPT、Gemini、Kimi、通义千问、豆包等主流 AI 平台。

## 功能特点

- **悬浮式知识面板** - 在页面中提供可自由拖拽的导航与采集面板，不影响正常阅读
- **智能识别问题** - 自动通过选择器识别并汇总用户提出的每一条问题，生成清晰的对话索引列表
- **快速跳转** - 点击任意条目即可平滑滚动至对应对话位置，实现快速跳转
- **自动高亮** - 实时检测当前可视区域，对正在阅读的对话项进行自动高亮，帮助用户保持上下文感知
- **实时更新** - 支持定时检测新消息，在对话持续增长时自动更新导航内容，无需刷新页面
- **知识采集** - 选中 AI 页面中的文字后，可在侧边面板里编辑标题和正文，并直接保存到个人知识库的记忆管理页

## 支持平台

| 平台 | 网址 |
|------|------|
| **ChatGPT** | chatgpt.com / chat.openai.com |
| **Gemini** | gemini.google.com |
| **Kimi** | kimi.com / www.kimi.com / kimi.moonshot.cn |
| **通义千问** | tongyi.aliyun.com / qianwen.com |
| **豆包** | doubao.com / www.doubao.com |

## 安装方法

### Chrome / Edge
1. 打开浏览器，访问 `chrome://extensions/`（Edge 访问 `edge://extensions/`）
2. 开启右上角的 **开发者模式**
3. 点击 **加载已解压的扩展程序**
4. 选择当前目录作为插件文件夹

> 当前项目推荐加载目录：`D:\CodeWorkSpace\personal-knowledge-base\Chrome`

### Firefox
1. 访问 `about:debugging#/runtime/this-firefox`
2. 点击 **加载临时附加组件**
3. 选择 `manifest.json` 文件

## 使用说明

- 插件会在对话页面右侧显示「个人知识库」浮动面板
- 可通过标题左侧拖拽点把面板移动到页面任意位置
- 点击条目可平滑跳转到对应对话位置
- 当前位置会自动高亮显示
- 图片消息会显示为 `[图片]`
- 顶部/底部按钮可快速跳转到页面顶部或底部
- 面板顶部只保留 2 个核心按钮：
  - `↑ 顶部`
  - `↓ 底部`
- 在 AI 页面中选中文字后，侧边面板会出现 `保存选中文本`
- 点击 `保存选中文本` 会进入保存表单
- 点击后可编辑：
  - 标题
  - 正文
  - 保存接口
- 默认保存接口是：`http://127.0.0.1:8000/api/memories/clip`
- 保存成功后，内容会进入个人知识库的 `记忆管理` 页面，作为普通记忆保存，不会自动入图谱

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Alt + J` | 切换导航面板显示/隐藏 |
| `Alt + ↑` | 跳转到上一条对话 |
| `Alt + ↓` | 跳转到下一条对话 |

---

## 🔧 如何查看 DOM 选择器（详细教程）

如果插件无法识别用户消息，你需要手动查找正确的选择器。

### 步骤 1：打开开发者工具
- **快捷键**：按 `F12` 或 `Ctrl+Shift+I`（Mac: `Cmd+Option+I`）
- 或右键页面 → 选择「检查」/「Inspect」

### 步骤 2：选择元素
1. 点击开发者工具左上角的 **选择元素按钮**（箭头图标）或按 `Ctrl+Shift+C`
2. 在页面上点击你发送的 **用户消息**（不是 AI 回复）
3. 开发者工具会自动定位到该元素的 HTML 代码

### 步骤 3：分析元素特征
在 Elements 面板中，找到用户消息的父容器，观察它的特征：

```html
<!-- 示例：假设你看到这样的结构 -->
<div class="chat-message user-message" data-role="user">
  <div class="message-content">你好</div>
</div>
```

可以使用的选择器格式：
- **class 属性**：`.user-message` 或 `[class*="user"]`（包含 user 的类名）
- **data 属性**：`[data-role="user"]`
- **组合选择器**：`.chat-message.user-message`

### 步骤 4：测试选择器
在开发者工具的 Console 面板中输入：
```javascript
document.querySelectorAll('你的选择器')
```
如果返回的元素数量等于你发送的消息数，说明选择器正确。

### 步骤 5：更新代码
打开 `content/platforms.js`，找到对应平台的 `selectors` 数组，添加新选择器：
```javascript
kimi: {
  selectors: [
    '你找到的新选择器',  // 添加到这里
    // ... 其他选择器
  ],
}
```

---

## 📦 插件上架指南

### Chrome Web Store

1. **注册开发者账号**
   - 访问 [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)
   - 需要支付 **$5 一次性注册费**（需要信用卡）

2. **准备材料**
   - 插件 ZIP 包（将整个文件夹打包）
   - 128×128 图标
   - 至少 1 张 1280×800 或 640×400 的截图
   - 详细描述（支持多语言）

3. **提交审核**
   - 登录后点击「New Item」上传 ZIP
   - 填写商品详情、截图、定价（免费）
   - 提交审核，通常 1-3 个工作日

### Microsoft Edge Add-ons

1. **注册开发者账号**
   - 访问 [Edge Add-ons Developer Dashboard](https://partner.microsoft.com/dashboard/microsoftedge)
   - **免费注册**，使用 Microsoft 账号

2. **准备材料**
   - 与 Chrome 相同，Manifest V3 插件可直接使用
   - 需要隐私政策 URL（可用 GitHub Gist 创建）

3. **提交审核**
   - 上传 ZIP，填写信息
   - 审核时间约 1-7 个工作日

### Firefox Add-ons (AMO)

1. **注册开发者账号**
   - 访问 [Firefox Add-on Developer Hub](https://addons.mozilla.org/developers/)
   - **免费注册**，使用 Firefox 账号

2. **修改 manifest.json**
   Firefox 需要添加 `browser_specific_settings`：
   ```json
   {
     "browser_specific_settings": {
       "gecko": {
         "id": "ai-chat-navigator@youremail.com",
         "strict_min_version": "109.0"
       }
     }
   }
   ```

3. **提交审核**
   - 上传 ZIP，可选择「Listed」（公开）或「Unlisted」（仅链接访问）
   - 自动审核通常几分钟，人工审核 1-2 周

---

## 许可证

MIT License
