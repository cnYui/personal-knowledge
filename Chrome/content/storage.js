(function () {
  'use strict';

  const DEFAULT_KNOWLEDGE_CAPTURE_API = 'http://127.0.0.1:8000/api/memories/clip';
  const FALLBACK_KNOWLEDGE_CAPTURE_APIS = [
    'http://localhost:8000/api/memories/clip',
    'http://127.0.0.1:8002/api/memories/clip',
    'http://localhost:8002/api/memories/clip',
  ];
  const KNOWLEDGE_CAPTURE_API_STORAGE_KEY = 'jumpai_knowledge_capture_api';
  const PANEL_POSITION_STORAGE_KEY = 'jumpai_panel_position';

  function getStorageApi() {
    return typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local ? chrome.storage.local : null;
  }

  async function loadKnowledgeCaptureApi() {
    const storageApi = getStorageApi();
    if (storageApi) {
      try {
        const result = await storageApi.get([KNOWLEDGE_CAPTURE_API_STORAGE_KEY]);
        return result[KNOWLEDGE_CAPTURE_API_STORAGE_KEY] || DEFAULT_KNOWLEDGE_CAPTURE_API;
      } catch (error) {
        console.warn('[JumpAI] 读取扩展存储失败，回退到默认接口地址。', error);
      }
    }

    try {
      return localStorage.getItem(KNOWLEDGE_CAPTURE_API_STORAGE_KEY) || DEFAULT_KNOWLEDGE_CAPTURE_API;
    } catch (error) {
      console.warn('[JumpAI] 读取本地存储失败，回退到默认接口地址。', error);
      return DEFAULT_KNOWLEDGE_CAPTURE_API;
    }
  }

  async function persistKnowledgeCaptureApi(value) {
    const storageApi = getStorageApi();
    if (storageApi) {
      await storageApi.set({ [KNOWLEDGE_CAPTURE_API_STORAGE_KEY]: value });
      return;
    }
    localStorage.setItem(KNOWLEDGE_CAPTURE_API_STORAGE_KEY, value);
  }

  function normalizeKnowledgeCaptureApi(value) {
    const normalized = (value || '').trim();
    return normalized || DEFAULT_KNOWLEDGE_CAPTURE_API;
  }

  function buildKnowledgeCaptureApiCandidates(value) {
    const normalized = normalizeKnowledgeCaptureApi(value);
    return [normalized, DEFAULT_KNOWLEDGE_CAPTURE_API, ...FALLBACK_KNOWLEDGE_CAPTURE_APIS].filter((item, index, list) => {
      return !!item && list.indexOf(item) === index;
    });
  }

  function normalizePanelPosition(value) {
    if (!value || typeof value !== 'object') return null;
    const x = Number(value.x);
    const y = Number(value.y);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
    const dockedSide = value.dockedSide === 'left' || value.dockedSide === 'right' ? value.dockedSide : null;
    return { x, y, dockedSide };
  }

  async function loadPanelPosition() {
    const storageApi = getStorageApi();
    if (storageApi) {
      try {
        const result = await storageApi.get([PANEL_POSITION_STORAGE_KEY]);
        return normalizePanelPosition(result[PANEL_POSITION_STORAGE_KEY]);
      } catch (error) {
        console.warn('[JumpAI] 读取面板位置失败。', error);
      }
    }

    try {
      const raw = localStorage.getItem(PANEL_POSITION_STORAGE_KEY);
      return normalizePanelPosition(raw ? JSON.parse(raw) : null);
    } catch (error) {
      console.warn('[JumpAI] 读取本地面板位置失败。', error);
      return null;
    }
  }

  async function persistPanelPosition(value) {
    const normalized = normalizePanelPosition(value);
    if (!normalized) return;

    const storageApi = getStorageApi();
    if (storageApi) {
      await storageApi.set({ [PANEL_POSITION_STORAGE_KEY]: normalized });
      return;
    }

    localStorage.setItem(PANEL_POSITION_STORAGE_KEY, JSON.stringify(normalized));
  }

  globalThis.JumpAIStorage = {
    DEFAULT_KNOWLEDGE_CAPTURE_API,
    loadKnowledgeCaptureApi,
    persistKnowledgeCaptureApi,
    normalizeKnowledgeCaptureApi,
    buildKnowledgeCaptureApiCandidates,
    loadPanelPosition,
    persistPanelPosition,
  };
})();
