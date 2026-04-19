(function () {
  'use strict';

  function getNodeOwnerElement(node) {
    if (!node) return null;
    if (node.nodeType === Node.ELEMENT_NODE) return node;
    return node.parentElement || null;
  }

  function isInsidePanel(node, panel) {
    const element = getNodeOwnerElement(node);
    return !!(element && panel && panel.contains(element));
  }

  function getCurrentSelectionText(panel) {
    const selection = window.getSelection();
    if (!selection) return '';
    if (selection.rangeCount === 0) return '';
    if (selection.isCollapsed) return '';

    const activeElement = document.activeElement;
    if (activeElement && isInsidePanel(activeElement, panel)) {
      return '';
    }
    if (isInsidePanel(selection.anchorNode, panel) || isInsidePanel(selection.focusNode, panel)) {
      return '';
    }

    try {
      const range = selection.getRangeAt(0);
      if (isInsidePanel(range.commonAncestorContainer, panel)) {
        return '';
      }
    } catch (error) {
      console.warn('[JumpAI] 读取选区范围失败。', error);
    }

    return (selection.toString() || '').replace(/\s+/g, ' ').trim();
  }

  function buildSelectionMeta(selectedText, currentPlatform, platformName, url) {
    if (!selectedText) return null;
    return {
      platform: currentPlatform,
      platformName,
      url,
    };
  }

  function getCaptureDraft(selectedText, apiUrl) {
    const normalized = (selectedText || '').replace(/\s+/g, ' ').trim();
    if (!normalized) return null;

    return {
      title: '',
      content: normalized,
      apiUrl,
    };
  }

  function buildCaptureRequestPayload(draft, selectionMeta) {
    if (!draft || !selectionMeta) return null;

    return {
      title: draft.title,
      content: draft.content,
      source_platform: selectionMeta.platform,
      source_url: selectionMeta.url,
      source_type: 'browser_clip',
    };
  }

  function clearBrowserSelection() {
    try {
      const selection = window.getSelection();
      if (selection) {
        selection.removeAllRanges();
      }
    } catch (error) {
      console.warn('[JumpAI] 清理浏览器选区失败。', error);
    }
  }

  function createCaptureController(deps) {
    async function sendPayload(apiUrl, payload) {
      let timeoutId = null;
      const controller = new AbortController();

      try {
        console.info('[PKB Chrome] 开始发送摘录到知识库', {
          apiUrl,
          title: payload?.title,
          source_platform: payload?.source_platform,
          content_length: payload?.content?.length || 0,
        });
        timeoutId = setTimeout(() => controller.abort(), deps.getSaveRequestTimeoutMs());
        const response = await fetch(apiUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: controller.signal,
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errorText = await response.text();
          console.error('[PKB Chrome] 保存摘录请求失败', {
            apiUrl,
            status: response.status,
            statusText: response.statusText,
            body: errorText,
          });
          const error = new Error(errorText || `保存失败 (${response.status})`);
          error.status = response.status;
          error.apiUrl = apiUrl;
          throw error;
        }

        const data = await response.json();
        console.info('[PKB Chrome] 摘录保存成功', {
          id: data?.id,
          title: data?.title,
        });
        return data;
      } finally {
        if (timeoutId) {
          clearTimeout(timeoutId);
        }
      }
    }

    function clearSelectedCaptureState() {
      deps.setSelectedText('');
      deps.setSelectionMeta(null);
      clearBrowserSelection();
      deps.refreshCaptureEntry();
    }

    function updateSelectionState() {
      const panel = deps.getPanel();
      const text = deps.readCurrentSelectionText(deps.getPanel());
      const activeElement = document.activeElement;
      const panelHasFocus = !!(panel && activeElement && panel.contains(activeElement));

      if (!text && panelHasFocus && deps.getSelectedText()) {
        console.info('[PKB Chrome] 面板获得焦点，保留当前页面选区摘要', {
          currentPanelMode: deps.getCurrentPanelMode(),
          selected_length: deps.getSelectedText()?.length || 0,
        });
        return;
      }

      if (text === deps.getSelectedText()) return;
      deps.setSelectedText(text);
      deps.setSelectionMeta(deps.buildSelectionMeta());
      if (deps.getCurrentPanelMode() === 'save' && !text && !panelHasFocus) {
        deps.setPanelMode('nav');
      }
      deps.refreshCaptureEntry();
    }

    async function handleSaveToKnowledgeBase() {
      if (!deps.getSelectionMeta()) {
        console.warn('[PKB Chrome] 当前没有选区元数据，无法保存');
        deps.setSaveStatus('请先在页面中选中要保存的内容', 'error');
        return;
      }

      const draft = deps.getCaptureDraft();
      if (!draft) {
        console.warn('[PKB Chrome] 未能构造保存草稿');
        deps.setSaveStatus('请先选中要保存的文本', 'error');
        return;
      }
      const payload = buildCaptureRequestPayload(draft, deps.getSelectionMeta());

      if (!draft.content) {
        console.warn('[PKB Chrome] 正文为空，停止保存', {
          hasContent: !!draft.content,
        });
        deps.setSaveStatus('正文不能为空', 'error');
        return;
      }
      if (!payload) {
        console.warn('[PKB Chrome] 构造保存请求体失败');
        deps.setSaveStatus('当前没有可保存的摘录内容', 'error');
        return;
      }

      deps.setSaveStatus('正在保存到记忆管理...', 'neutral');

      try {
        const apiCandidates = deps.getKnowledgeCaptureApiCandidates(draft.apiUrl);
        let saved = null;
        let lastError = null;
        let activeApiUrl = draft.apiUrl;

        for (const apiUrl of apiCandidates) {
          try {
            saved = await sendPayload(apiUrl, payload);
            activeApiUrl = apiUrl;
            break;
          } catch (error) {
            lastError = error;
            const isAbort = error?.name === 'AbortError';
            const isNetworkError = error?.message === 'Failed to fetch';
            const isNotFound = error?.status === 404;
            if (!(isAbort || isNetworkError || isNotFound)) {
              throw error;
            }
          }
        }

        if (!saved) {
          throw lastError || new Error('请检查个人知识库服务是否已启动');
        }

        await deps.persistKnowledgeCaptureApi(activeApiUrl);
        deps.setSaveStatus(`已保存：${saved?.title || draft.title}`, 'success');
        clearSelectedCaptureState();
        deps.onSaved?.(saved);
      } catch (error) {
        if (error.name === 'AbortError') {
          console.error('[PKB Chrome] 保存摘录超时');
          deps.setSaveStatus('保存超时：请检查个人知识库服务是否已启动，或确认接口地址是否正确。', 'error');
          return;
        }
        const message = error && error.message ? error.message : '请检查个人知识库服务是否已启动';
        console.error('[PKB Chrome] 保存摘录异常', error);
        deps.setSaveStatus(`保存失败：${message}`, 'error');
      }
    }

    return {
      clearSelectedCaptureState,
      updateSelectionState,
      handleSaveToKnowledgeBase,
    };
  }

  globalThis.JumpAICapture = {
    getCurrentSelectionText,
    buildSelectionMeta,
    getCaptureDraft,
    buildCaptureRequestPayload,
    clearBrowserSelection,
    createCaptureController,
  };
})();
