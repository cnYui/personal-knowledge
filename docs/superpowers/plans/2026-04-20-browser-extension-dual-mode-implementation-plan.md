# Browser Extension Dual-Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将浏览器插件从固定 AI 平台专用工具扩展为双模式插件，使其在普通网页中也能以轻量摘录模式出现，同时保留现有 AI 平台页面中的完整导航能力。

**Architecture:** 继续复用当前 content script 面板壳、拖拽吸附、选区保存链路，不引入新的前端框架。通过在 `platforms.js` 中新增纯函数页面上下文判定，在 `main.js` 中按 `platform` / `generic` 两种模式有条件启用导航增强能力，在 `ui.js` 中切换区块显隐，实现双模式运行。

**Tech Stack:** Chrome Extension Manifest V3、原生 content script JavaScript、CSS、Node.js 内建 `node:test` 测试运行器

---

## File Structure

- Modify: `Chrome/manifest.json`
  - 将 content script 注入范围扩展到所有 `http/https` 普通网页
- Modify: `Chrome/content/platforms.js`
  - 保留平台配置，并新增可测试的页面上下文解析函数
- Modify: `Chrome/content/main.js`
  - 统一初始化流程，按页面模式决定是否启用导航控制器与轮询
- Modify: `Chrome/content/ui.js`
  - 面板区块显隐控制、普通网页提示文案、对外导出的轻量 UI 状态函数
- Modify: `Chrome/styles.css`
  - 普通网页模式提示块样式与隐藏导航区块后的布局收口
- Modify: `Chrome/README.md`
  - 更新插件的“双模式”说明、安装后表现与使用说明
- Create: `Chrome/tests/dual-mode.test.js`
  - 使用 `node:test` 锁定页面模式判定、manifest 范围和 UI 区块状态

## Task 1: Add Page Context Resolution

**Files:**
- Create: `Chrome/tests/dual-mode.test.js`
- Modify: `Chrome/content/platforms.js`
- Test: `Chrome/tests/dual-mode.test.js`

- [ ] **Step 1: Write the failing test**

```javascript
const test = require('node:test');
const assert = require('node:assert/strict');

const { detectPlatform, resolvePageContext } = require('../content/platforms.js');

test('resolvePageContext returns platform mode for known AI hosts', () => {
  assert.equal(detectPlatform('chatgpt.com'), 'chatgpt');
  assert.deepEqual(
    resolvePageContext({ hostname: 'chatgpt.com', protocol: 'https:' }),
    {
      pageMode: 'platform',
      platformKey: 'chatgpt',
      platformName: 'ChatGPT',
      sourcePlatform: 'chatgpt',
      themeClass: 'chatgpt-theme',
    },
  );
});

test('resolvePageContext falls back to generic mode for ordinary webpages', () => {
  assert.deepEqual(
    resolvePageContext({ hostname: 'example.com', protocol: 'https:' }),
    {
      pageMode: 'generic',
      platformKey: null,
      platformName: '普通网页',
      sourcePlatform: 'generic_web',
      themeClass: 'generic-theme',
    },
  );
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
node --test Chrome/tests/dual-mode.test.js
```

Expected: FAIL with `resolvePageContext is not a function` or `detectPlatform` not exportable from Node.

- [ ] **Step 3: Write minimal implementation**

```javascript
function detectPlatform(hostname) {
  const resolvedHostname =
    hostname != null ? hostname : (typeof window !== 'undefined' ? window.location.hostname : '');

  for (const [key, config] of Object.entries(PLATFORM_CONFIG)) {
    if (config.hostPatterns.some((pattern) => resolvedHostname.includes(pattern))) {
      return key;
    }
  }
  return null;
}

function resolvePageContext({ hostname = '', protocol = 'https:' } = {}) {
  const platformKey = detectPlatform(hostname);
  if (platformKey) {
    const platform = PLATFORM_CONFIG[platformKey];
    return {
      pageMode: 'platform',
      platformKey,
      platformName: platform.name,
      sourcePlatform: platformKey,
      themeClass: platform.themeClass || '',
    };
  }

  if (protocol === 'http:' || protocol === 'https:') {
    return {
      pageMode: 'generic',
      platformKey: null,
      platformName: '普通网页',
      sourcePlatform: 'generic_web',
      themeClass: 'generic-theme',
    };
  }

  return {
    pageMode: null,
    platformKey: null,
    platformName: '',
    sourcePlatform: '',
    themeClass: '',
  };
}

const api = {
  PLATFORM_CONFIG,
  INPUT_SELECTORS,
  detectPlatform,
  getCurrentPlatformName,
  resolvePageContext,
};

globalThis.JumpAIPlatforms = api;

if (typeof module !== 'undefined' && module.exports) {
  module.exports = api;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
node --test Chrome/tests/dual-mode.test.js
```

