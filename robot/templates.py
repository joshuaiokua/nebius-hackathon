"""HTML templates for the robot control panel."""


def render_control_panel(session_id: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Robot Control Panel</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

:root {{
  --bg: #050507;
  --surface: #0e0f12;
  --surface-2: #161820;
  --surface-3: #1e2028;
  --border: #2a2d38;
  --border-hover: #3a3d48;
  --text: #e8e8ed;
  --text-muted: #9ca3af;
  --text-dim: #6b7280;
  --accent: #6ee7b7;
  --accent-dim: #34d399;
  --accent-bg: rgba(110, 231, 183, 0.08);
  --danger: #ef4444;
  --danger-bg: rgba(239, 68, 68, 0.08);
  --warning: #f59e0b;
  --warning-bg: rgba(245, 158, 11, 0.08);
  --blue: #60a5fa;
  --blue-bg: rgba(96, 165, 250, 0.08);
  --purple: #a78bfa;
}}

body {{
  font-family: 'Inter', sans-serif;
  background: var(--bg);
  color: var(--text);
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}

/* ---------- Header ---------- */

.header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}}

.header-left {{
  display: flex;
  align-items: center;
  gap: 12px;
}}

.sidebar-toggle {{
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  flex-shrink: 0;
}}

.sidebar-toggle:hover {{
  background: var(--surface-2);
  color: var(--text);
  border-color: var(--border-hover);
}}

.logo {{
  font-size: 17px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent), var(--blue));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}}

