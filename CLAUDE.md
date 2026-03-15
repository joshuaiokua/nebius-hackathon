# CLAUDE.md — Agent Context

> Read PLAN.md for full architecture, timeline, and competitive landscape.

## What This Is
**RoboStore** — a self-expanding robot agent platform. Robots get tasks, detect their own capability gaps, shop for hardware modules in a marketplace, auto-generate integration skills, and retry the task. Multi-agent orchestration via OpenClaw makes it parallel and real-time.

## What Already Exists (Josh built this)
- `orchestrator.py` — demo loop: task → detect gaps → search catalog → generate skill → install → retry
- `agent.py` — LLM calls via OpenRouter (Claude Sonnet), gap detection, skill generation
- `catalog.py` — hardware search via Tavily + Adafruit API, LLM-powered module selection
- `db.py` — SQLite + FTS5 catalog database (20 parts, fuzzy search, BM25 ranking)
- `storefront.py` — FastAPI marketplace (RoboStore) with HTML UI + JSON API
- `templates.py` — full dark-theme storefront UI (landing, catalog, detail, purchase pages)
- `schemas.py` — RobotProfile (Unitree A1), CapabilityGap, SelectedModule dataclasses
- `store_catalog.json` — 20 hardware modules across 10+ capabilities
- `skills/` — 4 generated skill YAMLs (depth perception, localization, manipulation, visual perception)
- `catalog.db` — pre-built SQLite database with FTS5 index

## What Needs to Be Built (Gary + Stephen)
1. **Update schemas to Unitree G1** (currently A1)
2. **Connect to MuJoCo** — real simulation environment for G1
3. **Multi-agent orchestration via OpenClaw** — SCOUT, PLANNER, SAFETY running in parallel
4. **Wire sim state into the self-expanding loop** — when robot detects a gap, the sim validates whether the new skill actually works
5. **Nebius Token Factory integration** — switch from OpenRouter to Nebius for inference (Qwen2-VL-72B for vision, Qwen3-235B for planning)

## Team & Ownership

### Gary + Stephen (backend/sim/orchestration)
- `agents/` — OpenClaw multi-agent orchestration (SCOUT, PLANNER, SAFETY)
- `sim/` — MuJoCo G1 environment
- `orchestrator.py` — enhance with multi-agent parallel execution
- `agent.py` — add Nebius Token Factory, vision model support
- `schemas.py` — update to G1

### Josh (frontend/db/product)
- `storefront.py` — marketplace UI and API
- `templates.py` — UI design and polish
- `db.py` — catalog database
- `store_catalog.json` — product catalog
- `README.md` — public-facing docs

## Key APIs
- OpenRouter: `https://openrouter.ai/api/v1/chat/completions` (OPENROUTER_API_KEY)
- Nebius Token Factory: `https://api.studio.nebius.com/v1/chat/completions` (NEBIUS_API_KEY)
- Tavily: `https://api.tavily.com/search` (TAVILY_API_KEY)
- Adafruit: `https://www.adafruit.com/api/products` (no key needed)

## Rules
- Push to main. No branches. Small commits every 30 min.
- If architecture changes, update PLAN.md and CLAUDE.md immediately.
- Checkpoints: 2:30 PM, 4:00 PM, 5:30 PM.
- Don't modify files outside your ownership zone without coordinating.

## MuJoCo G1 Simulation Reference

### Setup
```bash
pip install mujoco
# G1 23-DOF model (Stephen's unitree_ros):
# mujoco_sims/unitree_ros/robots/g1_description/g1_23dof.xml
```

### G1 Specs in MuJoCo (23-DOF variant)
- 23 DOF (degrees of freedom) — **NOT** the 29-DOF menagerie model
- Joint breakdown:
  - **Legs (0-11):** 6 per leg — 3 hip (pitch/roll/yaw) + 1 knee + 2 ankle (pitch/roll)
  - **Waist (12):** yaw only (1 DOF)
  - **Arms (13-22):** 5 per arm — 3 shoulder (pitch/roll/yaw) + 1 elbow + 1 extra
  - No wrists, no dexterous hands
- `data.qpos` — joint positions (array, length = model.nq)
- `data.qvel` — joint velocities (array, length = model.nv)
- `data.ctrl` — control inputs to actuators (23 elements)
- Position actuators on all joints

### Joint Groups (PD gains from Unitree reference)
- **Legs (0-11):** Hip KP=150/KD=2, Knee KP=300/KD=4, Ankle KP=40/KD=2
- **Waist (12):** KP=250/KD=5
- **Arms (13-22):** Shoulders KP=100/KD=2-5, Elbows KP=20-40/KD=1-2

### State Extraction Pattern
```python
import mujoco
import numpy as np

model = mujoco.MjModel.from_xml_path("mujoco_sims/unitree_ros/robots/g1_description/g1_23dof.xml")
data = mujoco.MjData(model)

# Step simulation
mujoco.mj_step(model, data)

# Extract state
state = {
    "time": data.time,
    "qpos": data.qpos.tolist(),        # joint positions
    "qvel": data.qvel.tolist(),        # joint velocities
    "position": data.qpos[:3].tolist(), # root xyz
    "orientation": data.qpos[3:7].tolist(), # root quaternion
    "velocity": data.qvel[:3].tolist(), # root linear velocity
    "angular_vel": data.qvel[3:6].tolist(), # root angular velocity
}
```

### Offscreen Rendering (headless, for dashboard)
```python
renderer = mujoco.Renderer(model, height=480, width=640)
renderer.update_scene(data)
frame = renderer.render()  # numpy RGB array
```

### Actions the Orchestrator Can Command
- `walk_forward` — drive hip pitch + knee joints
- `walk_backward` — reverse
- `turn_left` / `turn_right` — differential hip yaw
- `stop` / `stand` — neutral joint targets
- `wave` — right shoulder raise + extend
- `reach_left` / `reach_right` — arm extension

Each action maps to setting `data.ctrl[joint_indices]` to target positions (23 elements).

### SceneBuilder — LLM-Powered Scene Generation
`agents/scene_builder.py` — takes natural language prompts and generates valid MuJoCo MJCF XML body/geom elements via Nebius LLM. The orchestrator's `scene_command()` method accepts NL like "build a staircase of 10 steps" and sends generated MJCF to SimInterface for injection. Stephen handles the actual XML injection into the running sim.
