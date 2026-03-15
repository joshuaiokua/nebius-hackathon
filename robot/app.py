"""Robot control panel — chat interface for giving tasks, viewing status, approving purchases."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from db import get_part, get_part_full, recommend_for_task, search_parts, init_db, DB_PATH
from schemas import RobotProfile
from robot.templates import render_control_panel
from agents.orchestrator import AsyncOrchestrator


# ---------- Session state ----------


@dataclass
class Message:
    role: str          # "user", "robot", "system"
    content: str
    timestamp: str = ""
    msg_type: str = "text"  # "text", "status", "approval_request", "approval_response", "error", "plan", "part_card"
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%H:%M:%S")


@dataclass
class RobotSession:
    session_id: str = ""
    profile: RobotProfile = field(default_factory=RobotProfile)
    messages: list[Message] = field(default_factory=list)
    current_task: str = ""
    status: str = "idle"  # "idle", "planning", "searching", "awaiting_approval", "installing", "executing", "error"
    pending_approval: dict = field(default_factory=dict)
    installed_parts: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.session_id:
            self.session_id = str(uuid.uuid4())[:8]


SESSIONS: dict[str, RobotSession] = {}
SSE_QUEUES: dict[str, asyncio.Queue] = {}


def _get_or_create_session(session_id: str | None = None) -> RobotSession:
    if session_id and session_id in SESSIONS:
        return SESSIONS[session_id]
    session = RobotSession()
    session.messages.append(Message(
        role="system",
        content="Robot online. Unitree G1 ready — assign a task to begin.",
        msg_type="status",
    ))
    SESSIONS[session.session_id] = session
    SSE_QUEUES[session.session_id] = asyncio.Queue()
    return session


async def _emit(session_id: str, msg: Message) -> None:
    """Add a message to the session and push to SSE queue."""
    if session_id in SESSIONS:
        SESSIONS[session_id].messages.append(msg)
    if session_id in SSE_QUEUES:
        await SSE_QUEUES[session_id].put(msg)


# ---------- App ----------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if not DB_PATH.exists():
        init_db()
    yield


app = FastAPI(
    title="Robot Control Panel",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------- SSE stream ----------


@app.get("/api/robot/{session_id}/stream")
async def event_stream(session_id: str, request: Request):
    """SSE endpoint for real-time robot status updates."""
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")

    queue = SSE_QUEUES[session_id]

    async def generate():
        while True:
            if await request.is_disconnected():
                break
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30)
                yield {
                    "event": msg.msg_type,
                    "data": json.dumps({
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp,
                        "msg_type": msg.msg_type,
                        "metadata": msg.metadata,
                    }),
                }
            except asyncio.TimeoutError:
                # Send keepalive
                yield {"event": "ping", "data": ""}

    return EventSourceResponse(generate())


# ---------- API endpoints ----------


class TaskRequest(BaseModel):
    task: str


@app.post("/api/robot/{session_id}/task")
async def assign_task(session_id: str, req: TaskRequest):
    """Assign a task to the robot. Triggers the planning + gap detection pipeline."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status not in ("idle", "error"):
        raise HTTPException(409, f"Robot is busy: {session.status}")

    session.current_task = req.task
    session.status = "planning"

    # Run the pipeline in the background
    asyncio.create_task(_run_task_pipeline(session))

    return {"status": "accepted", "task": req.task}


class ApprovalResponse(BaseModel):
    approved: bool
    part_pid: str


@app.post("/api/robot/{session_id}/approve")
async def approve_purchase(session_id: str, req: ApprovalResponse):
    """Approve or deny a part purchase."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status != "awaiting_approval":
        raise HTTPException(409, "No pending approval")

    session.pending_approval = {"approved": req.approved, "pid": req.part_pid}
    return {"status": "received", "approved": req.approved}


@app.get("/api/robot/{session_id}/state")
async def get_robot_state(session_id: str):
    """Get the full robot session state."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "session_id": session.session_id,
        "status": session.status,
        "current_task": session.current_task,
        "capabilities": session.profile.capabilities,
        "installed_parts": session.installed_parts,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp,
                "msg_type": m.msg_type,
                "metadata": m.metadata,
            }
            for m in session.messages
        ],
    }


@app.post("/api/robot/new")
async def new_session():
    """Create a new robot session."""
    session = _get_or_create_session()
    return {"session_id": session.session_id}


# ---------- Task pipeline (runs in background) ----------


