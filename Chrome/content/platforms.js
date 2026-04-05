(function () {
  'use strict';

  const PLATFORM_CONFIG = {
    chatgpt: {
      name: 'ChatGPT',
      hostPatterns: ['chat.openai.com', 'chatgpt.com'],
      selectors: [
        '[data-message-author-role="user"]',
        '.text-base[data-message-author-role="user"]',
        '[class*="agent-turn"] [data-message-author-role="user"]',
      ],
      themeClass: 'chatgpt-theme',
      getTextContent: (el) => {
        const img = el.querySelector('img');
        if (img && !el.innerText?.trim()) return '[图片]';
        const textEl = el.querySelector('.whitespace-pre-wrap') || el;
        return textEl.innerText || textEl.textContent || '';
      },
    },
    gemini: {
      name: 'Gemini',
      hostPatterns: ['gemini.google.com'],
      selectors: [
        '.user-query-bubble-with-background',
        '[data-message-author="user"]',
        '.query-content',
      ],
      themeClass: 'gemini-theme',
      filterElement: (el) => !el.closest('button, a, [role="button"]'),
      getTextContent: (el) => {
        const img = el.querySelector('img');
        if (img && !el.innerText?.trim()) return '[图片]';
        let text = el.innerText || el.textContent || '';
        text = text
          .replace(/^(You said|You said:|你说了|你说)\s*/i, '')
          .replace(/^\s*了(?=[\u4e00-\u9fa5A-Za-z0-9])/u, '');
        return text;
      },
    },
    kimi: {
      name: 'Kimi',
      hostPatterns: ['kimi.moonshot.cn', 'kimi.com', 'www.kimi.com'],
      selectors: ['.user-content'],
      themeClass: 'kimi-theme',
      getTextContent: (el) => {
        const img = el.querySelector('img');
        if (img && !el.innerText?.trim()) return '[图片]';
        return el.innerText || el.textContent || '';
      },
    },
    qianwen: {
      name: '通义千问',
      hostPatterns: ['tongyi.aliyun.com', 'qianwen.aliyun.com', 'qianwen.com', 'www.qianwen.com'],
      selectors: [
        '[class*="bubble"][class*="right"]',
        '[class*="message-right"]',
        '[class*="self-message"]',
        '[class*="user-msg"]',
        '[class*="chatItem"][class*="user"]',
        '[class*="userMessage"]',
        '[data-role="user"]',
        '.chat-item-user',
        '[class*="questionItem"]',
        '[class*="human"]',
      ],
      themeClass: 'qianwen-theme',
      filterElement: (el) => !el.closest('button, a, [role="button"]'),
      getTextContent: (el) => {
        const img = el.querySelector('img');
        if (img && !el.innerText?.trim()) return '[图片]';
        let text = el.innerText || el.textContent || '';
        text = text.replace(/^\s*了(?=[\u4e00-\u9fa5A-Za-z0-9])/u, '');
        return text;
      },
    },
    doubao: {
      name: '豆包',
      hostPatterns: ['doubao.com', 'www.doubao.com'],
      selectors: [
        '[data-testid="send_message_container"]',
        '[data-testid="message_text_content"]:not(.flow-markdown-body):not([class*="markdown"])',
      ],
      themeClass: 'doubao-theme',
      filterElement: (el) => !el.closest('button, a, [role="button"]'),
      getTextContent: (el) => {
        const img = el.querySelector('img');
        if (img) {
          const text = el.innerText?.trim();
          return text ? text.substring(0, 12) : '[图片]';
        }
        let text = el.innerText || el.textContent || '';
        text = text.replace(/^\s*了(?=[\u4e00-\u9fa5A-Za-z0-9])/u, '');
        return text;
      },
    },
  };

  const INPUT_SELECTORS = {
    chatgpt: ['#prompt-textarea', 'textarea[data-id="root"]', 'form textarea'],
    gemini: ['rich-textarea', '.ql-editor', '[contenteditable="true"]'],
    kimi: ['[class*="editor"]', '[contenteditable="true"]', 'textarea'],
    qianwen: ['textarea', '[contenteditable="true"]', '[class*="input"]'],
    doubao: ['[data-testid="chat_input_input"]', 'textarea', '[contenteditable="true"]'],
  };

  function detectPlatform(hostname = window.location.hostname) {
    for (const [key, config] of Object.entries(PLATFORM_CONFIG)) {
      if (config.hostPatterns.some((pattern) => hostname.includes(pattern))) {
        return key;
      }
    }
    return null;
  }

  function getCurrentPlatformName(platformKey) {
    return PLATFORM_CONFIG[platformKey]?.name || '未知平台';
  }

  globalThis.JumpAIPlatforms = {
    PLATFORM_CONFIG,
    INPUT_SELECTORS,
    detectPlatform,
    getCurrentPlatformName,
  };
})();
