# Nebius.Build SF Hackathon — March 15, 2026

> **Track:** Sentient AI → Scalable Swarms
> **Event:** SHACK15, San Francisco | Build: 1:30–6:30 PM | Demos: 6:30 PM
> **Prize:** $35K grand prize

## Project: Parallel Agent Swarm for Robot Autonomy

### The Pitch (60 seconds)
> "One brain per robot is a toy. Real autonomy is a team — eyes, brain, and safety running simultaneously. We orchestrate specialized AI agents through OpenClaw to control a Unitree G1. The scout never stops watching. The planner thinks 3 moves ahead. The safety agent simulates every action before it happens. This is how we build autonomous inspection robots at Drover Labs."

---

## Architecture

```
                    ┌─────────────────────────────┐
                    │   OpenClaw Orchestrator      │
                    │   (coordinates all agents)   │
                    └──────────┬──────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
    ┌─────▼─────┐      ┌──────▼──────┐     ┌──────▼──────┐
    │  👁 SCOUT  │      │  🧠 PLANNER │     │  ⚠️ SAFETY  │
    │  (Vision)  │      │  (Strategy) │     │  (Guardian) │
    │            │      │             │     │             │
    │ Qwen2-VL   │      │ Qwen3-235B  │     │ MuJoCo      │
    │ "what do   │      │ "given what │     │ rollouts    │
    │  I see?"   │      │  we see,    │     │ "will this  │
    │            │      │  do what?"  │     │  fall over?"|
    └─────┬─────┘      └──────┬──────┘     └──────┬──────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                        ┌──────▼──────┐
                        │  🤖 EXECUTOR │
                        │  (G1 MuJoCo) │
                        └─────────────┘
```

### Key Differentiator
Other teams run sequentially: see → think → act → repeat.
We run in **parallel**: SCOUT continuously analyzes, PLANNER reasons ahead, SAFETY simulates proposed actions concurrently. EXECUTOR acts only when PLANNER + SAFETY agree.

---

## Team

| | **Gary + Stephen** | **Josh** |
|---|---|---|
| **Background** | Gary: CEO Drover Labs, robotics/autonomy, NASA. Stephen: PhD scientist, hardware/technical | Fullstack dev, marketing/story |
| **Owns** | OpenClaw orchestration, MuJoCo env, all agents (SCOUT/PLANNER/SAFETY), sim rollouts, model optimization | Frontend marketplace UI, agent dashboard, DB, pitch deck, demo script, README |
| **Directories** | `agents/`, `sim/`, `orchestrator/` | `frontend/`, `db/`, `README.md` |

---

## Hour-by-Hour Build Plan

### 🔧 1:30–2:30 — Foundations (all parallel, zero dependencies)

| Gary | Stephen | Josh |
|---|---|---|
| Install/configure OpenClaw on local or Nebius VM | Spin up Nebius GPU VM, get MuJoCo running with G1 model | Scaffold frontend marketplace UI (product landing + dashboard) |
| Define multi-agent workflow: spawn SCOUT, PLANNER, SAFETY as OpenClaw sessions | Set up SSH access for all 3 team members, distribute API keys | Design 4-panel agent dashboard: Scout feed, Planner reasoning, Safety status, Robot view |
| Get first agent talking to Nebius Token Factory (Qwen3-235B) through OpenClaw | Extract G1 state as JSON from MuJoCo (position, velocity, orientation, stability) | Draft pitch outline — problem, product vision (marketplace), demo, Drover credibility |

**✅ Checkpoint 2:30:** MuJoCo G1 running. OpenClaw spawns agents. Josh has dashboard + marketplace skeleton.

---

### ⚡ 2:30–4:00 — Wire It Together

| Gary | Stephen | Josh |
|---|---|---|
| Build orchestrator: SCOUT + SAFETY run continuously, PLANNER triggers on new observations | Build SAFETY agent: fork MuJoCo state → parallel rollouts with noise → stability score + risk level | Connect dashboard to agents via WebSocket/SSE — live stream each agent's output |
| Define decision protocol: PLANNER proposes → SAFETY validates → EXECUTOR fires only if risk < threshold | Build SCOUT: camera frame → Qwen2-VL via Token Factory → scene description. Tune prompts for actionable output | Build marketplace UI — browse agent "skills", plug-and-play modules, product story |
| Handle conflict resolution: SAFETY vetoes PLANNER → re-plan loop | Add obstacle spawning in MuJoCo for demo scenarios | Start pitch slides (5 max) — frame as both hackathon demo AND product |

**✅ Checkpoint 4:00:** Full loop works E2E. Command → SCOUT sees → PLANNER reasons → SAFETY checks → G1 moves (or re-plans). Dashboard shows it live. Marketplace UI tells the product story.

