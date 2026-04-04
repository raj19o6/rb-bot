const API_BASE = 'https://api-richbot.btacode.com';

// Refresh access token using stored refresh token
async function refreshAccessToken() {
  const { refreshToken } = await chrome.storage.local.get('refreshToken');
  if (!refreshToken) return null;

  try {
    const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken })
    });
    if (!res.ok) throw new Error('Refresh failed');
    const data = await res.json();
    await chrome.storage.local.set({ authToken: data.access });
    return data.access;
  } catch {
    // Refresh token expired — clear auth
    await chrome.storage.local.remove(['authToken', 'refreshToken', 'user']);
    return null;
  }
}

// Fetch with automatic token refresh on 401
async function apiFetch(url, options = {}) {
  const { authToken } = await chrome.storage.local.get('authToken');
  options.headers = { 'Content-Type': 'application/json', ...options.headers };
  if (authToken) options.headers['Authorization'] = `Bearer ${authToken}`;

  let res = await fetch(url, options);

  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      options.headers['Authorization'] = `Bearer ${newToken}`;
      res = await fetch(url, options);
    }
  }
  return res;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'saveWorkflow') {
    apiFetch(`${API_BASE}/api/v1/workflows/save/`, {
      method: 'POST',
      body: JSON.stringify(message.payload)
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        sendResponse({ success: true, data });
      })
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true; // keep channel open for async response
  }

  if (message.action === 'fetchBots') {
    apiFetch(`${API_BASE}/api/v1/bot/available/`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        sendResponse({ success: true, data });
      })
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true;
  }
});
