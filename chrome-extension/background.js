// Background script - Handles API communication

const API_URL = 'http://127.0.0.1:8000';

// Listen for messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'uploadRecording') {
    uploadWorkflow(message.sessionId, message.actions)
      .then(result => sendResponse({ status: 'success', result }))
      .catch(error => sendResponse({ status: 'error', error: error.message }));
    return true;
  }

  if (message.action === 'login') {
    login(message.email, message.password)
      .then(result => sendResponse({ status: 'success', result }))
      .catch(error => sendResponse({ status: 'error', error: error.message }));
    return true;
  }
});

async function uploadWorkflow(sessionId, actions) {
  const { authToken } = await chrome.storage.local.get('authToken');

  if (!authToken) {
    throw new Error('Not authenticated');
  }

  console.log('Uploading workflow:', { sessionId, actionCount: actions.length });

  const response = await fetch(`${API_URL}/api/workflows`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`
    },
    body: JSON.stringify({
      session_id: sessionId,
      actions: actions,
      recorded_at: new Date().toISOString()
    })
  });

  if (!response.ok) {
    console.error('Upload failed:', response.statusText);
    throw new Error(`Upload failed: ${response.statusText}`);
  }

  const result = await response.json();
  console.log('Upload successful:', result);

  chrome.notifications.create({
    type: 'basic',
    title: 'RB-BOT',
    message: `Workflow saved! ${actions.length} actions recorded.`
  });

  return result;
}

async function login(email, password) {
  const response = await fetch(`${API_URL}/auth/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: email, password: password })
  });

  if (!response.ok) {
    throw new Error('Login failed');
  }

  const data = await response.json();
  await chrome.storage.local.set({
    authToken: data.access,
    refreshToken: data.refresh,
    user: { username: email }
  });

  return data;
}