---

### 🎯 4:00–5:30 — Demo Scenario + Polish

| Gary | Stephen | Josh |
|---|---|---|
| Build scripted demo: G1 walks → obstacle detected → SAFETY vetoes → PLANNER re-routes → resumes | Optimize latency — SCOUT and SAFETY real-time. Cache sim states, batch rollouts | Make everything beautiful — dark theme, agent panels (🟢 SCOUT, 🔵 PLANNER, 🔴 SAFETY), marketplace polish |
| Add 2-3 NL commands ("walk to the door", "check if safe to turn left", "inspect that area") | Record backup demo video | Finalize pitch: demo + product vision + Drover credibility. Practice 60s + 3min versions |
| Test full demo 3x, fix broken edges | Stress test: VLM slow? → timeout + fallback. Everything dangerous? → confidence calibration | Prepare exact demo script — commands to type, what to say at each moment |

**✅ Checkpoint 5:30:** Demo runs clean 3x. Backup video recorded. Pitch rehearsed.

---

### 🏁 5:30–6:30 — Final Prep

- Run demo 2 more times on presentation machine
- Josh: full dry-run pitch (time it — under 3 minutes)
- Verify Nebius API keys, WiFi, dashboard URL, marketplace URL
- Gary: prep judge Q&A — "how vs ROS?", "why OpenClaw?", "latency?", "what's the business model?"
- Stephen: prep technical deep-dives — MuJoCo fidelity, rollout physics, VLM accuracy

---

## Message Protocol

```json
// SCOUT → Orchestrator (every 500ms)
{
  "agent": "scout",
  "frame_id": 42,
  "scene": "clear path ahead, chair 2m right",
  "objects": [{"type": "chair", "distance": 2.1, "bearing": "right"}],
  "confidence": 0.92
}

// PLANNER → Orchestrator (on new scout data)
{
  "agent": "planner",
  "action": "walk_forward",
  "reasoning": "path clear, objective ahead",
  "steps_ahead": ["walk_forward", "turn_left", "approach_target"],
  "confidence": 0.87
}

// SAFETY → Orchestrator (on proposed action)
{
  "agent": "safety",
  "action": "walk_forward",
  "rollouts": 5,
  "stability_rate": 0.95,
  "risk": "LOW",
  "approved": true
}

// Orchestrator → EXECUTOR (only if safety.approved == true)
{
  "execute": "walk_forward"
}
```

---

## Tech Stack

| Component | Tool |
|---|---|
| Orchestration | OpenClaw sessions (spawn + coordinate) |
| Simulation | MuJoCo + mujoco_menagerie G1 model |
| Vision (SCOUT) | Qwen2-VL-72B via Nebius Token Factory |
| Planning (PLANNER) | Qwen3-235B-A22B via Nebius Token Factory |
| Safety (SAFETY) | MuJoCo parallel rollouts (on Nebius VM) |
| Dashboard | Single HTML page, WebSocket, dark theme |
| Collab | GitHub repo, all SSH into same Nebius VM |

---

## Competitive Landscape (as of 11:30 AM)

| Team | Project | Our Edge |
|---|---|---|
| **galileo-ml** (CHAI) | G1 companion — Hindi speech, obstacle clearing, VLM + state machine | Single agent, sequential. We're parallel + multi-agent |
| **TheApexWu** (NIWA) | Zero-training manipulation via in-context RL, critic + artist agents | Cool concept but no orchestration layer, 2 agents only |
| **0-5-blood-prince** (RoboMind) | LLM-orchestrated G1 + predictive rollouts | Closest competitor — but single LLM, no parallel agents, no OpenClaw |
| **marioToribi0** (Msiruote) | Robot tour guide, voice + vision | Early stage, just README |

---

## Why This Wins

1. **Only multi-agent project** — everyone else is single-LLM
2. **Uses the sponsor's product** (OpenClaw) as core infrastructure
3. **Parallel, not sequential** — visually obvious in dashboard
4. **Real-world credible** — "we build autonomous robots, this is how it actually works"
5. **Josh's dashboard** will be the most polished demo on stage
6. **Drover Labs story** — not weekend hobbyists, actual robotics company

---

## Resources

- Nebius Token Factory: https://tokenfactory.nebius.com/
- Nebius Cloud Console: https://console.nebius.com
- MuJoCo Menagerie (G1 model): https://github.com/google-deepmind/mujoco_menagerie
- MuJoCo Playground: https://github.com/google-deepmind/mujoco_playground
- Solo CLI docs: https://github.com/GetSoloTech/solo-cli
- OpenClaw docs: https://docs.openclaw.ai
- Unitree G1 MuJoCo RL: https://github.com/unitreerobotics/unitree_rl_mjlab
