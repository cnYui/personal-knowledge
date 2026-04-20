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
