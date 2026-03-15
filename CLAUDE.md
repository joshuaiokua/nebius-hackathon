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
