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

.logo {{
  font-size: 18px;
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
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}}

.messages::-webkit-scrollbar {{ width: 6px; }}
.messages::-webkit-scrollbar-track {{ background: transparent; }}
.messages::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}

.msg {{
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  animation: fadeIn 0.2s ease;
}}

@keyframes fadeIn {{
  from {{ opacity: 0; transform: translateY(6px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

.msg-user {{
  align-self: flex-end;
  background: var(--accent);
  color: #050507;
  border-bottom-right-radius: 4px;
}}

.msg-robot {{
  align-self: flex-start;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
}}

.msg-system {{
  align-self: center;
  background: transparent;
  color: var(--text-dim);
  font-size: 12px;
  padding: 4px 0;
}}

.msg-status {{
  align-self: flex-start;
  background: var(--surface-2);
  border-left: 3px solid var(--blue);
  border-radius: 4px 12px 12px 4px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
}}

.msg-warning {{
  align-self: flex-start;
  background: var(--warning-bg);
  border-left: 3px solid var(--warning);
  border-radius: 4px 12px 12px 4px;
  color: var(--warning);
  font-size: 14px;
  font-weight: 500;
}}

.msg-error {{
  align-self: flex-start;
  background: var(--danger-bg);
  border-left: 3px solid var(--danger);
  border-radius: 4px 12px 12px 4px;
  color: var(--danger);
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
}}

.msg-plan {{
  align-self: flex-start;
  background: var(--accent-bg);
  border-left: 3px solid var(--accent);
  border-radius: 4px 12px 12px 4px;
  color: var(--accent);
  font-size: 14px;
  font-weight: 500;
}}

.msg-timestamp {{
  font-size: 10px;
  color: var(--text-dim);
  margin-top: 2px;
  font-family: 'JetBrains Mono', monospace;
}}

/* ---------- Part card ---------- */

.part-card {{
  align-self: flex-start;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  max-width: 420px;
  width: 100%;
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
  align-self: flex-start;
  display: flex;
  gap: 10px;
  padding: 4px 0;
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

.input-bar {{
  padding: 16px 20px;
  background: var(--surface);
  border-top: 1px solid var(--border);
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}}

.input-bar input {{
  flex: 1;
  padding: 10px 16px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--text);
  font-size: 14px;
  font-family: 'Inter', sans-serif;
  outline: none;
  transition: border-color 0.15s;
}}

.input-bar input:focus {{
  border-color: var(--accent);
}}

.input-bar input::placeholder {{
  color: var(--text-dim);
}}

.input-bar button {{
  padding: 10px 20px;
  background: var(--accent);
  color: #050507;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  font-family: 'Inter', sans-serif;
  transition: all 0.15s;
  white-space: nowrap;
}}

.input-bar button:hover {{ background: #86efac; }}
.input-bar button:disabled {{ opacity: 0.4; cursor: not-allowed; }}

/* ---------- Side panel ---------- */

.side-panel {{
  width: 300px;
  background: var(--surface);
  border-left: 1px solid var(--border);
  padding: 20px;
  overflow-y: auto;
  flex-shrink: 0;
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
  padding: 12px;
  background: var(--surface);
  border-top: 1px solid var(--border);
  height: 280px;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}}

/* ---------- Responsive ---------- */

@media (max-width: 768px) {{
  .side-panel {{ display: none; }}
  .msg {{ max-width: 95%; }}
  .agent-dashboard {{ grid-template-columns: 1fr; grid-template-rows: repeat(4, 1fr); }}
}}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <div class="logo">Robot Control</div>
    <div class="status-badge status-idle" id="status-badge">IDLE</div>
  </div>
  <div class="header-right">
    <span class="caps-count" id="caps-count">2 capabilities</span>
    <a href="http://localhost:8000/store" target="_blank" class="store-link">Parts Store &rarr;</a>
  </div>
</div>

<div class="main">
  <div class="chat-panel">
    <div class="messages" id="messages"></div>
    <div class="input-bar">
      <input type="text" id="task-input" placeholder="Give the robot a command... (e.g. walk forward 5 meters, pick up the red box)"
             autocomplete="off">
      <button id="send-btn" onclick="sendUnified()">Send</button>
    </div>
    <div class="sim-viewer">
      <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
        <div style="width:8px; height:8px; border-radius:50%; background:#a78bfa;"></div>
        <span style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#a78bfa; font-family:'JetBrains Mono',monospace;">SIM VIEW</span>
      </div>
      <div style="flex:1; display:flex; align-items:center; justify-content:center; overflow:hidden; background:#000; border-radius:8px;">
        <img id="sim-camera" src="/api/sim/frame" alt="MuJoCo G1"
             style="max-width:100%; max-height:100%; object-fit:contain;">
      </div>
    </div>
  </div>

  <div class="side-panel">
    <div class="side-section">
      <div class="side-title">Robot Profile</div>
      <div class="robot-info">
        <div><strong>ID:</strong> unitree-g1-sim</div>
        <div><strong>Platform:</strong> Unitree G1</div>
        <div><strong>DOF:</strong> 23 joints</div>
        <div><strong>Power:</strong> 15W budget</div>
        <div><strong>Sim:</strong> MuJoCo</div>
      </div>
    </div>

    <div class="side-section">
      <div class="side-title">Capabilities</div>
      <div id="capabilities">
        <span class="cap-tag">locomotion</span>
        <span class="cap-tag">imu</span>
      </div>
    </div>

    <div class="side-section" id="installed-section" style="display:none">
      <div class="side-title">Installed Parts</div>
      <div id="installed-parts"></div>
    </div>

    <div class="side-section">
      <div class="side-title">Try These</div>
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

function addMessage(role, content, timestamp) {{
  const div = document.createElement("div");
  div.className = `msg msg-${{role}}`;
  div.innerHTML = escapeHtml(content);
  if (timestamp) {{
    const ts = document.createElement("div");
    ts.className = "msg-timestamp";
    ts.textContent = timestamp;
    div.appendChild(ts);
  }}
  messagesEl.appendChild(div);
  scrollToBottom();
}}

function addStatusMessage(content, timestamp) {{
  const div = document.createElement("div");
  div.className = "msg msg-status";
  div.innerHTML = escapeHtml(content);
  if (timestamp) {{
    const ts = document.createElement("div");
    ts.className = "msg-timestamp";
    ts.textContent = timestamp;
    div.appendChild(ts);
  }}
  messagesEl.appendChild(div);
  scrollToBottom();
}}

function addPlanMessage(content, timestamp) {{
  const div = document.createElement("div");
  div.className = "msg msg-plan";
  div.innerHTML = escapeHtml(content);
  messagesEl.appendChild(div);
  scrollToBottom();
}}

function addWarningMessage(content, timestamp) {{
  const div = document.createElement("div");
  div.className = "msg msg-warning";
  div.innerHTML = escapeHtml(content);
  if (timestamp) {{
    const ts = document.createElement("div");
    ts.className = "msg-timestamp";
    ts.textContent = timestamp;
    div.appendChild(ts);
  }}
  messagesEl.appendChild(div);
  scrollToBottom();
}}

function addErrorMessage(content, timestamp) {{
  const div = document.createElement("div");
  div.className = "msg msg-error";
  div.innerHTML = escapeHtml(content);
  messagesEl.appendChild(div);
  scrollToBottom();
}}

function addImageMessage(meta) {{
  const div = document.createElement("div");
  div.className = "msg msg-robot";
  div.style.padding = "6px";
  div.style.maxWidth = "420px";
  const img = document.createElement("img");
  img.src = meta.src;
  img.alt = meta.alt || "Delivery";
  img.style.width = "100%";
  img.style.borderRadius = "8px";
  img.style.display = "block";
  div.appendChild(img);
  messagesEl.appendChild(div);
  scrollToBottom();
}}

function addPartCard(meta) {{
  const part = meta.part;
  const tools = part.tools || [];
  const toolsHtml = tools.map(t => `<code>${{escapeHtml(t.name)}}</code>`).join(" ");

  const div = document.createElement("div");
  div.className = "part-card";
  div.innerHTML = `
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
  messagesEl.appendChild(div);
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
const simFps = document.getElementById("sim-fps");
let frameCount = 0;
let lastFpsTime = Date.now();

function refreshSimFrame() {{
  const img = new Image();
  const ts = Date.now();
  img.onload = () => {{
    simCamera.src = img.src;
    frameCount++;
    const elapsed = ts - lastFpsTime;
    if (elapsed > 2000) {{
      const fps = Math.round((frameCount / elapsed) * 1000);
      simFps.textContent = fps + " fps";
      frameCount = 0;
      lastFpsTime = ts;
    }}
    setTimeout(refreshSimFrame, 200);
  }};
  img.onerror = () => {{
    setTimeout(refreshSimFrame, 1000);
  }};
  img.src = "/api/sim/frame?t=" + ts;
}}

refreshSimFrame();

// --- Init ---

taskInput.addEventListener("keydown", (e) => {{
  if (e.key === "Enter" && !sendBtn.disabled) sendUnified();
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
      addStatusMessage("Robot online. Unitree G1 ready — use the SIM bar below to send commands.");
    }}
  }} catch(e) {{
    addStatusMessage("Robot online. Unitree G1 ready — use the SIM bar below to send commands.");
  }}
}})();
</script>

</body>
</html>"""
