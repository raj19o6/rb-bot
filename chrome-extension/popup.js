// Popup script - Manifest V3 compatible
let isRecording = false;
let sessionId = null;
let recordingTab = null;

document.addEventListener('DOMContentLoaded', () => {
  chrome.storage.local.get(['authToken', 'user', 'isRecording', 'sessionId', 'recordingTab', 'workflowName'], (result) => {
    if (result.authToken) {
      showRecorder(result.user);

      if (result.isRecording) {
        isRecording = true;
        sessionId = result.sessionId;
        recordingTab = result.recordingTab;

        if (result.workflowName) {
          document.getElementById('workflowNameInput').value = result.workflowName;
        }

        updateUI();
      }
    } else {
      showLogin();
    }
  });

  document.getElementById('loginBtn').addEventListener('click', login);
  document.getElementById('recordBtn').addEventListener('click', startRecording);
  document.getElementById('stopBtn').addEventListener('click', stopRecording);
  document.getElementById('logoutBtn').addEventListener('click', logout);
});

function showLogin() {
  document.getElementById('loginSection').style.display = 'block';
  document.getElementById('recorderSection').style.display = 'none';
}

function showRecorder(user) {
  document.getElementById('loginSection').style.display = 'none';
  document.getElementById('recorderSection').style.display = 'block';
  document.getElementById('userInfo').textContent = user.email;
  document.getElementById('userAvatar').textContent = (user.email || '?')[0].toUpperCase();
}

function logout() {
  chrome.storage.local.remove(['authToken', 'refreshToken', 'user', 'isRecording', 'sessionId', 'recordingTab', 'workflowName'], () => {
    showLogin();
  });
}

function showToast(message, type = 'info') {
  const toasts = document.querySelectorAll('#toast');
  const toast = toasts[toasts.length - 1];
  toast.textContent = message;
  toast.className = `toast-${type}`;
  toast.style.display = 'block';
  setTimeout(() => { toast.style.display = 'none'; }, 3500);
}

function login() {
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;

  if (!email || !password) {
    showToast('Please enter username and password', 'error');
    return;
  }

  const btn = document.getElementById('loginBtn');
  btn.textContent = 'Signing in...';
  btn.disabled = true;

  fetch('https://lknpz8c6-8000.inc1.devtunnels.ms/auth/token/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: email, password: password })
  })
    .then(response => {
      if (!response.ok) throw new Error('Invalid credentials');
      return response.json();
    })
    .then(data => data)
    .then(data => {
      const tokenParts = data.access.split('.');
      const payload = JSON.parse(atob(tokenParts[1]));
      const user = { email: email, userId: payload.user_id };
      chrome.storage.local.set({
        authToken: data.access,
        refreshToken: data.refresh,
        user: user
      }, () => showRecorder(user));
    })
    .catch(error => {
      showToast('Login failed: ' + error.message, 'error');
      const btn = document.getElementById('loginBtn');
      btn.innerHTML = '<span>🔐</span> Sign In';
      btn.disabled = false;
    });
}

async function startRecording() {
  const workflowName = document.getElementById('workflowNameInput').value || 'Untitled Workflow';
  sessionId = 'session_' + Date.now();

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  recordingTab = tab.id;

  chrome.storage.local.set({
    isRecording: true,
    sessionId: sessionId,
    recordingTab: tab.id,
    workflowName: workflowName
  });

  try {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (sid) => {
        window.rbBotRecording = true;
        window.rbBotActions = [];
        window.rbBotSessionId = sid;
        window.rbBotInputTimers = {};
        window.rbBotLastClick = null;

        console.log('RB-BOT: Recording started!');

        const indicator = document.createElement('div');
        indicator.id = 'rb-bot-indicator';
        indicator.style.cssText = `
          position: fixed; top: 10px; right: 10px;
          background: #ef4444; color: white;
          padding: 12px 24px; border-radius: 8px;
          z-index: 2147483647; font-family: Arial;
          font-weight: bold; font-size: 14px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        `;
        indicator.innerHTML = 'Recording...';
        document.body.appendChild(indicator);

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
            const classes = element.className.split(' ').filter(c => c && !c.includes('[') && !c.includes('&') && c.length < 30).slice(0, 2);
            if (classes.length > 0) return element.tagName.toLowerCase() + '.' + classes.join('.');
          }
          return element.tagName.toLowerCase();
        }

        document.addEventListener('click', function (e) {
          if (!window.rbBotRecording) return;

          const target = e.target;
          const selector = getSmartSelector(target);
          const clickKey = selector + '_' + (target.textContent || '').substring(0, 20);
          const now = Date.now();

          if (window.rbBotLastClick && window.rbBotLastClick.key === clickKey && (now - window.rbBotLastClick.time) < 300) {
            console.log('Skipped duplicate click:', clickKey);
            return;
          }

          window.rbBotLastClick = { key: clickKey, time: now };

          const action = {
            type: 'click',
            selector: selector,
            text: (target.textContent || '').substring(0, 50),
            timestamp: now,
            url: window.location.href
          };

          window.rbBotActions.push(action);
          console.log('Recorded click:', action);

          const ind = document.getElementById('rb-bot-indicator');
          if (ind) ind.innerHTML = 'Recording... (' + window.rbBotActions.length + ')';
        }, { capture: true, passive: true });

        document.addEventListener('input', function (e) {
          if (!window.rbBotRecording) return;

          const selector = getSmartSelector(e.target);

          if (window.rbBotInputTimers[selector]) clearTimeout(window.rbBotInputTimers[selector]);

          window.rbBotInputTimers[selector] = setTimeout(() => {
            window.rbBotActions = window.rbBotActions.filter(a => !(a.type === 'fill' && a.selector === selector));

            const action = {
              type: 'fill',
              selector: selector,
              value: e.target.value,
              timestamp: Date.now(),
              url: window.location.href
            };

            window.rbBotActions.push(action);
            console.log('Recorded input:', action);

            const ind = document.getElementById('rb-bot-indicator');
            if (ind) ind.innerHTML = 'Recording... (' + window.rbBotActions.length + ')';
          }, 1000);
        }, true);

        console.log('Recording active!');
      },
      args: [sessionId]
    });

    console.log('Recording started');
    window.close();
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

