# RB-BOT Chrome Extension

Records web workflows and saves them to the RB-BOT backend.

## Prerequisites

- Google Chrome browser
- RB-BOT backend running at `http://127.0.0.1:8000` (or update `API_BASE` in `popup.js`)

## Setup

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle, top-right)
3. Click **Load unpacked**
4. Select the `chrome-extension/` folder
5. The **RB-BOT** icon will appear in your toolbar

## Usage

1. Click the RB-BOT extension icon
2. Sign in with your RB-BOT account credentials
3. Select a **Bot** from the dropdown
4. Enter a **Workflow Name**
5. Navigate to the website you want to record
6. Click **Start Recording** — a red indicator appears on the page
7. Perform your workflow (clicks, form inputs, etc.)
8. Click **Stop and Save** — the workflow is uploaded to the backend automatically

> If the backend is unreachable, the workflow is downloaded as a JSON file instead.

## Permissions Used

| Permission | Reason |
|---|---|
| `activeTab` | Inject recording script into current tab |
| `scripting` | Execute content scripts for recording |
| `storage` | Persist auth token and recording state |
| `tabs` | Identify the active tab being recorded |
| `downloads` | Fallback: download workflow as JSON |
| `host_permissions: <all_urls>` | Record on any website |
