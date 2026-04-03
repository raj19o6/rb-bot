// Content script - Injected into web pages to record actions

let isRecording = false;
let recordedActions = [];
let sessionId = null;

console.log('RB-BOT Content Script Loaded!');

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Content script received message:', message);

  if (message.action === 'startRecording') {
    startRecording(message.sessionId);
    sendResponse({ status: 'started' });
    return true;
  }

  if (message.action === 'stopRecording') {
    const actions = stopRecording(message.workflowName);
    sendResponse({ status: 'stopped', actions: actions });
    return true;
  }

  if (message.action === 'getActionCount') {
    sendResponse({ count: recordedActions.length });
    return true;
  }
});

function startRecording(sid) {
  isRecording = true;
  sessionId = sid;
  recordedActions = [];

  console.log('🔴 Recording started! Session:', sid);

  // Add event listeners
  document.addEventListener('click', handleClick, true);
  document.addEventListener('input', handleInput, true);
  document.addEventListener('submit', handleSubmit, true);

  // Visual indicator
  showRecordingIndicator();
}

function stopRecording(workflowName) {
  isRecording = false;

  console.log('⏹️ Recording stopped! Total actions:', recordedActions.length);

  // Remove event listeners
  document.removeEventListener('click', handleClick, true);
  document.removeEventListener('input', handleInput, true);
  document.removeEventListener('submit', handleSubmit, true);

  // Remove visual indicator
  hideRecordingIndicator();

  // Upload to background script
  chrome.runtime.sendMessage({
    action: 'uploadRecording',
    sessionId: sessionId,
    workflowName: workflowName || 'Untitled Workflow',
    actions: recordedActions
  });

  console.log('Recorded actions:', recordedActions);

  return recordedActions;
}

function handleClick(event) {
  if (!isRecording) return;

  const element = event.target;
  const selector = getSelector(element);

  const action = {
    type: 'click',
    selector: selector,
    text: element.textContent?.substring(0, 50) || '',
    timestamp: Date.now(),
    url: window.location.href
  };

  recordedActions.push(action);
  console.log('Recorded click:', action);
}

let inputTimeout = null;
function handleInput(event) {
  if (!isRecording) return;

  clearTimeout(inputTimeout);
  inputTimeout = setTimeout(() => {
    const element = event.target;
    const selector = getSelector(element);

    const action = {
      type: 'fill',
      selector: selector,
      value: element.value,
      timestamp: Date.now(),
      url: window.location.href
    };

    recordedActions.push(action);
    console.log('Recorded input:', action);
  }, 500);
}

function handleSubmit(event) {
  if (!isRecording) return;

  const element = event.target;
  const selector = getSelector(element);

  recordedActions.push({
    type: 'submit',
    selector: selector,
    timestamp: Date.now(),
    url: window.location.href
  });
}

function getSelector(element) {
  if (element.id) {
    return `#${element.id}`;
  }

  if (element.name) {
    return `[name="${element.name}"]`;
  }

  if (element.className) {
    const classes = element.className.split(' ').filter(c => c).join('.');
    return `${element.tagName.toLowerCase()}.${classes}`;
  }

  return element.tagName.toLowerCase();
}

// Visual indicator
function showRecordingIndicator() {
  const indicator = document.createElement('div');
  indicator.id = 'rb-bot-indicator';
  indicator.style.cssText = `
    position: fixed;
    top: 10px;
    right: 10px;
    background: red;
    color: white;
    padding: 10px 20px;
    border-radius: 5px;
    z-index: 999999;
    font-family: Arial;
    font-weight: bold;
    animation: pulse 1s infinite;
  `;
  indicator.textContent = '🔴 Recording...';
  document.body.appendChild(indicator);
}

function hideRecordingIndicator() {
  const indicator = document.getElementById('rb-bot-indicator');
  if (indicator) {
    indicator.remove();
  }
}