async function stopRecording() {
  const workflowName = document.getElementById('workflowNameInput').value || 'Untitled Workflow';

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: recordingTab },
      func: () => {
        window.rbBotRecording = false;
        const indicator = document.getElementById('rb-bot-indicator');
        if (indicator) indicator.remove();
        console.log('Recording stopped. Total:', window.rbBotActions.length);
        return window.rbBotActions || [];
      }
    });

    const actions = results[0]?.result || [];
    console.log('Retrieved', actions.length, 'actions');

    chrome.storage.local.set({ isRecording: false, sessionId: null, recordingTab: null, workflowName: null });

    isRecording = false;
    updateUI();

    document.getElementById('actionCount').textContent = actions.length;
    showToast(`Recorded ${actions.length} actions`, 'info');

    if (actions.length > 0) {
      const recording = {
        workflowName: workflowName,
        sessionId: sessionId,
        actions: actions,
        recordedAt: new Date().toISOString(),
        actionCount: actions.length
      };

      chrome.storage.local.get(['recordings', 'authToken'], async (result) => {
        const recordings = result.recordings || [];
        recordings.push(recording);
        chrome.storage.local.set({ recordings: recordings });

        if (result.authToken) {
          try {
            showToast('Uploading to server...', 'info');

            const response = await fetch('https://lknpz8c6-8000.inc1.devtunnels.ms/api/v1/workflows/save/', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${result.authToken}`
              },
              body: JSON.stringify(recording)
            });

            if (response.ok) {
              const data = await response.json();
              showToast(`✅ Saved! ID: ${(data.workflow_id || data.id || '').toString().slice(0, 8)}...`, 'success');
              console.log('Workflow saved:', data);
            } else {
              showToast(`Upload failed (${response.status}), downloading...`, 'error');
              downloadJSON(recording);
            }
          } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
            downloadJSON(recording);
          }
        } else {
          downloadJSON(recording);
        }
      });
    } else {
      showToast('No actions were recorded', 'error');
    }
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

function downloadJSON(recording) {
  const blob = new Blob([JSON.stringify(recording, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${recording.workflowName.replace(/\s+/g, '_')}_${recording.sessionId}.json`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('Downloaded locally', 'info');
}

function updateUI() {
  const dot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const badge = document.getElementById('headerBadge');
  const recordBtn = document.getElementById('recordBtn');
  const stopBtn = document.getElementById('stopBtn');

  if (isRecording) {
    dot.className = 'status-dot dot-recording';
    statusText.innerHTML = '<strong>Recording</strong> in progress...';
    badge.className = 'header-badge badge-recording';
    badge.textContent = '● REC';
    recordBtn.style.display = 'none';
    stopBtn.style.display = 'flex';
  } else {
    dot.className = 'status-dot dot-idle';
    statusText.innerHTML = '<strong>Ready</strong> to record';
    badge.className = 'header-badge badge-idle';
    badge.textContent = 'IDLE';
    recordBtn.style.display = 'flex';
    stopBtn.style.display = 'none';
  }
}

setInterval(async () => {
  if (isRecording && recordingTab) {
    try {
      const results = await chrome.scripting.executeScript({
        target: { tabId: recordingTab },
        func: () => window.rbBotActions ? window.rbBotActions.length : 0
      });

      if (results && results[0]) {
        document.getElementById('actionCount').textContent = results[0].result;
      }
    } catch (e) { }
  }
}, 1000);
