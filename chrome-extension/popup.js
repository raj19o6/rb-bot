// Popup script
let isRecording = false;
let sessionId = null;

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
  // Check if user is logged in
  chrome.storage.local.get(['authToken', 'user'], (result) => {
    if (result.authToken) {
      showRecorder(result.user);
    } else {
      showLogin();
    }
  });

  // Add event listeners
  document.getElementById('loginBtn').addEventListener('click', login);
  document.getElementById('recordBtn').addEventListener('click', startRecording);
  document.getElementById('stopBtn').addEventListener('click', stopRecording);
});

function showLogin() {
  document.getElementById('loginSection').style.display = 'block';
  document.getElementById('recorderSection').style.display = 'none';
}

function showRecorder(user) {
  document.getElementById('loginSection').style.display = 'none';
  document.getElementById('recorderSection').style.display = 'block';
  document.getElementById('userInfo').textContent = `Logged in as: ${user.email}`;
}

async function login() {
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;

  if (!email || !password) {
    alert('Please enter email and password');
    return;
  }

  // For demo: accept any credentials
  const user = { email: email };
  chrome.storage.local.set({ authToken: 'demo_token', user: user }, () => {
    showRecorder(user);
  });
}

async function startRecording() {
  sessionId = 'session_' + Date.now();

  console.log('Popup: Starting recording...');

  // Update UI immediately
  isRecording = true;
  updateUI();

  // Get active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  console.log('Popup: Active tab:', tab.id, tab.url);

  // Send message to content script
  chrome.tabs.sendMessage(tab.id, {
    action: 'startRecording',
    sessionId: sessionId
  }, (response) => {
    console.log('Popup: Response:', response);
    
    if (chrome.runtime.lastError) {
      console.error('Popup: Error:', chrome.runtime.lastError.message);
      alert('Please refresh the page and try again');
      isRecording = false;
      updateUI();
      return;
    }
    
    if (response && response.status === 'started') {
      console.log('✅ Recording started successfully');
    }
  });
}

async function stopRecording() {
  const workflowName = document.getElementById('workflowNameInput').value || 'Untitled Workflow';

  console.log('Popup: Stopping recording...');

  // Get active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  // Send message to content script
  chrome.tabs.sendMessage(tab.id, {
    action: 'stopRecording',
    workflowName: workflowName
  }, (response) => {
    console.log('Popup: Stop response:', response);
    
    if (chrome.runtime.lastError) {
      console.error('Popup: Error:', chrome.runtime.lastError.message);
      isRecording = false;
      updateUI();
      return;
    }
    
    if (response && response.status === 'stopped') {
      const actions = response.actions || [];
      console.log('✅ Popup: Retrieved', actions.length, 'actions');

      isRecording = false;
      updateUI();

      // Show success
      document.getElementById('status').textContent =
        `✅ Recorded ${actions.length} actions`;
      document.getElementById('actionCount').textContent = `Actions: ${actions.length}`;

      // Upload to backend
      if (actions.length > 0) {
        document.getElementById('status').textContent =
          `✅ Recorded ${actions.length} actions. Uploading...`;

        chrome.runtime.sendMessage({
          action: 'uploadRecording',
          sessionId: sessionId,
          workflowName: workflowName,
          actions: actions
        }, (uploadResponse) => {
          if (uploadResponse?.status === 'success') {
            document.getElementById('status').textContent =
              `✅ Uploaded successfully!`;
          } else {
            document.getElementById('status').textContent =
              `⚠️ Upload failed (${actions.length} actions recorded)`;
          }
        });
      } else {
        document.getElementById('status').textContent = 'No actions recorded';
      }
    }
  });
}

function updateUI() {
  const status = document.getElementById('status');
  const recordBtn = document.getElementById('recordBtn');
  const stopBtn = document.getElementById('stopBtn');

  if (isRecording) {
    status.className = 'status recording';
    status.textContent = '🔴 Recording...';
    recordBtn.style.display = 'none';
    stopBtn.style.display = 'block';
  } else {
    status.className = 'status idle';
    status.textContent = 'Ready to record';
    recordBtn.style.display = 'block';
    stopBtn.style.display = 'none';
  }
}

// Update action count periodically
setInterval(async () => {
  if (isRecording) {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      chrome.tabs.sendMessage(tab.id, { action: 'getActionCount' }, (response) => {
        if (response && response.count !== undefined) {
          document.getElementById('actionCount').textContent = `Actions: ${response.count}`;
        }
      });
    } catch (e) {
      console.error('Error getting action count:', e);
    }
  }
}, 1000);