Expected: PASS for the two page-context tests.

- [ ] **Step 5: Commit**

```bash
git add Chrome/content/platforms.js Chrome/tests/dual-mode.test.js
git commit -m "test: add page context resolution for extension modes"
```

## Task 2: Expand Manifest Injection Scope

**Files:**
- Modify: `Chrome/manifest.json`
- Modify: `Chrome/tests/dual-mode.test.js`
- Test: `Chrome/tests/dual-mode.test.js`

- [ ] **Step 1: Write the failing test**

Append this test to `Chrome/tests/dual-mode.test.js`:

```javascript
const fs = require('node:fs');
const path = require('node:path');

test('manifest injects content scripts into general http and https pages', () => {
  const manifest = JSON.parse(
    fs.readFileSync(path.join(__dirname, '..', 'manifest.json'), 'utf8'),
  );

  const matches = manifest.content_scripts[0].matches;
  assert.ok(matches.includes('http://*/*'));
  assert.ok(matches.includes('https://*/*'));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
node --test Chrome/tests/dual-mode.test.js
```

Expected: FAIL because `manifest.json` still only contains the fixed AI platform URLs.

- [ ] **Step 3: Write minimal implementation**

Replace the `content_scripts[0].matches` list in `Chrome/manifest.json` with:

```json
"matches": [
  "http://*/*",
  "https://*/*"
]
```

Keep the existing `js` and `css` file order unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
node --test Chrome/tests/dual-mode.test.js
```

Expected: PASS for page-context tests and manifest-scope test.

- [ ] **Step 5: Commit**

```bash
git add Chrome/manifest.json Chrome/tests/dual-mode.test.js
git commit -m "feat: inject extension on general webpages"
```

## Task 3: Add Generic-Mode UI and Runtime Gating

**Files:**
- Modify: `Chrome/content/main.js`
- Modify: `Chrome/content/ui.js`
- Modify: `Chrome/styles.css`
- Modify: `Chrome/tests/dual-mode.test.js`
- Test: `Chrome/tests/dual-mode.test.js`

- [ ] **Step 1: Write the failing test**

Append this test to `Chrome/tests/dual-mode.test.js`:

```javascript
const { getPanelSectionState } = require('../content/ui.js');