.status-badge {{
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

.status-idle {{ background: var(--accent-bg); color: var(--accent); }}
.status-planning, .status-searching {{ background: var(--blue-bg); color: var(--blue); }}
.status-awaiting_approval {{ background: var(--warning-bg); color: var(--warning); }}
.status-installing {{ background: rgba(168, 139, 250, 0.1); color: var(--purple); }}
.status-executing {{ background: var(--accent-bg); color: var(--accent); }}
.status-error {{ background: var(--danger-bg); color: var(--danger); }}

.header-right {{
  display: flex;
  align-items: center;
  gap: 16px;
}}

.caps-count {{
  font-size: 13px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}}

.store-link {{
  font-size: 13px;
  color: var(--accent);
  text-decoration: none;
}}
.store-link:hover {{ text-decoration: underline; }}

/* ---------- Main layout ---------- */

.main {{
  display: flex;
  flex: 1;
  overflow: hidden;
}}

/* ---------- Chat panel ---------- */

.chat-panel {{
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}}

.messages {{
  flex: 1;
  overflow-y: auto;
  padding: 0;
  display: flex;
  flex-direction: column;
}}

.messages::-webkit-scrollbar {{ width: 6px; }}
.messages::-webkit-scrollbar-track {{ background: transparent; }}
.messages::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}

@keyframes fadeIn {{
  from {{ opacity: 0; transform: translateY(4px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

/* --- Chat rows (ChatGPT style) --- */

.msg-row {{
  display: flex;
  gap: 16px;
  padding: 20px 24px;
  animation: fadeIn 0.25s ease;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}}

.msg-row:hover {{
  background: rgba(255,255,255,0.015);
}}

.msg-row-user {{
  background: transparent;
}}

.msg-row-robot {{
  background: var(--surface);
}}

.msg-row-center {{
  max-width: 760px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  gap: 16px;
}}

.msg-avatar {{
  width: 32px;
  height: 32px;
  min-width: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}}

.msg-avatar-user {{
  background: var(--accent);
  color: #050507;
}}

.msg-avatar-robot {{
  background: var(--purple);
  color: #fff;
}}

.msg-avatar-system {{
  background: var(--surface-3);
  color: var(--text-dim);
  border-radius: 50%;
  font-size: 14px;
}}

.msg-body {{
  flex: 1;
  min-width: 0;
}}

.msg-sender {{
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
  color: var(--text);
}}

.msg-content {{
  font-size: 14.5px;
  line-height: 1.6;
  color: var(--text);
  word-wrap: break-word;
}}

.msg-row-user .msg-content {{
  color: var(--text);
}}

.msg-row-robot .msg-content {{
  color: var(--text);
}}

.msg-timestamp {{
  font-size: 10px;
  color: var(--text-dim);
  margin-top: 6px;
  font-family: 'JetBrains Mono', monospace;
}}

/* --- Status messages (keep original colors) --- */

.msg-row-status,
.msg-row-warning,
.msg-row-error,
.msg-row-plan,
.msg-row-system {{
  background: transparent;
  padding: 8px 24px;
  border-bottom: none;
}}

.msg-row-status:hover,
.msg-row-warning:hover,
.msg-row-error:hover,
.msg-row-plan:hover,
.msg-row-system:hover {{
  background: transparent;
}}

.msg-row-status .msg-sender,
.msg-row-warning .msg-sender,
.msg-row-error .msg-sender,
.msg-row-system .msg-sender {{
  display: none;
}}

.msg-row-status .msg-content {{
  background: var(--surface-2);
  border-left: 3px solid var(--blue);
  border-radius: 4px 8px 8px 4px;
  padding: 10px 14px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
}}

.msg-row-warning .msg-content {{
  background: var(--warning-bg);
  border-left: 3px solid var(--warning);
  border-radius: 4px 8px 8px 4px;
  padding: 10px 14px;
  color: var(--warning);
  font-size: 14px;
  font-weight: 500;
}}

.msg-row-error .msg-content {{
  background: var(--danger-bg);
  border-left: 3px solid var(--danger);
  border-radius: 4px 8px 8px 4px;
  padding: 10px 14px;
  color: var(--danger);
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
}}

.msg-row-plan .msg-content {{
  background: var(--accent-bg);
  border-left: 3px solid var(--accent);
  border-radius: 4px 8px 8px 4px;
  padding: 10px 14px;
  color: var(--accent);
  font-size: 14px;
  font-weight: 500;
}}

.msg-row-system .msg-content {{
  color: var(--text-dim);
  font-size: 12px;
}}

/* ---------- Part card ---------- */

.part-card {{
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  max-width: 420px;
  width: 100%;
  margin: 8px 0;
}}

.part-card-header {{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}}

.part-card-cap {{
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent);
  font-weight: 600;
}}

.part-card-step {{
  font-size: 11px;
  color: var(--text-dim);
  font-family: 'JetBrains Mono', monospace;
}}

.part-card-name {{
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 6px;
}}

.part-card-meta {{
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
  margin-bottom: 8px;
}}

.part-card-tools {{
  font-size: 12px;
  color: var(--text-dim);
  margin-bottom: 8px;
}}

.part-card-tools code {{
  background: var(--surface-3);
  padding: 1px 5px;
  border-radius: 3px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--text-muted);
}}

.part-card-price {{
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
}}

/* ---------- Approval buttons ---------- */

.approval-row {{
  display: flex;
  gap: 10px;
  padding: 8px 24px 8px 72px;
  max-width: 808px;
  margin: 0 auto;
  animation: fadeIn 0.2s ease;
}}

.btn-approve, .btn-deny {{
  padding: 8px 20px;
  border-radius: 8px;
  border: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: 'Inter', sans-serif;
  transition: all 0.15s;
}}

.btn-approve {{
  background: var(--accent);
  color: #050507;
}}
.btn-approve:hover {{ background: #86efac; transform: translateY(-1px); }}

.btn-deny {{
  background: var(--surface-3);
  color: var(--text-muted);
  border: 1px solid var(--border);
}}
.btn-deny:hover {{ background: var(--surface-2); color: var(--danger); border-color: var(--danger); }}

.btn-approve:disabled, .btn-deny:disabled {{
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
}}

/* ---------- Input bar ---------- */

.input-bar-wrap {{
  padding: 12px 24px 20px;
  background: var(--bg);
  flex-shrink: 0;
}}

.input-bar {{
  max-width: 760px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 24px;
  padding: 6px 6px 6px 20px;
  transition: border-color 0.2s, box-shadow 0.2s;
}}

.input-bar:focus-within {{
  border-color: rgba(110, 231, 183, 0.4);
  box-shadow: 0 0 0 1px rgba(110, 231, 183, 0.15), 0 4px 20px rgba(0,0,0,0.3);
}}

.input-bar textarea {{
  flex: 1;
  padding: 8px 0;
  background: transparent;
  border: none;
  color: var(--text);
  font-size: 15px;
  font-family: 'Inter', sans-serif;
  outline: none;
  resize: none;
  max-height: 150px;
  line-height: 1.5;
  min-height: 24px;
}}

.input-bar textarea::placeholder {{
  color: var(--text-dim);
}}

.input-bar button {{
  width: 36px;
  height: 36px;
  min-width: 36px;
  min-height: 36px;
  background: var(--accent);
  color: #050507;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}}

.input-bar button:hover {{ background: #86efac; transform: scale(1.05); }}
.input-bar button:disabled {{ opacity: 0.3; cursor: not-allowed; transform: none; }}

.input-hint {{
  max-width: 760px;
  margin: 6px auto 0;
  font-size: 11px;
  color: var(--text-dim);
  text-align: center;
}}

/* ---------- Side panel ---------- */

.side-panel {{
  width: 280px;
  background: var(--surface);
  border-right: 1px solid var(--border);
  padding: 16px;
  overflow-y: auto;
  overflow-x: hidden;
  flex-shrink: 0;
  transition: width 0.25s ease, padding 0.25s ease, opacity 0.2s ease;
}}

.side-panel.collapsed {{
  width: 0;
  padding: 0;
  opacity: 0;
  border-right: none;
  overflow: hidden;
}}

.side-section {{
  margin-bottom: 24px;
}}

.side-title {{
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-dim);
  font-weight: 600;
  margin-bottom: 10px;
}}

.robot-info {{
  font-size: 13px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
  line-height: 1.8;
}}

.cap-tag {{
  display: inline-block;
  padding: 3px 8px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--text-muted);
  margin: 2px;
}}

.cap-tag.installed {{
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-bg);
}}

.installed-part {{
  padding: 8px 10px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 6px;
  font-size: 12px;
}}

.installed-part-name {{
  font-weight: 600;
  color: var(--text);
  margin-bottom: 2px;
}}

.installed-part-cap {{
  font-size: 11px;
  color: var(--accent);
  font-family: 'JetBrains Mono', monospace;
}}

/* ---------- Example tasks ---------- */

.example-tasks {{
  display: flex;
  flex-direction: column;
  gap: 6px;
}}

.example-task {{
  padding: 8px 10px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
  font-family: 'Inter', sans-serif;
}}

.example-task:hover {{
  border-color: var(--accent);
  color: var(--text);
  background: var(--accent-bg);
}}

/* ---------- Sim viewer ---------- */

.sim-viewer {{
  padding: 0;
}}

/* ---------- Collapsible sections ---------- */

.side-title.collapsible {{
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  user-select: none;
  padding: 4px 0;
  transition: color 0.15s;
}}

.side-title.collapsible:hover {{
  color: var(--text-muted);
}}

.collapse-icon {{
  transition: transform 0.2s ease;
}}

.side-title.collapsible[data-open="false"] .collapse-icon {{
  transform: rotate(-90deg);
}}

.side-collapsible {{
  overflow: hidden;
  max-height: 600px;
  transition: max-height 0.25s ease, opacity 0.2s ease;
  opacity: 1;
}}

.side-collapsible.collapsed {{
  max-height: 0;
  opacity: 0;
}}

/* ---------- Responsive ---------- */

@media (max-width: 768px) {{
  .side-panel {{ display: none; }}
  .msg-row {{ padding: 12px 16px; }}
  .input-bar-wrap {{ padding: 8px 12px 14px; }}
}}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <button class="sidebar-toggle" id="sidebar-toggle" onclick="toggleSidebar()" aria-label="Toggle sidebar">
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="2" y="4" width="14" height="1.5" rx="0.75" fill="currentColor"/><rect x="2" y="8.25" width="14" height="1.5" rx="0.75" fill="currentColor"/><rect x="2" y="12.5" width="14" height="1.5" rx="0.75" fill="currentColor"/></svg>
    </button>
    <div class="logo">RoboStore</div>
    <div class="status-badge status-idle" id="status-badge">IDLE</div>
  </div>
  <div class="header-right">
    <span class="caps-count" id="caps-count">2 capabilities</span>
    <a href="http://localhost:8000/store" target="_blank" class="store-link">Parts Store &rarr;</a>
  </div>
</div>

<div class="main">
  <div class="side-panel">
    <div class="side-section">
      <div class="side-title collapsible" onclick="toggleSection(this)" data-open="true">
        <span>Sim View</span>
        <svg class="collapse-icon" width="12" height="12" viewBox="0 0 12 12"><path d="M3 5L6 8L9 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" fill="none"/></svg>
      </div>
      <div class="side-collapsible">
        <div class="sim-viewer">
          <div style="display:flex; align-items:center; justify-content:center; overflow:hidden; background:#000; border-radius:8px; aspect-ratio:4/3;">
            <img id="sim-camera" src="/api/sim/frame" alt="MuJoCo G1"
                 style="max-width:100%; max-height:100%; object-fit:contain;">
          </div>
        </div>
      </div>
    </div>

    <div class="side-section">
      <div class="side-title collapsible" onclick="toggleSection(this)" data-open="true">
        <span>Robot Profile</span>
        <svg class="collapse-icon" width="12" height="12" viewBox="0 0 12 12"><path d="M3 5L6 8L9 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" fill="none"/></svg>
      </div>
      <div class="side-collapsible">
        <div class="robot-info">
          <div><strong>ID:</strong> unitree-g1-sim</div>
          <div><strong>Platform:</strong> Unitree G1</div>
          <div><strong>DOF:</strong> 23 joints</div>
          <div><strong>Power:</strong> 15W budget</div>
          <div><strong>Sim:</strong> MuJoCo</div>
        </div>
      </div>
    </div>

    <div class="side-section">
      <div class="side-title collapsible" onclick="toggleSection(this)" data-open="true">
        <span>Capabilities</span>
        <svg class="collapse-icon" width="12" height="12" viewBox="0 0 12 12"><path d="M3 5L6 8L9 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" fill="none"/></svg>
      </div>
      <div class="side-collapsible">
        <div id="capabilities">
          <span class="cap-tag">locomotion</span>
          <span class="cap-tag">imu</span>
        </div>
      </div>
    </div>

    <div class="side-section" id="installed-section" style="display:none">
      <div class="side-title">Installed Parts</div>
      <div id="installed-parts"></div>
    </div>

    <div class="side-section">
      <div class="side-title collapsible" onclick="toggleSection(this)" data-open="true">
        <span>Try These</span>
        <svg class="collapse-icon" width="12" height="12" viewBox="0 0 12 12"><path d="M3 5L6 8L9 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" fill="none"/></svg>
      </div>
      <div class="side-collapsible">
        <div class="example-tasks">
          <button class="example-task" onclick="setTask(this.textContent)">
            Walk forward 5 meters
          </button>
          <button class="example-task" onclick="setTask(this.textContent)">
            Pick up the red box and bring it to the charging station
          </button>
          <button class="example-task" onclick="setTask(this.textContent)">
            Patrol the warehouse perimeter and report obstacles
          </button>
          <button class="example-task" onclick="setTask(this.textContent)">
            Build a wall 2 meters ahead
          </button>
        </div>
      </div>
    </div>
  </div>

  <div class="chat-panel">
    <div class="messages" id="messages"></div>
    <div class="input-bar-wrap">
      <div class="input-bar">
        <textarea id="task-input" rows="1" placeholder="Send a command to the robot..." autocomplete="off"></textarea>
        <button id="send-btn" onclick="sendUnified()" aria-label="Send">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 14L14.5 8L2 2V6.5L10 8L2 9.5V14Z" fill="currentColor"/></svg>
        </button>
      </div>
      <div class="input-hint">Press Enter to send, Shift+Enter for new line</div>
    </div>
  </div>
</div>

<script>
const SESSION_ID = "{session_id}";
const messagesEl = document.getElementById("messages");
const taskInput = document.getElementById("task-input");
const sendBtn = document.getElementById("send-btn");
const statusBadge = document.getElementById("status-badge");
const capsEl = document.getElementById("capabilities");
const capsCount = document.getElementById("caps-count");
const installedSection = document.getElementById("installed-section");
const installedParts = document.getElementById("installed-parts");

let robotStatus = "idle";

// --- SSE Connection ---

let sseRetries = 0;

function connectSSE() {{
  const es = new EventSource(`/api/robot/${{SESSION_ID}}/stream`);

  es.addEventListener("text", (e) => {{
    sseRetries = 0;
    const data = JSON.parse(e.data);
    addMessage(data.role, data.content, data.timestamp);
  }});

  es.addEventListener("status", (e) => {{
    sseRetries = 0;
    const data = JSON.parse(e.data);
    addStatusMessage(data.content, data.timestamp);
    updateRobotState();
  }});

  es.addEventListener("warning", (e) => {{
    sseRetries = 0;
    const data = JSON.parse(e.data);
    addWarningMessage(data.content, data.timestamp);
    updateRobotState();
  }});

  es.addEventListener("image", (e) => {{
    const data = JSON.parse(e.data);
    addImageMessage(data.metadata);
  }});

  es.addEventListener("plan", (e) => {{
    const data = JSON.parse(e.data);
    addPlanMessage(data.content, data.timestamp);
    updateRobotState();
  }});

  es.addEventListener("error", (e) => {{
    if (e.data) {{
      try {{
        const data = JSON.parse(e.data);
        addErrorMessage(data.content, data.timestamp);
        updateRobotState();
      }} catch(_) {{}}
    }}
  }});

  es.addEventListener("part_card", (e) => {{
    const data = JSON.parse(e.data);
    addPartCard(data.metadata);
  }});

  es.addEventListener("approval_request", (e) => {{
    const data = JSON.parse(e.data);
    addApprovalButtons(data.metadata);
  }});

  es.addEventListener("approval_response", (e) => {{
    const data = JSON.parse(e.data);
    addMessage(data.role, data.content, data.timestamp);
    updateRobotState();
  }});

  es.addEventListener("ping", () => {{ sseRetries = 0; }});

  es.onerror = () => {{
    es.close();
    sseRetries++;
    if (sseRetries < 5) {{
      setTimeout(connectSSE, 3000);
    }}
  }};
}}

// --- Message rendering ---

function createMsgRow(type, avatarClass, avatarLabel, senderName) {{
  const row = document.createElement("div");
  row.className = `msg-row msg-row-${{type}}`;

  const center = document.createElement("div");
  center.className = "msg-row-center";

  const avatar = document.createElement("div");
  avatar.className = `msg-avatar ${{avatarClass}}`;
  avatar.textContent = avatarLabel;

  const body = document.createElement("div");
  body.className = "msg-body";

  if (senderName) {{
    const sender = document.createElement("div");
    sender.className = "msg-sender";
    sender.textContent = senderName;
    body.appendChild(sender);
  }}

  const content = document.createElement("div");
  content.className = "msg-content";
  body.appendChild(content);

  center.appendChild(avatar);
  center.appendChild(body);
  row.appendChild(center);

  return {{ row, content, body }};
}}

function addMessage(role, content, timestamp) {{
  const isUser = role === "user";
  const {{ row, content: contentEl, body }} = createMsgRow(
    isUser ? "user" : "robot",
    isUser ? "msg-avatar-user" : "msg-avatar-robot",
    isUser ? "Y" : "G1",
    isUser ? "You" : "Robot G1"
  );
  contentEl.innerHTML = escapeHtml(content);
  if (timestamp) {{
    const ts = document.createElement("div");
    ts.className = "msg-timestamp";
    ts.textContent = timestamp;
    body.appendChild(ts);
  }}
  messagesEl.appendChild(row);
  scrollToBottom();
}}

function addStatusMessage(content, timestamp) {{
  const {{ row, content: contentEl, body }} = createMsgRow(
    "status", "msg-avatar-system", "\u2139", null
  );
  contentEl.innerHTML = escapeHtml(content);
  if (timestamp) {{
    const ts = document.createElement("div");
    ts.className = "msg-timestamp";
    ts.style.marginTop = "4px";
    ts.textContent = timestamp;
    contentEl.appendChild(ts);
  }}
  messagesEl.appendChild(row);
  scrollToBottom();
}}

function addPlanMessage(content, timestamp) {{
  const {{ row, content: contentEl }} = createMsgRow(
    "plan", "msg-avatar-robot", "RS", "RoboStore"
  );
  contentEl.innerHTML = escapeHtml(content);
  messagesEl.appendChild(row);
  scrollToBottom();
}}

function addWarningMessage(content, timestamp) {{
  const {{ row, content: contentEl }} = createMsgRow(
    "warning", "msg-avatar-system", "\u26A0", null
  );
  contentEl.innerHTML = escapeHtml(content);
  if (timestamp) {{
    const ts = document.createElement("div");
    ts.className = "msg-timestamp";
    ts.style.marginTop = "4px";
    ts.textContent = timestamp;
    contentEl.appendChild(ts);
  }}
  messagesEl.appendChild(row);
  scrollToBottom();
}}

function addErrorMessage(content, timestamp) {{
  const {{ row, content: contentEl }} = createMsgRow(
    "error", "msg-avatar-system", "\u2716", null
  );
  contentEl.innerHTML = escapeHtml(content);
  messagesEl.appendChild(row);
  scrollToBottom();
}}

function addImageMessage(meta) {{
  const {{ row, content: contentEl }} = createMsgRow(
    "robot", "msg-avatar-robot", "RS", "RoboStore"
  );
  const img = document.createElement("img");
  img.src = meta.src;
  img.alt = meta.alt || "Delivery";
  img.style.maxWidth = "420px";
  img.style.width = "100%";
  img.style.borderRadius = "8px";
  img.style.display = "block";
  img.style.marginTop = "4px";
  contentEl.appendChild(img);
  messagesEl.appendChild(row);
  scrollToBottom();
}}

function addPartCard(meta) {{
  const part = meta.part;
  const tools = part.tools || [];
  const toolsHtml = tools.map(t => `<code>${{escapeHtml(t.name)}}</code>`).join(" ");

  const {{ row, content: contentEl }} = createMsgRow(
    "robot", "msg-avatar-robot", "RS", "RoboStore"
  );
  const card = document.createElement("div");
  card.className = "part-card";
  card.innerHTML = `
    <div class="part-card-header">
      <span class="part-card-cap">${{escapeHtml(meta.capability)}}</span>
      <span class="part-card-step">${{meta.index}}/${{meta.total}}</span>
    </div>
    <div class="part-card-name">${{escapeHtml(part.name)}}</div>
    <div class="part-card-meta">
      <span>${{escapeHtml(part.interface_type || "")}}</span>
      <span>${{part.power_draw_watts || 0}}W</span>
      <span>${{escapeHtml(part.mount_type || "")}}</span>
    </div>
    ${{tools.length ? `<div class="part-card-tools">Tools: ${{toolsHtml}}</div>` : ""}}
    <div class="part-card-price">${{part.price ? "$" + part.price.toFixed(2) : ""}}</div>
  `;
  contentEl.appendChild(card);
  messagesEl.appendChild(row);
  scrollToBottom();
}}

function addApprovalButtons(meta) {{
  const row = document.createElement("div");
  row.className = "approval-row";
  row.id = `approval-${{meta.pid}}`;

  const approveBtn = document.createElement("button");
  approveBtn.className = "btn-approve";
  approveBtn.textContent = "Approve";
  approveBtn.onclick = () => respondApproval(meta.pid, true, row);

  const denyBtn = document.createElement("button");
  denyBtn.className = "btn-deny";
  denyBtn.textContent = "Skip";
  denyBtn.onclick = () => respondApproval(meta.pid, false, row);

  row.appendChild(approveBtn);
  row.appendChild(denyBtn);
  messagesEl.appendChild(row);
  scrollToBottom();
}}

// --- Actions ---

async function sendUnified() {{
  const task = taskInput.value.trim();
  if (!task) return;

  taskInput.value = "";
  sendBtn.disabled = true;

  try {{
    const resp = await fetch(`/api/robot/${{SESSION_ID}}/task`, {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{ task }}),
    }});
    if (!resp.ok) {{
      const err = await resp.json();
      addErrorMessage(err.detail || "Failed to send task");
      sendBtn.disabled = false;
    }}
  }} catch (e) {{
    addErrorMessage("Connection error: " + e.message);
    sendBtn.disabled = false;
  }}
}}

async function respondApproval(pid, approved, rowEl) {{
  // Disable buttons
  rowEl.querySelectorAll("button").forEach(b => b.disabled = true);

  try {{
    await fetch(`/api/robot/${{SESSION_ID}}/approve`, {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{ part_pid: pid, approved }}),
    }});
  }} catch (e) {{
    addErrorMessage("Approval failed: " + e.message);
  }}
}}

function setTask(text) {{
  taskInput.value = text.trim();
  taskInput.focus();
}}

// --- State sync ---

async function updateRobotState() {{
  try {{
    const resp = await fetch(`/api/robot/${{SESSION_ID}}/state`);
    const state = await resp.json();

    // Status badge
    robotStatus = state.status;
    statusBadge.textContent = state.status.toUpperCase().replace("_", " ");
    statusBadge.className = `status-badge status-${{state.status}}`;

    // Enable/disable input
    const canSend = state.status === "idle" || state.status === "error";
    sendBtn.disabled = !canSend;

    // Capabilities
    const baseCaps = ["locomotion", "imu"];
    const allCaps = state.capabilities.map(c => c.id);
    capsEl.innerHTML = allCaps.map(c => {{
      const isInstalled = !baseCaps.includes(c);
      return `<span class="cap-tag ${{isInstalled ? 'installed' : ''}}">${{escapeHtml(c)}}</span>`;
    }}).join("");
    capsCount.textContent = `${{allCaps.length}} capabilities`;

    // Installed parts
    if (state.installed_parts.length > 0) {{
      installedSection.style.display = "block";
      installedParts.innerHTML = state.installed_parts.map(p => `
        <div class="installed-part">
          <div class="installed-part-name">${{escapeHtml(p.name)}}</div>
          <div class="installed-part-cap">${{escapeHtml(p.capability)}}</div>
        </div>
      `).join("");
    }}
  }} catch (e) {{
    // silent
  }}
}}

// --- Helpers ---

function toggleSidebar() {{
  const panel = document.querySelector(".side-panel");
  panel.classList.toggle("collapsed");
}}

function toggleSection(titleEl) {{
  const content = titleEl.nextElementSibling;
  const isOpen = titleEl.getAttribute("data-open") !== "false";
  if (isOpen) {{
    content.classList.add("collapsed");
    titleEl.setAttribute("data-open", "false");
  }} else {{
    content.classList.remove("collapsed");
    titleEl.setAttribute("data-open", "true");
  }}
}}

function escapeHtml(text) {{
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}}

function scrollToBottom() {{
  messagesEl.scrollTop = messagesEl.scrollHeight;
}}

// --- Live sim camera feed ---

const simCamera = document.getElementById("sim-camera");

function refreshSimFrame() {{
  const img = new Image();
  const ts = Date.now();
  img.onload = () => {{
    simCamera.src = img.src;
    setTimeout(refreshSimFrame, 200);
  }};
  img.onerror = () => {{
    setTimeout(refreshSimFrame, 1000);
  }};
  img.src = "/api/sim/frame?t=" + ts;
}}

refreshSimFrame();

// --- Init ---

// Auto-resize textarea
taskInput.addEventListener("input", () => {{
  taskInput.style.height = "auto";
  taskInput.style.height = Math.min(taskInput.scrollHeight, 150) + "px";
}});

taskInput.addEventListener("keydown", (e) => {{
  if (e.key === "Enter" && !e.shiftKey && !sendBtn.disabled) {{
    e.preventDefault();
    sendUnified();
    taskInput.style.height = "auto";
  }}
}});

// Load initial state
(async () => {{
  try {{
    const resp = await fetch(`/api/robot/${{SESSION_ID}}/state`);
    if (resp.ok) {{
      const state = await resp.json();
      state.messages.forEach(m => {{
        if (m.msg_type === "image") addImageMessage(m.metadata);
        else if (m.msg_type === "warning") addWarningMessage(m.content, m.timestamp);
        else if (m.msg_type === "status") addStatusMessage(m.content, m.timestamp);
        else if (m.msg_type === "error") addErrorMessage(m.content, m.timestamp);
        else if (m.msg_type === "plan") addPlanMessage(m.content, m.timestamp);
        else addMessage(m.role, m.content, m.timestamp);
      }});
      updateRobotState();
      connectSSE();
    }} else {{
      addStatusMessage("Robot online. Unitree G1 ready \u2014 send a command to get started.");
    }}
  }} catch(e) {{
    addStatusMessage("Robot online. Unitree G1 ready \u2014 send a command to get started.");
  }}
}})();
</script>

</body>
</html>"""
