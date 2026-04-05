(function () {
  'use strict';

  function scrollScrollableContainers(position) {
    const targetTop = position === 'top' ? 0 : Number.MAX_SAFE_INTEGER;
    const candidates = [document.scrollingElement, document.documentElement, document.body];
    document.querySelectorAll('main, section, article, div').forEach((node) => {
      if (node.id === 'ai-nav-panel' || node.id === 'ai-nav-scroll' || node.closest('#ai-nav-panel')) {
        return;
      }
      const canScroll = node.scrollHeight - node.clientHeight > 120;
      if (canScroll) {
        candidates.push(node);
      }
    });

    const seen = new Set();
    candidates.forEach((node) => {
      if (!node || seen.has(node)) return;
      seen.add(node);
      try {
        const top = position === 'top' ? 0 : node.scrollHeight;
        if (typeof node.scrollTo === 'function') {
          node.scrollTo({ top, behavior: 'smooth' });
        } else {
          node.scrollTop = top;
        }
      } catch (error) {
        console.warn('[JumpAI] 滚动容器失败。', error);
      }
    });
  }

  function scrollPageTo(questions, position) {
    scrollScrollableContainers(position);
    window.scrollTo({ top: position === 'top' ? 0 : document.documentElement.scrollHeight, behavior: 'smooth' });
    if (questions.length > 0) {
      const targetQuestion = position === 'top' ? questions[0] : questions[questions.length - 1];
      setTimeout(() => {
        targetQuestion.scrollIntoView({ behavior: 'smooth', block: position === 'top' ? 'start' : 'end' });
      }, 180);
      setTimeout(() => {
        scrollScrollableContainers(position);
        window.scrollTo({ top: position === 'top' ? 0 : document.documentElement.scrollHeight, behavior: 'auto' });
        targetQuestion.scrollIntoView({ behavior: 'auto', block: position === 'top' ? 'start' : 'end' });
      }, 520);
    } else {
      setTimeout(() => {
        scrollScrollableContainers(position);
        window.scrollTo({ top: position === 'top' ? 0 : document.documentElement.scrollHeight, behavior: 'auto' });
      }, 520);
    }
  }

  function getQuestions(currentPlatform, platformConfig) {
    const platform = platformConfig[currentPlatform];
    if (!platform) return [];

    for (const selector of platform.selectors) {
      let elements = Array.from(document.querySelectorAll(selector));
      if (typeof platform.filterElement === 'function') {
        elements = elements.filter((element) => {
          try {
            return platform.filterElement(element);
          } catch (error) {
            console.warn('[JumpAI] 过滤问题元素失败。', error);
            return true;
          }
        });
      }
      if (elements.length > 0) {
        return elements;
      }
    }
    return [];
  }

  function getQuestionText(questionElement, currentPlatform, platformConfig) {
    const platform = platformConfig[currentPlatform];
    let text = '';
    if (platform && platform.getTextContent) {
      text = platform.getTextContent(questionElement);
    } else {
      text = questionElement.innerText || questionElement.textContent || '';
    }
    return text.trim().replace(/\s+/g, ' ');
  }

  function getCleanText(element) {
    return element.innerText || element.textContent || '';
  }

  function getCleanAnswerText(questionEl) {
    try {
      let next = questionEl.nextElementSibling;
      if (next) {
        return getCleanText(next).trim().substring(0, 2000);
      }
      let parent = questionEl.parentElement;
      for (let i = 0; i < 5 && parent; i += 1) {
        next = parent.nextElementSibling;
        if (next && getCleanText(next).trim()) {
          return getCleanText(next).trim().substring(0, 2000);
        }
        parent = parent.parentElement;
      }
    } catch (error) {
      console.warn('[JumpAI] 提取回答文本失败。', error);
    }
    return '';
  }

  function getAnswerForQuestion(questionEl) {
    try {
      let next = questionEl.nextElementSibling;
      if (next) {
        return next.innerText?.trim().substring(0, 2000) || '';
      }

      let parent = questionEl.parentElement;
      for (let i = 0; i < 5 && parent; i += 1) {
        next = parent.nextElementSibling;
        if (next && next.innerText?.trim()) {
          return next.innerText.trim().substring(0, 2000);
        }
        parent = parent.parentElement;
      }
    } catch (error) {
      console.warn('[JumpAI] 提取问题对应回答失败。', error);
    }
    return '';
  }

  function createNavigationController(deps) {
    let intersectionObserver = null;

    function updateActiveState() {
      const scrollContainer = deps.getScrollContainer();
      if (!scrollContainer) return;
      const items = scrollContainer.querySelectorAll('.ai-nav-item');
      items.forEach((item) => {
        const index = parseInt(item.dataset.index, 10);
        if (index === deps.getCurrentActiveIndex()) {
          item.classList.add('active');
        } else {
          item.classList.remove('active');
        }
      });
    }

    function rebuildNavigation(questions, scrollToBottom = false) {
      const scrollContainer = deps.getScrollContainer();
      if (!scrollContainer) return;
      scrollContainer.innerHTML = '';

      if (questions.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'ai-nav-empty';
        empty.textContent = '暂无对话';
        scrollContainer.appendChild(empty);
        deps.setLastQuestionCount(0);
        return;
      }

      deps.setLastQuestionCount(questions.length);
      let visibleCount = 0;

      questions.forEach((question, index) => {
        const text = deps.getQuestionText(question);

        if (deps.getCurrentSearchTerm() && !text.toLowerCase().includes(deps.getCurrentSearchTerm())) {
          return;
        }

        visibleCount += 1;
        const displayText = text.length > 12 ? text.substring(0, 12) + '...' : text;

        const item = document.createElement('div');
        item.className = 'ai-nav-item';
        item.dataset.index = index;
        item.dataset.fullText = text;
        if (index === deps.getCurrentActiveIndex()) {
          item.classList.add('active');
        }

        const textSpan = document.createElement('span');
        textSpan.className = 'ai-nav-item-text';
        textSpan.textContent = displayText || `对话 ${index + 1}`;

        item.addEventListener('click', () => {
          deps.activateQuestion(index, question, intersectionObserver);
          updateActiveState();
        });

        item.appendChild(textSpan);

        item.addEventListener('mouseenter', () => deps.showTooltip(text, item));
        item.addEventListener('mouseleave', () => deps.hideTooltip());

        scrollContainer.appendChild(item);
      });

      if (visibleCount === 0 && deps.getCurrentSearchTerm()) {
        const empty = document.createElement('div');
        empty.className = 'ai-nav-empty';
        empty.textContent = '无匹配结果';
        scrollContainer.appendChild(empty);
      }

      const maxHeight = deps.getVisibleItems() * deps.getItemHeight();
      scrollContainer.style.maxHeight = `${maxHeight}px`;

      if (scrollToBottom) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }

    function setupScrollObserver() {
      const questions = deps.getQuestions();
      if (questions.length === 0) return;

      if (intersectionObserver) {
        intersectionObserver.disconnect();
      }

      let debounceTimer = null;
      intersectionObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            const currentQuestions = deps.getQuestions();
            const index = Array.from(currentQuestions).indexOf(entry.target);
            if (index === -1 || index === deps.getCurrentActiveIndex()) return;
            deps.setCurrentActiveIndex(index);
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
              updateActiveState();
              const scrollContainer = deps.getScrollContainer();
              const activeItem = scrollContainer?.querySelector('.ai-nav-item.active');
              if (activeItem) {
                activeItem.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
              }
            }, 100);
          });
        },
        { threshold: 0.3 },
      );

      questions.forEach((question) => intersectionObserver.observe(question));
    }

    function checkForNewMessages() {
      const questions = deps.getQuestions();
      const currentCount = questions.length;

      if (currentCount !== deps.getLastQuestionCount()) {
        rebuildNavigation(questions, currentCount > deps.getLastQuestionCount());
        setupScrollObserver();
      }
    }

    function handleKeyboardShortcut(event) {
      const navPanel = deps.getNavPanel();
      if (!navPanel) return;

      if (event.altKey && event.key === 'j') {
        event.preventDefault();
        navPanel.classList.toggle('is-hidden');
      }

      if (event.altKey && event.key === 'ArrowUp') {
        event.preventDefault();
        const questions = deps.getQuestions();
        if (questions.length > 0 && deps.getCurrentActiveIndex() > 0) {
          deps.setCurrentActiveIndex(deps.getCurrentActiveIndex() - 1);
          questions[deps.getCurrentActiveIndex()].scrollIntoView({ behavior: 'smooth', block: 'start' });
          updateActiveState();
        }
      }

      if (event.altKey && event.key === 'ArrowDown') {
        event.preventDefault();
        const questions = deps.getQuestions();
        if (questions.length > 0 && deps.getCurrentActiveIndex() < questions.length - 1) {
          deps.setCurrentActiveIndex(deps.getCurrentActiveIndex() + 1);
          const isNearEnd = deps.getCurrentActiveIndex() >= questions.length - 3;
          questions[deps.getCurrentActiveIndex()].scrollIntoView({ behavior: 'smooth', block: isNearEnd ? 'center' : 'start' });
          updateActiveState();
        }
      }
    }

    return {
      updateActiveState,
      rebuildNavigation,
      setupScrollObserver,
      checkForNewMessages,
      handleKeyboardShortcut,
    };
  }

  globalThis.JumpAINavigation = {
    scrollPageTo,
    getQuestions,
    getQuestionText,
    getCleanText,
    getCleanAnswerText,
    getAnswerForQuestion,
    createNavigationController,
  };
})();