test('generic mode hides navigation-only panel sections', () => {
  assert.deepEqual(getPanelSectionState('platform'), {
    showJumpButtons: true,
    showSearch: true,
    showNavigation: true,
    showHint: false,
  });

  assert.deepEqual(getPanelSectionState('generic'), {
    showJumpButtons: false,
    showSearch: false,
    showNavigation: false,
    showHint: true,
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
node --test Chrome/tests/dual-mode.test.js
```

Expected: FAIL because `getPanelSectionState` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

In `Chrome/content/ui.js`, add a pure helper and section toggling:

```javascript
function getPanelSectionState(pageMode) {
  if (pageMode === 'platform') {
    return {
      showJumpButtons: true,
      showSearch: true,
      showNavigation: true,
      showHint: false,
    };
  }

  return {
    showJumpButtons: false,
    showSearch: false,
    showNavigation: false,
    showHint: true,
  };
}

function applyPanelSectionState(refs, pageMode) {
  const state = getPanelSectionState(pageMode);
  refs.panel.dataset.pageMode = pageMode;
  refs.jumpBtns.style.display = state.showJumpButtons ? 'flex' : 'none';
  refs.searchWrapper.style.display = state.showSearch ? 'block' : 'none';
  refs.scrollContainer.style.display = state.showNavigation ? 'block' : 'none';
  refs.genericHint.style.display = state.showHint ? 'block' : 'none';
}
```

Extend `createPanelShell()` so it creates and returns `genericHint`, `jumpBtns`, and `searchWrapper`:

```javascript
const genericHint = document.createElement('div');
genericHint.id = 'ai-nav-generic-hint';
genericHint.textContent = '选中网页中的文字后可直接保存到知识库';
panel.appendChild(genericHint);

return {
  panel,
  jumpTopBtn,
  jumpBottomBtn,
  jumpBtns,
  searchWrapper,
  searchInput,
  scrollContainer,
  saveEntry,
  saveStatus,
  dragHandle,
  tooltip,
  dockHoverTrigger,
  genericHint,
};
```

Export the helper for Node:

```javascript
globalThis.JumpAIUI = {
  updatePanelPosition,
  updateDockHoverTrigger,
  createPanelShell,
  refreshCaptureEntry,
  setSaveStatus,
  createPanelInteractionController,
  getPanelSectionState,
  applyPanelSectionState,
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    getPanelSectionState,
  };
}
```

In `Chrome/content/main.js`, gate navigation by page mode:

```javascript
const { PLATFORM_CONFIG, resolvePageContext } = globalThis.JumpAIPlatforms;
const { createPanelShell, applyPanelSectionState } = globalThis.JumpAIUI;

let pageContext = {
  pageMode: null,
  platformKey: null,
  platformName: '',
  sourcePlatform: '',
  themeClass: '',
};
let pageMode = null;
let navigationRefreshTimer = null;

function getCurrentPlatformName() {
  return pageContext.platformName || '普通网页';
}

function buildCurrentSelectionMeta() {
  if (!selectedText) return null;
  return buildSelectionMeta(
    selectedText,
    pageContext.sourcePlatform,
    getCurrentPlatformName(),
    location.href,
  );
}

function createPanel() {
  if (navPanel) return;

  ({
    panel: navPanel,
    jumpTopBtn,
    jumpBottomBtn,
    jumpBtns,
    searchWrapper,
    searchInput,
    scrollContainer,
    saveEntry,
    saveStatus,
    dragHandle,
    tooltip,
    dockHoverTrigger,
    genericHint,
  } = createPanelShell(pageContext.themeClass || ''));

  applyPanelSectionState(
    { panel: navPanel, jumpBtns, searchWrapper, scrollContainer, genericHint },
    pageMode,
  );

  if (pageMode === 'platform') {
    jumpTopBtn.addEventListener('click', () => {
      scrollPageTo(getQuestions(currentPlatform, PLATFORM_CONFIG), 'top');
    });

    jumpBottomBtn.addEventListener('click', () => {
      scrollPageTo(getQuestions(currentPlatform, PLATFORM_CONFIG), 'bottom');
    });

    navigationController = createNavigationController({
      getScrollContainer: () => scrollContainer,
      getCurrentActiveIndex: () => currentActiveIndex,
      setCurrentActiveIndex: (value) => { currentActiveIndex = value; },
      getCurrentSearchTerm: () => currentSearchTerm.trim().toLowerCase(),
      getVisibleItems: () => 6,
      getItemHeight: () => 44,
      getQuestions: () => getQuestions(currentPlatform, PLATFORM_CONFIG),
      getQuestionText: (question) => getQuestionText(question, currentPlatform, PLATFORM_CONFIG),
      activateQuestion: (index, question) => {
        currentActiveIndex = index;
        question.scrollIntoView({ behavior: 'smooth', block: 'center' });
      },
      showTooltip: (text, item) => {
        if (!tooltip || !item || !text) return;
        const rect = item.getBoundingClientRect();
        tooltip.textContent = text;
        tooltip.style.display = 'block';
        tooltip.style.left = `${Math.min(window.innerWidth - 280, rect.left)}px`;
        tooltip.style.top = `${Math.max(8, rect.top - 36)}px`;
      },
      hideTooltip: () => {
        if (!tooltip) return;
        tooltip.style.display = 'none';
      },
      setLastQuestionCount: (value) => { lastQuestionCount = value; },
      getLastQuestionCount: () => lastQuestionCount,
      getNavPanel: () => navPanel,
    });

    searchInput.addEventListener('input', (event) => {
      currentSearchTerm = event.target.value || '';
      navigationController.rebuildNavigation(getQuestions(currentPlatform, PLATFORM_CONFIG), false);
    });

    navigationController.rebuildNavigation(getQuestions(currentPlatform, PLATFORM_CONFIG), false);
    navigationController.setupScrollObserver();
  }
}

async function init() {
  pageContext = resolvePageContext({
    hostname: location.hostname,
    protocol: location.protocol,
  });

  if (!pageContext.pageMode) {
    return;
  }

  pageMode = pageContext.pageMode;
  currentPlatform = pageContext.platformKey;

  createPanel();
  knowledgeCaptureApiUrl = await loadKnowledgeCaptureApi();

  document.addEventListener('selectionchange', updateSelectionState);
  document.addEventListener('mouseup', () => setTimeout(updateSelectionState, 0));

  if (pageMode === 'platform') {
    document.addEventListener('keydown', (event) => navigationController?.handleKeyboardShortcut?.(event));
    navigationRefreshTimer = window.setInterval(() => {
      navigationController?.checkForNewMessages?.();
    }, 1500);
  }

  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      ensurePanelVisible(false);
      if (pageMode === 'platform') {
        navigationController?.checkForNewMessages?.();
      }
    }
  });

  window.addEventListener('resize', () => ensurePanelVisible(true));
  updateSelectionState();
}
```

In `Chrome/styles.css`, add the generic hint styling:

```css
#ai-nav-generic-hint {
  display: none;
  margin: 0 2px 10px;
  padding: 10px 12px;
  border: 1px dashed var(--pkb-border);
  border-radius: 8px;
  background: rgba(232, 230, 220, 0.18);
  font-size: 11px;
  color: var(--pkb-text-soft);
  line-height: 1.6;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