async def _run_task_pipeline(session: RobotSession) -> None:
    """Run the full self-expanding pipeline for a task."""
    sid = session.session_id

    try:
        # 1. User message
        await _emit(sid, Message(
            role="user",
            content=session.current_task,
        ))

        # 2. Acknowledge
        await _emit(sid, Message(
            role="robot",
            content=f"Task received. Analyzing requirements...",
            msg_type="status",
        ))
        await asyncio.sleep(0.8)

        # 3. Show current capabilities
        cap_names = [c["id"] for c in session.profile.capabilities]
        await _emit(sid, Message(
            role="robot",
            content=f"Current capabilities: {', '.join(cap_names)}",
            msg_type="status",
        ))
        await asyncio.sleep(0.5)

        # 4. Search for recommended parts (gap detection via catalog)
        session.status = "searching"
        await _emit(sid, Message(
            role="robot",
            content="Searching catalog for required hardware...",
            msg_type="status",
        ))
        await asyncio.sleep(0.5)

        recommendations = recommend_for_task(
            task=session.current_task,
            current_capabilities=cap_names,
            power_budget_w=session.profile.power_budget_w,
            platform=session.profile.platform,
        )

        if not recommendations:
            await _emit(sid, Message(
                role="robot",
                content="All required capabilities are already available. Ready to execute.",
                msg_type="status",
            ))
            session.status = "idle"
            return

        # 5. Show the plan
        cap_list = [r["capability"] for r in recommendations]
        await _emit(sid, Message(
            role="robot",
            content=f"Found {len(recommendations)} capability gap(s): {', '.join(cap_list)}",
            msg_type="plan",
            metadata={"gaps": cap_list},
        ))
        await asyncio.sleep(0.5)

        # 6. For each recommendation, ask for approval
        for i, rec in enumerate(recommendations):
            part = rec["recommended"]
            cap = rec["capability"]

            await _emit(sid, Message(
                role="robot",
                content="",
                msg_type="part_card",
                metadata={
                    "index": i + 1,
                    "total": len(recommendations),
                    "capability": cap,
                    "part": part,
                    "alternatives_count": len(rec.get("alternatives", [])),
                },
            ))

            # Ask for approval
            session.status = "awaiting_approval"
            session.pending_approval = {}

            await _emit(sid, Message(
                role="robot",
                content=f"Permission to order {part['name']} for ${part['price']:.2f}?",
                msg_type="approval_request",
                metadata={"pid": part["pid"], "name": part["name"], "price": part["price"], "capability": cap},
            ))

            # Wait for user approval
            while not session.pending_approval:
                await asyncio.sleep(0.3)

            approved = session.pending_approval.get("approved", False)

            if approved:
                await _emit(sid, Message(
                    role="user",
                    content=f"Approved: {part['name']}",
                    msg_type="approval_response",
                    metadata={"approved": True},
                ))

                # Simulate purchase + install
                session.status = "installing"
                await _emit(sid, Message(
                    role="robot",
                    content=f"Ordering {part['name']}...",
                    msg_type="status",
                ))
                await asyncio.sleep(1.0)

                # Get full part data with skill YAML
                full_part = get_part_full(part["pid"])
                if full_part and full_part.get("skill_yaml"):
                    try:
                        skill = yaml.safe_load(full_part["skill_yaml"])
                        if skill:
                            tool_names = [t["name"] for t in skill.get("agent_tools", [])]
                            session.profile.add_capability({
                                "id": skill["skill_id"],
                                "description": f"{skill['hardware']} — tools: {tool_names}",
                            })
                            session.installed_parts.append({
                                "pid": part["pid"],
                                "name": part["name"],
                                "capability": cap,
                                "skill_id": skill["skill_id"],
                                "tools": tool_names,
                            })

                            # Show install info
                            install = skill.get("installation", {})
                            if install.get("physical"):
                                await _emit(sid, Message(
                                    role="robot",
                                    content=f"Physical install: {install['physical']}",
                                    msg_type="status",
                                ))
                                await asyncio.sleep(0.5)

                            sw_steps = install.get("software", [])
                            if sw_steps:
                                await _emit(sid, Message(
                                    role="robot",
                                    content=f"Running: {', '.join(sw_steps)}",
                                    msg_type="status",
                                ))
                                await asyncio.sleep(0.8)

                            context_update = skill.get("agent_context_update", "").strip()
                            await _emit(sid, Message(
                                role="robot",
                                content=f"Installed {cap}: {', '.join(tool_names)} now available.",
                                msg_type="status",
                                metadata={"tools": tool_names, "context_update": context_update},
                            ))
                    except Exception as e:
                        await _emit(sid, Message(
                            role="robot",
                            content=f"Skill ingestion warning: {e}",
                            msg_type="error",
                        ))
                else:
                    await _emit(sid, Message(
                        role="robot",
                        content=f"Part data unavailable for {part['name']}, skipping install.",
                        msg_type="error",
                    ))
            else:
                await _emit(sid, Message(
                    role="user",
                    content=f"Denied: {part['name']}",
                    msg_type="approval_response",
                    metadata={"approved": False},
                ))
                await _emit(sid, Message(
                    role="robot",
                    content=f"Skipping {cap}. Will proceed without this capability.",
                    msg_type="status",
                ))

            session.pending_approval = {}
            await asyncio.sleep(0.3)

        # 7. Final status
        final_caps = [c["id"] for c in session.profile.capabilities]
        await _emit(sid, Message(
            role="robot",
            content=f"Setup complete. Capabilities: {', '.join(final_caps)}",
            msg_type="status",
        ))
        await asyncio.sleep(0.3)

        await _emit(sid, Message(
            role="robot",
            content=f"Ready to execute: {session.current_task}",
            msg_type="plan",
            metadata={"capabilities": final_caps},
        ))

        session.status = "idle"

    except Exception as e:
        session.status = "error"
        await _emit(sid, Message(
            role="robot",
            content=f"Pipeline error: {e}",
            msg_type="error",
        ))


