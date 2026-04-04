// Popup script - Manifest V3 compatible
const API_BASE = 'https://api-richbot.btacode.com';

let isRecording = false;
let sessionId = null;
let recordingTab = null;

document.addEventListener('DOMContentLoaded', () => {
  chrome.storage.local.get(['authToken', 'user', 'isRecording', 'sessionId', 'recordingTab', 'workflowName', 'selectedBotId'], (result) => {
    if (result.authToken) {
      showRecorder(result.user);
      fetchBots();

      if (result.isRecording) {
        isRecording = true;
        sessionId = result.sessionId;
        recordingTab = result.recordingTab;
        if (result.workflowName) {
          document.getElementById('workflowNameInput').value = result.workflowName;
        }
        updateUI();
        startCounterPoll();
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

// ── Bot dropdown ─────────────────────────────────────────────────
function fetchBots() {
  chrome.runtime.sendMessage({ action: 'fetchBots' }, (response) => {
    if (!response?.success) {
      showToast('Could not load bots', 'error', 'recorder');
      return;
    }
    const bots = Array.isArray(response.data) ? response.data : (response.data.results || []);
    const select = document.getElementById('botSelect');
    select.innerHTML = '<option value="">-- Select Bot --</option>';
    bots.forEach(bot => {
      const opt = document.createElement('option');
      opt.value = bot.id;
      opt.textContent = bot.name;
      select.appendChild(opt);
    });
    chrome.storage.local.get('selectedBotId', (r) => {
      if (r.selectedBotId) select.value = r.selectedBotId;
    });
    select.addEventListener('change', () => {
      const selected = select.options[select.selectedIndex];
      chrome.storage.local.set({ selectedBotId: selected.value, selectedBotName: selected.textContent });
    });
  });
}

// ── Auth ─────────────────────────────────────────────────────────
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
  chrome.storage.local.remove(['authToken', 'refreshToken', 'user', 'isRecording', 'sessionId', 'recordingTab', 'workflowName', 'rbBotActions'], () => {
    showLogin();
  });
}

function login() {
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;

  if (!email || !password) {
    showToast('Please enter username and password', 'error', 'login');
    return;
  }

  const btn = document.getElementById('loginBtn');
  btn.textContent = 'Signing in...';
  btn.disabled = true;

  fetch(`${API_BASE}/auth/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: email, password: password })
  })
    .then(response => {
      if (!response.ok) throw new Error('Invalid credentials');
      return response.json();
    })
    .then(data => {
      const payload = JSON.parse(atob(data.access.split('.')[1]));
      const user = { email: email, userId: payload.user_id };
      chrome.storage.local.set({ authToken: data.access, refreshToken: data.refresh, user }, () => {
        showRecorder(user);
        fetchBots();
      });
    })
    .catch(error => {
      showToast('Login failed: ' + error.message, 'error', 'login');
      btn.textContent = 'Sign In';
      btn.disabled = false;
    });
}

// ── Recording ────────────────────────────────────────────────────
async function startRecording() {
  const workflowName = document.getElementById('workflowNameInput').value || 'Untitled Workflow';
  const botSelect = document.getElementById('botSelect');
  const botId = botSelect?.value;
  const botName = botSelect?.options[botSelect.selectedIndex]?.textContent;

  if (!botId) {
    showToast('Please select a bot before recording', 'error', 'recorder');
    return;
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (!tab?.url || tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://') || tab.url.startsWith('about:')) {
    showToast('Navigate to a website first, then start recording', 'error', 'recorder');
    return;
  }

  sessionId = 'session_' + Date.now();
  recordingTab = tab.id;

  chrome.storage.local.set({
    isRecording: true,
    sessionId,
    recordingTab: tab.id,
    workflowName,
    selectedBotId: botId,
    selectedBotName: botName,
    rbBotActions: []
  });

  chrome.tabs.sendMessage(tab.id, { action: 'startRecording', sessionId }, (response) => {
    if (chrome.runtime.lastError || !response) {
      showToast('Could not start recording on this page. Try refreshing it.', 'error', 'recorder');
      chrome.storage.local.set({ isRecording: false });
      return;
    }
    isRecording = true;
    updateUI();
    startCounterPoll();
    window.close();
  });
}

async function stopRecording() {
  const workflowName = document.getElementById('workflowNameInput').value || 'Untitled Workflow';

  chrome.tabs.sendMessage(recordingTab, { action: 'stopRecording' }, (response) => {
    const actions = response?.actions || [];

    chrome.storage.local.set({ isRecording: false, sessionId: null, recordingTab: null, workflowName: null, rbBotActions: [] });
    isRecording = false;
    updateUI();
    document.getElementById('actionCount').textContent = actions.length;
    showToast(`Recorded ${actions.length} actions`, 'info');

    if (!actions.length) {
      showToast('No actions were recorded', 'error');
      return;
    }

    chrome.storage.local.get(['authToken', 'selectedBotId'], (result) => {
      const recording = {
        workflowName,
        sessionId,
        actions,
        recordedAt: new Date().toISOString(),
        actionCount: actions.length,
        botId: result.selectedBotId || null
      };

      if (result.authToken) {
        showToast('Uploading to server...', 'info');
        chrome.runtime.sendMessage({ action: 'saveWorkflow', payload: recording }, (res) => {
          if (res?.success) {
            showToast(`✅ Saved! Bot: ${res.data.bot_name || 'N/A'}`, 'success');
          } else if (res?.error?.includes('401')) {
            showToast('Session expired. Please login again.', 'error');
            chrome.storage.local.remove(['authToken', 'refreshToken', 'user']);
            showLogin();
          } else {
            showToast(`Upload failed: ${res?.error || 'Unknown'}`, 'error');
            downloadJSON(recording);
          }
        });
      } else {
        downloadJSON(recording);
      }
    });
  });
}

// ── Counter poll ─────────────────────────────────────────────────
let counterInterval = null;
function startCounterPoll() {
  if (counterInterval) clearInterval(counterInterval);
  counterInterval = setInterval(() => {
    if (!isRecording) { clearInterval(counterInterval); return; }
    chrome.storage.local.get('rbBotActions', ({ rbBotActions }) => {
      document.getElementById('actionCount').textContent = (rbBotActions || []).length;
    });
  }, 1000);
}

// ── Helpers ──────────────────────────────────────────────────────
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

function showToast(message, type = 'info', section = 'recorder') {
  const toast = document.getElementById(section === 'login' ? 'loginToast' : 'recorderToast');
  if (!toast) return;
  toast.textContent = message;
  toast.className = `toast toast-${type}`;
  toast.style.display = 'block';
  setTimeout(() => { toast.style.display = 'none'; }, 3500);
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
    badge.className = 'badge badge-recording';
    badge.textContent = 'REC';
    recordBtn.style.display = 'none';
    stopBtn.style.display = 'block';
  } else {
    dot.className = 'status-dot dot-idle';
    statusText.innerHTML = '<strong>Ready</strong> to record';
    badge.className = 'badge badge-idle';
    badge.textContent = 'Idle';
    recordBtn.style.display = 'block';
    stopBtn.style.display = 'none';
  }
}