node --test Chrome/tests/dual-mode.test.js
node --check Chrome/content/platforms.js
node --check Chrome/content/ui.js
node --check Chrome/content/main.js
```

Expected:

- `node --test` shows all tests PASS
- each `node --check` command exits with no output

- [ ] **Step 5: Commit**

```bash
git add Chrome/content/main.js Chrome/content/ui.js Chrome/styles.css Chrome/tests/dual-mode.test.js
git commit -m "feat: add generic webpage mode to browser extension"
```

## Task 4: Update Documentation and Run Manual Browser Verification

**Files:**
- Modify: `Chrome/README.md`
- Test: manual browser verification on one ordinary webpage and one supported AI webpage

- [ ] **Step 1: Update README**

Replace the opening summary and usage section in `Chrome/README.md` with content that explicitly describes dual mode:

```md
这是一个与 `personal-knowledge-base` 配套使用的浏览器插件。它现在支持两种运行模式：

- **普通网页模式**：在任意 `http/https` 网页中显示悬浮面板，用户选中文字后可直接保存到知识库
- **平台增强模式**：在 ChatGPT、Gemini、Kimi、通义千问、豆包等页面中额外提供问题导航、搜索与跳转能力

## 使用说明

- 在普通网页中，插件会显示简化面板，只保留知识摘录能力
- 在已支持 AI 平台中，插件会显示完整导航面板，同时保留知识摘录能力
- 面板可拖动，拖到左右边缘后会自动吸附隐藏
```

- [ ] **Step 2: Reload the extension**

Run this manual flow:

```text
1. 打开 chrome://extensions/
2. 找到当前插件
3. 点击“重新加载”
```

Expected: 插件重新加载成功，没有 manifest 报错。

- [ ] **Step 3: Verify ordinary webpage mode**

Run this manual flow:

```text
1. 打开 https://example.com 或任一普通文章/文档网页
2. 确认右侧出现插件面板
3. 拖动面板到左/右边缘，确认自动吸附隐藏
4. 在页面中选中一段文字
5. 确认面板显示“保存选中文本”和选区预览
6. 点击保存，确认知识库接口返回成功
```

Expected:

- 不显示顶部/底部跳转按钮
- 不显示搜索框和导航列表
- 保存链路正常

- [ ] **Step 4: Verify supported AI webpage mode**

Run this manual flow:

```text
1. 打开 https://chatgpt.com 或另一个已支持平台
2. 确认插件面板仍然出现
3. 确认顶部/底部跳转、搜索框、问题列表仍然存在
4. 测试问题点击跳转
5. 再选中一段文字并执行保存
```

Expected:

- 原有导航能力不回退
- 知识保存能力继续可用

- [ ] **Step 5: Commit**

```bash
git add Chrome/README.md
git commit -m "docs: describe browser extension dual-mode behavior"
```

## Self-Review

- **Spec coverage:** Task 1 covers模式判定；Task 2 covers全网页注入范围；Task 3 covers普通网页 UI、导航能力 gating、普通网页 source metadata；Task 4 covers README 与双模式手工验收。
- **Placeholder scan:** 计划中没有 `TODO`、`TBD`、`similar to task N` 或“自行处理”的空洞表述。
- **Type consistency:** 统一使用 `pageMode`、`platformKey`、`platformName`、`sourcePlatform`、`themeClass`、`getPanelSectionState` 这些名字，避免实现时前后不一致。
