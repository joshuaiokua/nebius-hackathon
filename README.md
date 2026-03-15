# RoboStore — Self-Expanding Robot Agent Platform

> **Nebius.Build SF Hackathon — March 15, 2026**
> Track: Sentient AI → Scalable Swarms

## What It Does

Robots shouldn't need humans to tell them what hardware they're missing.

**RoboStore** is a self-expanding robot agent that:
1. **Gets a task** — "Navigate to the red box, pick it up, bring it back"
2. **Detects its own gaps** — "I can walk, but I can't see or grab things"
3. **Shops for hardware** — searches a real parts catalog for cameras, grippers, sensors
4. **Auto-generates integration skills** — YAML skill files with install instructions, ROS2 packages, and agent tools
5. **Installs and retries** — robot expands its own capabilities and re-attempts the task

Multiple AI agents run **in parallel** via OpenClaw orchestration:
- 👁 **SCOUT** — continuous vision, scene understanding (Qwen2-VL-72B)
- 🧠 **PLANNER** — task decomposition, multi-step reasoning (Qwen3-235B)
- ⚠️ **SAFETY** — parallel simulation rollouts, risk assessment

All running on **Nebius GPU compute** with **Token Factory** for inference.

## Architecture

```
User gives task
       │
       ▼
┌──────────────┐     ┌──────────────────────────────┐
│  Gap Detector │────▶│  RoboStore Marketplace        │
│  (LLM)       │     │  20+ hardware modules          │
└──────┬───────┘     │  Real-time Tavily + Adafruit   │
       │             │  FTS5 fuzzy search + BM25       │
       │             └──────────────┬───────────────────┘
       │                            │
       ▼                            ▼
┌──────────────┐     ┌──────────────────────────────┐
│  Skill Gen   │────▶│  Auto-generated YAML skills   │
│  (LLM)       │     │  Install instructions          │
└──────┬───────┘     │  ROS2 packages + agent tools   │
       │             └──────────────────────────────┘
       ▼
┌──────────────────────────────────────────────┐
│  OpenClaw Multi-Agent Orchestration          │
│                                              │
│  👁 SCOUT ──┐                                │
│  🧠 PLANNER ├── parallel ──▶ 🤖 G1 Robot    │
│  ⚠️ SAFETY ──┘                               │
└──────────────────────────────────────────────┘
```

## Quick Start

```bash
# Clone
git clone https://github.com/joshuaiokua/nebius-hackathon.git
cd nebius-hackathon

# Install
uv pip install -e .

# Set API keys
cp .env.example .env
# Edit .env with your keys

# Run the self-expanding agent demo
python orchestrator.py

# Run the marketplace storefront
uvicorn storefront:app --reload --port 8000
# Open http://localhost:8000
```

## API Endpoints

### Marketplace (Human + Bot friendly)
| Endpoint | Description |
|---|---|
| `GET /` | Landing page |
| `GET /catalog` | Browse all parts |
| `GET /api/v1/parts` | JSON: list parts (filter by capability, price, interface) |
| `GET /api/v1/parts/search?q=camera` | JSON: fuzzy search with BM25 ranking |
| `GET /api/v1/capabilities` | JSON: all capabilities with part counts |
| `GET /api/v1/recommend?task=pick+up+box` | JSON: task-based recommendations |
| `GET /api/v1/parts/{pid}` | JSON: part detail with skill YAML |
| `GET /api/v1/parts/{pid}/skill.yaml` | Raw YAML skill file |

## Tech Stack

| Component | Technology |
|---|---|
| Orchestration | OpenClaw multi-agent sessions |
| Simulation | MuJoCo — Unitree G1 |
| Vision Agent | Qwen2-VL-72B via Nebius Token Factory |
| Planning Agent | Qwen3-235B-A22B via Nebius Token Factory |
| Catalog Search | Tavily web search + Adafruit API |
| Database | SQLite + FTS5 (fuzzy search, BM25 ranking) |
| Storefront | FastAPI + dark-theme HTML UI |
| Inference | Nebius AI Cloud GPU |

## Team

- **Gary Holmgren** — OpenClaw orchestration, multi-agent architecture, sim integration (CEO, Drover Labs)
- **Stephen Lantin** — MuJoCo G1 environment, model optimization, safety rollouts
- **Josh Albano** — Marketplace UI, catalog database, product design

## License

MIT
