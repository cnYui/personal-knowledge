，(function () {
  'use strict';

  function updatePanelPosition(panel, panelPosition, dockState = {}) {
    if (!panel) return;
    const visibleStrip = dockState.visibleStrip || 0;
    const panelWidth = panel.offsetWidth || 240;
    const dockedSide = dockState.dockedSide || null;
    const isExpanded = !!dockState.isExpanded;
    let left = panelPosition.x;

    panel.classList.toggle('is-docked', !!dockedSide);
    panel.classList.toggle('is-docked-left', dockedSide === 'left');
    panel.classList.toggle('is-docked-right', dockedSide === 'right');
    panel.classList.toggle('is-dock-expanded', isExpanded);

    if (dockedSide === 'left') {
      left = isExpanded ? 12 : -(panelWidth - visibleStrip);
    } else if (dockedSide === 'right') {
      left = isExpanded ? window.innerWidth - panelWidth - 12 : window.innerWidth - visibleStrip;
    }

    panel.style.left = `${left}px`;
    panel.style.top = `${panelPosition.y}px`;
  }

  function updateDockHoverTrigger(trigger, panel, panelPosition, dockState = {}) {
    if (!trigger) return;

    const dockedSide = dockState.dockedSide || null;
    const isExpanded = !!dockState.isExpanded;
    const triggerWidth = dockState.triggerWidth || 14;
    const panelHeight = panel?.offsetHeight || 240;

    if (!dockedSide || isExpanded) {
      trigger.style.display = 'none';
      return;
    }

    trigger.style.display = 'block';
    trigger.style.top = `${panelPosition.y}px`;
    trigger.style.height = `${panelHeight}px`;
    trigger.style.left = dockedSide === 'left' ? '0px' : `${window.innerWidth - triggerWidth}px`;
  }

  function createPanelShell(themeClass = '') {
    const panel = document.createElement('div');
    panel.id = 'ai-nav-panel';
    panel.className = themeClass.trim();
    panel.dataset.pkbChromeVersion = 'minimal-save-v2';

    const header = document.createElement('div');
    header.id = 'ai-nav-header';

    const dragHandle = document.createElement('button');
    dragHandle.id = 'ai-nav-drag-handle';
    dragHandle.type = 'button';
    dragHandle.innerHTML = '⋮⋮';
    dragHandle.title = '拖动移动面板';
    header.appendChild(dragHandle);

    const title = document.createElement('span');
    title.id = 'ai-nav-title';
    title.textContent = '个人知识库';
    header.appendChild(title);
    panel.appendChild(header);

    const jumpBtns = document.createElement('div');
    jumpBtns.id = 'ai-nav-jump-btns';
    const jumpTopBtn = document.createElement('button');
    jumpTopBtn.className = 'ai-nav-jump-btn';
    jumpTopBtn.type = 'button';
    jumpTopBtn.innerHTML = '↑ 顶部';
    const jumpBottomBtn = document.createElement('button');
    jumpBottomBtn.className = 'ai-nav-jump-btn';
    jumpBottomBtn.type = 'button';
    jumpBottomBtn.innerHTML = '↓ 底部';
    jumpBtns.appendChild(jumpTopBtn);
    jumpBtns.appendChild(jumpBottomBtn);
    panel.appendChild(jumpBtns);

    const searchWrapper = document.createElement('div');
    searchWrapper.id = 'ai-nav-search-wrapper';
    const searchInput = document.createElement('input');
    searchInput.id = 'ai-nav-search';
    searchInput.type = 'search';
    searchInput.placeholder = '搜索当前消息...';
    searchWrapper.appendChild(searchInput);
    panel.appendChild(searchWrapper);

    const scrollContainer = document.createElement('div');
    scrollContainer.id = 'ai-nav-scroll';
    panel.appendChild(scrollContainer);

    const saveEntry = document.createElement('button');
    saveEntry.id = 'ai-nav-capture-entry';
    saveEntry.type = 'button';
    saveEntry.style.display = 'none';
    saveEntry.innerHTML = `
      <span class="ai-nav-capture-label">保存选中文本</span>
      <span class="ai-nav-capture-preview"></span>
    `;
    panel.appendChild(saveEntry);

    const saveStatus = document.createElement('div');
    saveStatus.id = 'ai-nav-save-status';
    saveStatus.style.display = 'none';
    panel.appendChild(saveStatus);

    const tooltip = document.createElement('div');
    tooltip.id = 'ai-nav-tooltip';
    document.body.appendChild(tooltip);

    const dockHoverTrigger = document.createElement('div');
    dockHoverTrigger.id = 'ai-nav-dock-trigger';
    document.body.appendChild(dockHoverTrigger);

    return {
      panel,
      jumpTopBtn,
      jumpBottomBtn,
      searchInput,
      scrollContainer,
      saveEntry,
      saveStatus,
      dragHandle,
      tooltip,
      dockHoverTrigger,
    };
  }

  function refreshCaptureEntry(saveEntry, selectedText) {
    if (!saveEntry) return;
    const shouldShow = !!selectedText;
    saveEntry.style.display = shouldShow ? 'flex' : 'none';
    if (!shouldShow) return;
    const textEl = saveEntry.querySelector('.ai-nav-capture-preview');
    if (!textEl) return;
    const preview = selectedText.length > 72 ? `${selectedText.slice(0, 72)}...` : selectedText;
    textEl.textContent = preview;
  }

  function setSaveStatus(saveStatus, message, tone = 'neutral') {
    if (!saveStatus) return;
    saveStatus.textContent = message;
    saveStatus.dataset.tone = tone;
    saveStatus.style.display = message ? 'block' : 'none';
  }

  function createPanelInteractionController(deps) {
    function setupDrag() {
      const panel = deps.getPanel();
      const handle = deps.getDragHandle();
      if (!panel || !handle) return;

      let activePointerId = null;

      const handlePointerMove = (event) => {
        if (!deps.getIsDragging() || event.pointerId !== activePointerId) return;
        const rect = panel.getBoundingClientRect();
        const deltaX = event.clientX - deps.getDragStartX();
        const deltaY = event.clientY - deps.getDragStartY();
        const nextX = Math.max(12, Math.min(window.innerWidth - rect.width - 12, deps.getPanelStartPosition().x + deltaX));
        const nextY = Math.max(12, Math.min(window.innerHeight - rect.height - 12, deps.getPanelStartPosition().y + deltaY));
        deps.setPanelPosition({ x: nextX, y: nextY });
        deps.updatePanelPosition();
        event.preventDefault();
      };

      const cleanupDragListeners = () => {
        window.removeEventListener('pointermove', handlePointerMove, true);
        window.removeEventListener('pointerup', stopDrag, true);
        window.removeEventListener('pointercancel', stopDrag, true);
        window.removeEventListener('blur', stopDrag);
      };

      const stopDrag = (event) => {
        if (event?.pointerId != null && activePointerId != null && event.pointerId !== activePointerId) return;
        if (!deps.getIsDragging()) return;
        deps.setDragging(false);
        panel.classList.remove('dragging');
        cleanupDragListeners();
        activePointerId = null;
        deps.finalizeDocking?.();
        deps.persistPanelPosition?.(deps.getPanelPosition());
      };

      handle.addEventListener('pointerdown', (event) => {
        activePointerId = event.pointerId;
        const rect = panel.getBoundingClientRect();
        deps.clearDockedState?.();
        deps.setDragging(true);
        deps.setDragStartX(event.clientX);
        deps.setDragStartY(event.clientY);
        deps.setPanelStartPosition({ x: rect.left, y: rect.top });
        panel.classList.add('dragging');
        window.addEventListener('pointermove', handlePointerMove, true);
        window.addEventListener('pointerup', stopDrag, true);
        window.addEventListener('pointercancel', stopDrag, true);
        window.addEventListener('blur', stopDrag);
        event.preventDefault();
        event.stopPropagation();
      });
    }

    return {
      setupDrag,
    };
  }

  globalThis.JumpAIUI = {
    updatePanelPosition,
    updateDockHoverTrigger,
    createPanelShell,
    refreshCaptureEntry,
    setSaveStatus,
    createPanelInteractionController,
  };
})();
