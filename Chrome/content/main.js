(function () {
  'use strict';

  if (window.__jumpAIInitialized) {
    return;
  }
  window.__jumpAIInitialized = true;

  const PKB_CHROME_VERSION = 'minimal-save-v2';

  const { PLATFORM_CONFIG, detectPlatform } = globalThis.JumpAIPlatforms;
  const {
    scrollPageTo,
    getQuestions,
    getQuestionText,
    createNavigationController,
  } = globalThis.JumpAINavigation;
  const {
    DEFAULT_KNOWLEDGE_CAPTURE_API,
    loadKnowledgeCaptureApi,
    loadPanelPosition,
    persistPanelPosition,
  } = globalThis.JumpAIStorage;
  const {
    getCurrentSelectionText,
    buildSelectionMeta,
    getCaptureDraft,
    createCaptureController,
  } = globalThis.JumpAICapture;
  const {
    updatePanelPosition: applyPanelPosition,
    updateDockHoverTrigger,
    createPanelShell,
    refreshCaptureEntry: renderCaptureEntry,
    setSaveStatus: renderSaveStatus,
    createPanelInteractionController,
  } = globalThis.JumpAIUI;

  const SAVE_REQUEST_TIMEOUT_MS = 12000;
  const PANEL_DOCK_SNAP_THRESHOLD = 36;
  const PANEL_DOCK_VISIBLE_STRIP = 0;
  const PANEL_DOCK_TRIGGER_WIDTH = 14;

  let currentPlatform = null;
  let navPanel = null;
  let jumpTopBtn = null;
  let jumpBottomBtn = null;
  let saveEntry = null;
  let saveStatus = null;
  let dragHandle = null;
  let searchInput = null;
  let scrollContainer = null;
  let tooltip = null;
  let dockHoverTrigger = null;

  let selectedText = '';
  let selectionMeta = null;
  let knowledgeCaptureApiUrl = DEFAULT_KNOWLEDGE_CAPTURE_API;

  let isDragging = false;
  let dragStartX = 0;
  let dragStartY = 0;
  let panelStartPosition = { x: 0, y: 0 };
  let panelPosition = { x: 0, y: 96 };
  let dockedSide = null;
  let isDockExpanded = false;

  let captureController = null;
  let panelInteractionController = null;
  let navigationController = null;
  let saveStatusTimer = null;
  let currentActiveIndex = -1;
  let lastQuestionCount = 0;
  let currentSearchTerm = '';

  function getCurrentPlatformName() {
    return PLATFORM_CONFIG[currentPlatform]?.name || '未知平台';
  }

  function updatePanelPosition() {
    applyPanelPosition(navPanel, panelPosition, {
      dockedSide,
      isExpanded: isDockExpanded || isDragging,
      visibleStrip: PANEL_DOCK_VISIBLE_STRIP,
    });
    updateDockHoverTrigger(dockHoverTrigger, navPanel, panelPosition, {
      dockedSide,
      isExpanded: isDockExpanded || isDragging,
      triggerWidth: PANEL_DOCK_TRIGGER_WIDTH,
    });
  }

  function clampPanelPosition(position) {
    const width = navPanel?.offsetWidth || 240;
    const height = navPanel?.offsetHeight || 240;
    return {
        x: Math.max(12, Math.min(window.innerWidth - width - 12, position.x)),
        y: Math.max(12, Math.min(window.innerHeight - height - 12, position.y)),
    };
  }

  function setDockedSide(nextSide) {
    dockedSide = nextSide;
    if (!nextSide) {
      isDockExpanded = false;
    }
  }

  function clearDockedState() {
    setDockedSide(null);
    updatePanelPosition();
  }

  function finalizeDocking() {
    const width = navPanel?.offsetWidth || 240;
    const clamped = clampPanelPosition(panelPosition);
    const nearLeft = clamped.x <= PANEL_DOCK_SNAP_THRESHOLD;
    const nearRight = clamped.x >= window.innerWidth - width - PANEL_DOCK_SNAP_THRESHOLD;

    panelPosition = clamped;
    if (nearLeft) {
      setDockedSide('left');
      panelPosition.x = 12;
    } else if (nearRight) {
      setDockedSide('right');
      panelPosition.x = window.innerWidth - width - 12;
    } else {
      setDockedSide(null);
    }
    updatePanelPosition();
  }

  function ensurePanelVisible(persist = false) {
    panelPosition = clampPanelPosition(panelPosition);
    if (dockedSide === 'right') {
      const width = navPanel?.offsetWidth || 240;
      panelPosition.x = window.innerWidth - width - 12;
    } else if (dockedSide === 'left') {
      panelPosition.x = 12;
    }
    updatePanelPosition();
    if (persist) {
      persistPanelPosition({ ...panelPosition, dockedSide }).catch(() => {});
    }
  }

  function refreshCaptureEntry() {
    renderCaptureEntry(saveEntry, selectedText);
  }

  function setSaveStatus(message, tone = 'neutral') {
    if (saveStatusTimer) {
      clearTimeout(saveStatusTimer);
      saveStatusTimer = null;
    }
    renderSaveStatus(saveStatus, message, tone);
    if (message) {
      saveStatusTimer = setTimeout(() => {
        renderSaveStatus(saveStatus, '', 'neutral');
      }, tone === 'success' ? 2600 : 4200);
    }
  }

  function buildCurrentSelectionMeta() {
    if (!selectedText) return null;
    return buildSelectionMeta(selectedText, currentPlatform, getCurrentPlatformName(), location.href);
  }

  function getCurrentCaptureDraft() {
    return getCaptureDraft(selectedText, knowledgeCaptureApiUrl);
  }

  function clearSelectedCaptureState() {
    captureController?.clearSelectedCaptureState();
  }

  function updateSelectionState() {
    captureController?.updateSelectionState();
  }

  async function handleSaveToKnowledgeBase() {
    await captureController?.handleSaveToKnowledgeBase();
  }

  function createPanel() {
    if (navPanel) return;

    const platform = PLATFORM_CONFIG[currentPlatform];
    ({
      panel: navPanel,
      jumpTopBtn,
      jumpBottomBtn,
      searchInput,
      scrollContainer,
      saveEntry,
      saveStatus,
      dragHandle,
      tooltip,
      dockHoverTrigger,
    } = createPanelShell(platform?.themeClass || ''));

    document.body.appendChild(navPanel);

    ['mousedown', 'mouseup', 'click', 'dblclick', 'pointerdown', 'pointerup'].forEach((eventName) => {
      navPanel.addEventListener(eventName, (event) => {
        event.stopPropagation();
      });
    });

    captureController = createCaptureController({
      readCurrentSelectionText: getCurrentSelectionText,
      getPanel: () => navPanel,
      getSelectedText: () => selectedText,
      setSelectedText: (value) => { selectedText = value; },
      buildSelectionMeta: buildCurrentSelectionMeta,
      getSelectionMeta: () => selectionMeta,
      setSelectionMeta: (value) => { selectionMeta = value; },
      getCurrentPanelMode: () => 'nav',
      setPanelMode: () => {},
      refreshCaptureEntry,
      getCaptureDraft: getCurrentCaptureDraft,
      setSaveStatus,
      persistKnowledgeCaptureApi: async () => {},
      getSaveRequestTimeoutMs: () => SAVE_REQUEST_TIMEOUT_MS,
      onSaved: () => {
        setTimeout(() => {
          ensurePanelVisible(true);
        }, 120);
      },
    });

    panelInteractionController = createPanelInteractionController({
      getPanel: () => navPanel,
      getDragHandle: () => dragHandle,
      getIsDragging: () => isDragging,
      setDragging: (value) => { isDragging = value; },
      getDragStartX: () => dragStartX,
      setDragStartX: (value) => { dragStartX = value; },
      getDragStartY: () => dragStartY,
      setDragStartY: (value) => { dragStartY = value; },
      getPanelStartPosition: () => panelStartPosition,
      setPanelStartPosition: (value) => { panelStartPosition = value; },
      getPanelPosition: () => panelPosition,
      setPanelPosition: (value) => { panelPosition = value; },
      updatePanelPosition,
      persistPanelPosition: (value) => persistPanelPosition({ ...value, dockedSide }),
      clearDockedState,
      finalizeDocking,
    });

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

    function triggerDirectSave(event) {
      event?.preventDefault?.();
      event?.stopPropagation?.();
      if (!selectedText) {
        setSaveStatus('请先选中要保存的文本', 'error');
        return;
      }
      console.info('[PKB Chrome] 直接保存选中文本', {
        selected_length: selectedText.length,
      });
      handleSaveToKnowledgeBase();
    }

    saveEntry.addEventListener('pointerdown', triggerDirectSave);
    saveEntry.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
    });

    panelInteractionController.setupDrag();
    navPanel.addEventListener('mouseenter', () => {
      if (!dockedSide || isDragging) return;
      isDockExpanded = true;
      updatePanelPosition();
    });
    navPanel.addEventListener('mouseleave', () => {
      if (!dockedSide || isDragging) return;
      isDockExpanded = false;
      updatePanelPosition();
    });

    dockHoverTrigger.addEventListener('mouseenter', () => {
      if (!dockedSide || isDragging) return;
      isDockExpanded = true;
      updatePanelPosition();
    });

    panelPosition = clampPanelPosition({
      x: Math.max(12, window.innerWidth - 252),
      y: Math.max(24, Math.round(window.innerHeight * 0.16)),
    });
    updatePanelPosition();
    navigationController.rebuildNavigation(getQuestions(currentPlatform, PLATFORM_CONFIG), false);
    navigationController.setupScrollObserver();
    setTimeout(() => ensurePanelVisible(true), 200);
  }

  async function init() {
    currentPlatform = detectPlatform();
    if (!currentPlatform) {
      console.log(`[PKB Chrome ${PKB_CHROME_VERSION}] 未识别的平台`);
      return;
    }

    console.log(`[PKB Chrome ${PKB_CHROME_VERSION}] 已加载: ${PLATFORM_CONFIG[currentPlatform].name}`);

    createPanel();
    knowledgeCaptureApiUrl = await loadKnowledgeCaptureApi();

    const savedPanelPosition = await loadPanelPosition();
    if (savedPanelPosition) {
      dockedSide = savedPanelPosition.dockedSide || null;
      panelPosition = clampPanelPosition(savedPanelPosition);
      updatePanelPosition();
    }

    document.addEventListener('selectionchange', updateSelectionState);
    document.addEventListener('mouseup', () => setTimeout(updateSelectionState, 0));
    document.addEventListener('keydown', (event) => navigationController?.handleKeyboardShortcut?.(event));

    window.addEventListener('resize', () => ensurePanelVisible(true));
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        ensurePanelVisible(false);
        navigationController?.checkForNewMessages?.();
      }
    });

    window.setInterval(() => {
      navigationController?.checkForNewMessages?.();
    }, 1500);

    updateSelectionState();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(init, 300));
  } else {
    setTimeout(init, 300);
  }
})();
