const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const { detectPlatform, resolvePageContext } = require('../content/platforms.js');
const { getPanelSectionState } = require('../content/ui.js');

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

test('manifest injects content scripts into general http and https pages', () => {
  const manifest = JSON.parse(
    fs.readFileSync(path.join(__dirname, '..', 'manifest.json'), 'utf8'),
  );

  const matches = manifest.content_scripts[0].matches;
  assert.ok(matches.includes('http://*/*'));
  assert.ok(matches.includes('https://*/*'));
});

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
