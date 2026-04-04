// Content script — injected into every page, survives navigation
// Restores recording state from storage on each page load

let isRecording = false;
let inputTimers = {};
let lastClick = null;

function getSmartSelector(element) {
  if (element.id) return '#' + element.id;
  if (element.name) return '[name="' + element.name + '"]';
  if (element.getAttribute('data-testid')) return '[data-testid="' + element.getAttribute('data-testid') + '"]';
  if (element.getAttribute('aria-label')) return '[aria-label="' + element.getAttribute('aria-label') + '"]';
  if (element.tagName === 'INPUT' && element.placeholder) return 'input[placeholder="' + element.placeholder + '"]';
  if (element.tagName === 'BUTTON' && element.textContent) {
    const text = element.textContent.trim();
    if (text.length > 0 && text.length < 50) return 'button:has-text("' + text + '")';
  }
  if (element.className && typeof element.className === 'string') {
    const classes = element.className.split(' ')
      .filter(c => c && !c.includes('[') && !c.includes('&') && c.length < 30)
      .slice(0, 2);
    if (classes.length > 0) return element.tagName.toLowerCase() + '.' + classes.join('.');
  }
  return element.tagName.toLowerCase();
}

function handleClick(e) {
  if (!isRecording) return;
  const target = e.target;
  const selector = getSmartSelector(target);
  const clickKey = selector + '_' + (target.textContent || '').substring(0, 20);
  const now = Date.now();

  if (lastClick && lastClick.key === clickKey && (now - lastClick.time) < 300) return;
  lastClick = { key: clickKey, time: now };

  const action = {
    type: 'click',
    selector,
    text: (target.textContent || '').substring(0, 50),
    timestamp: now,
    url: window.location.href
  };

  appendAction(action);
}

function handleInput(e) {
  if (!isRecording) return;
  const selector = getSmartSelector(e.target);
  if (inputTimers[selector]) clearTimeout(inputTimers[selector]);

  inputTimers[selector] = setTimeout(() => {
    const action = {
      type: 'fill',
      selector,
      value: e.target.value,
      timestamp: Date.now(),
      url: window.location.href
    };
    // Remove previous fill for same selector then append
    chrome.storage.local.get('rbBotActions', ({ rbBotActions }) => {
      const actions = (rbBotActions || []).filter(a => !(a.type === 'fill' && a.selector === selector));
      actions.push(action);
      chrome.storage.local.set({ rbBotActions: actions });
      updateIndicator(actions.length);
    });
  }, 1000);
}

function appendAction(action) {
  chrome.storage.local.get('rbBotActions', ({ rbBotActions }) => {
    const actions = rbBotActions || [];
    actions.push(action);
    chrome.storage.local.set({ rbBotActions: actions });
    updateIndicator(actions.length);
  });
}

function showIndicator(count) {
  if (document.getElementById('rb-bot-indicator')) return;
  const el = document.createElement('div');
  el.id = 'rb-bot-indicator';
  el.style.cssText = `
    position: fixed; top: 10px; right: 10px;
    background: #ef4444; color: white;
    padding: 12px 24px; border-radius: 8px;
    z-index: 2147483647; font-family: Arial;
    font-weight: bold; font-size: 14px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    pointer-events: none;
  `;
  el.textContent = `Recording... (${count})`;
  document.body.appendChild(el);
}

function updateIndicator(count) {
  const el = document.getElementById('rb-bot-indicator');
  if (el) el.textContent = `Recording... (${count})`;
}

function hideIndicator() {
  const el = document.getElementById('rb-bot-indicator');
  if (el) el.remove();
}

function startListeners() {
  document.addEventListener('click', handleClick, { capture: true, passive: true });
  document.addEventListener('input', handleInput, true);
}

function stopListeners() {
  document.removeEventListener('click', handleClick, true);
  document.removeEventListener('input', handleInput, true);
}

// On every page load — restore recording state from storage
chrome.storage.local.get(['isRecording', 'rbBotActions'], ({ isRecording: stored, rbBotActions }) => {
  if (stored) {
    isRecording = true;
    startListeners();
    // Wait for DOM to be ready before showing indicator
    const show = () => showIndicator((rbBotActions || []).length);
    document.readyState === 'loading'
      ? document.addEventListener('DOMContentLoaded', show)
      : show();
  }
});

// Listen for commands from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'startRecording') {
    isRecording = true;
    inputTimers = {};
    lastClick = null;
    chrome.storage.local.set({ rbBotActions: [] });
    startListeners();
    showIndicator(0);
    sendResponse({ status: 'started' });
  }

  if (message.action === 'stopRecording') {
    isRecording = false;
    stopListeners();
    hideIndicator();
    chrome.storage.local.get('rbBotActions', ({ rbBotActions }) => {
      sendResponse({ status: 'stopped', actions: rbBotActions || [] });
    });
    return true; // async
  }

  if (message.action === 'getActionCount') {
    chrome.storage.local.get('rbBotActions', ({ rbBotActions }) => {
      sendResponse({ count: (rbBotActions || []).length });
    });
    return true;
  }
});