# ---------- Multi-agent orchestrator ----------

_orchestrator = AsyncOrchestrator()


class CommandRequest(BaseModel):
    text: str


@app.post("/api/command")
async def run_command(req: CommandRequest):
    """Execute a natural language command through the multi-agent orchestrator.

    Routes to SCOUT → PLANNER → SAFETY → EXECUTOR pipeline or scene building
    depending on the command. Returns the full result when complete.
    """
    result = await _orchestrator.command(req.text)
    return result


@app.get("/api/command/stream")
async def stream_command(request: Request, text: str):
    """SSE endpoint that streams agent outputs in real-time.

    Connect with EventSource, passing ?text=<command>. Each event contains
    the agent name, message, and optional metadata as JSON.

    Event format:
        event: agent
        data: {"agent": "SCOUT", "message": "...", "metadata": {...}}
    """
    queue: asyncio.Queue = asyncio.Queue()

    async def on_event(agent: str, message: str, metadata: dict) -> None:
        await queue.put({"agent": agent, "message": message, "metadata": metadata})

    async def run_in_background() -> None:
        try:
            result = await _orchestrator.command(text, on_event=on_event)
            await queue.put({"agent": "DONE", "message": "complete", "metadata": result})
        except Exception as e:
            await queue.put({"agent": "ERROR", "message": str(e), "metadata": {}})

    # Start the orchestrator in the background
    task = asyncio.create_task(run_in_background())

    async def generate():
        while True:
            if await request.is_disconnected():
                task.cancel()
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                yield {
                    "event": "agent",
                    "data": json.dumps(event),
                }
                if event["agent"] == "DONE":
                    break
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": ""}

    return EventSourceResponse(generate())


# ---------- Live sim camera feed ----------


@app.get("/api/sim/frame")
async def sim_frame():
    """Return the current MuJoCo camera frame as a JPEG image."""
    from fastapi.responses import Response

    try:
        img_bytes = await _orchestrator.sim.get_camera_frame_bytes()
        return Response(
            content=img_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "no-store"},
        )
    except Exception as e:
        return Response(content=str(e), status_code=500)


@app.get("/api/sim/state")
async def sim_state():
    """Return the current MuJoCo sim state as JSON."""
    try:
        state = await _orchestrator.sim.get_state()
        return state
    except Exception as e:
        return {"error": str(e)}


# ---------- HTML pages ----------


@app.get("/", response_class=HTMLResponse)
async def control_panel():
    session = _get_or_create_session()
    return render_control_panel(session.session_id)


@app.get("/{session_id}", response_class=HTMLResponse)
async def control_panel_session(session_id: str):
    if session_id not in SESSIONS:
        session = _get_or_create_session()
        return render_control_panel(session.session_id)
    return render_control_panel(session_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("robot.app:app", host="0.0.0.0", port=8001, reload=True)
