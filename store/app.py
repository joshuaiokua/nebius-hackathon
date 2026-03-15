import json
import yaml
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from db import (
    init_db, get_all_parts, get_part, get_part_full, get_part_skill_yaml,
    get_capabilities, search_parts, recommend_for_task, DB_PATH,
)
from templates import render_landing, render_catalog, render_detail, render_purchase

_BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if not DB_PATH.exists():
        init_db()
    yield


app = FastAPI(
    title="RoboStore",
    description="Self-expanding robot parts storefront — human and bot friendly",
    version="0.2.0",
    lifespan=lifespan,
)


# ---------- JSON API ----------


@app.get("/api/v1/health")
async def health() -> dict:
    parts = get_all_parts()
    caps = get_capabilities()
    return {
        "status": "ok",
        "catalog_size": len(parts),
        "capability_count": len(caps),
        "capabilities": [c["capability"] for c in caps],
    }


@app.get("/api/v1/capabilities")
async def list_capabilities() -> list[dict]:
    """Returns all capabilities with descriptions and available part counts."""
    return get_capabilities()


@app.get("/api/v1/parts")
async def list_parts(
    capability: str | None = Query(None, description="Filter by exact capability ID"),
    interface: str | None = Query(None, description="Filter by interface type (USB-C, I2C, etc.)"),
    max_price: float | None = Query(None, description="Maximum price in USD"),
    max_power_watts: float | None = Query(None, description="Maximum power draw in watts"),
    in_stock: bool | None = Query(None, description="Filter by stock availability"),
    platform: str | None = Query(None, description="Filter by compatible platform"),
    mount: str | None = Query(None, description="Filter by mount point"),
    q: str | None = Query(None, description="Fuzzy search across name, description, tags, capability"),
    sort: str | None = Query(None, description="Sort by: price, power, name (prefix with - for desc)"),
) -> list[dict]:
    """List parts with filtering, fuzzy search, and sorting. Returns slim responses (no skill_yaml)."""
    results = search_parts(
        query=q or "",
        capability=capability or "",
        interface=interface or "",
        max_price=max_price,
        max_power_watts=max_power_watts,
        in_stock=in_stock,
        platform=platform or "",
        mount=mount or "",
    )

    # Client-side sorting if requested (FTS results already sorted by relevance)
    if sort:
        desc = sort.startswith("-")
        key = sort.lstrip("-")
        sort_keys = {"price": "price", "power": "power_draw_watts", "name": "name"}
        if key in sort_keys:
            results = sorted(results, key=lambda i: i.get(sort_keys[key], 0), reverse=desc)

    return results


@app.get("/api/v1/parts/{pid}")
async def get_part_detail(pid: str) -> dict:
    """Get full detail for a single part (includes tools summary, excludes raw skill_yaml)."""
    item = get_part(pid)
    if not item:
        raise HTTPException(404, f"Part {pid} not found")
    return item


@app.get("/api/v1/parts/{pid}/skill", response_class=PlainTextResponse)
async def get_skill(pid: str) -> str:
    """Returns the raw YAML skill file for a part, ready for ingestion."""
    skill_yaml = get_part_skill_yaml(pid)
    if skill_yaml is None:
        raise HTTPException(404, f"Part {pid} not found")
    return skill_yaml


class SearchRequest(BaseModel):
    need: str = ""
    query: str = ""
    power_budget_w: float = 15.0
    mount_points: list[str] = []
    platform: str = ""
    max_price: float | None = None
    in_stock_only: bool = False


@app.post("/api/v1/search")
async def search_parts_api(req: SearchRequest) -> dict:
    """Bot-oriented search: find parts matching a capability need or free-text query.

    Accepts either an exact capability `need` (e.g. "vision") or a free-text
    `query` (e.g. "I need to see and grab objects"). Both can be combined.
    Returns ranked results with FTS5 BM25 relevance scores.
    """
    search_text = f"{req.need} {req.query}".strip()

    results = search_parts(
        query=search_text,
        capability=req.need if req.need and not req.query else "",
        max_power_watts=req.power_budget_w,
        max_price=req.max_price,
        in_stock=True if req.in_stock_only else None,
        platform=req.platform,
        mount=req.mount_points[0] if req.mount_points else "",
    )

    return {
        "query": search_text,
        "total_results": len(results),
        "results": results,
    }


class PurchaseRequest(BaseModel):
    robot_id: str = "unitree-a1-sim"


@app.post("/api/v1/purchase/{pid}")
async def purchase_part(pid: str, req: PurchaseRequest) -> dict:
    """Simulated purchase: returns parsed skill data ready for immediate ingestion."""
    item = get_part_full(pid)
    if not item:
        raise HTTPException(404, f"Part {pid} not found")

    # Parse skill YAML into structured data
    skill_parsed = None
    try:
        skill = yaml.safe_load(item.get("skill_yaml", ""))
        if skill:
            skill_parsed = {
                "skill_id": skill.get("skill_id", ""),
                "hardware": skill.get("hardware", ""),
                "compatibility": skill.get("compatibility", []),
                "installation": skill.get("installation", {}),
                "tools": skill.get("agent_tools", []),
                "agent_context_update": skill.get("agent_context_update", ""),
            }
    except Exception:
        pass

    return {
        "status": "purchased",
        "robot_id": req.robot_id,
        "part": {
            "pid": item["pid"],
            "name": item["name"],
            "price": item["price"],
            "capability": item["capability"],
            "interface_type": item.get("interface_type", ""),
            "power_draw_watts": item.get("power_draw_watts", 0),
            "mount_type": item.get("mount_type", ""),
        },
        "skill_id": item.get("skill_id", ""),
        "skill_yaml": item.get("skill_yaml", ""),
        "skill": skill_parsed,
    }


class RecommendRequest(BaseModel):
    task: str
    current_capabilities: list[str] = []
    power_budget_w: float = 15.0
    platform: str = "Unitree A1"
    max_price_per_part: float | None = None


@app.post("/api/v1/recommend")
async def recommend_parts(req: RecommendRequest) -> dict:
    """Task-based part recommendation.

    Given a task description and the robot's current capabilities,
    returns parts grouped by capability that could help accomplish the task.
    Uses FTS5 full-text search with BM25 ranking.
    """
    recommendations = recommend_for_task(
        task=req.task,
        current_capabilities=req.current_capabilities,
        power_budget_w=req.power_budget_w,
        platform=req.platform,
        max_price=req.max_price_per_part,
    )

    return {
        "task": req.task,
        "current_capabilities": req.current_capabilities,
        "recommendations": recommendations,
    }


# ---------- HTML Pages ----------


@app.get("/", response_class=HTMLResponse)
async def landing() -> str:
    parts = get_all_parts()
    caps = get_capabilities()
    return render_landing(catalog_size=len(parts), capability_count=len(caps))


@app.get("/store", response_class=HTMLResponse)
async def store_catalog() -> str:
    # HTML catalog still uses full data for rendering
    all_parts = get_all_parts()
    capabilities = sorted({p["capability"] for p in all_parts})
    # Re-add image_url and tags for template rendering (already in the slim response)
    return render_catalog(all_parts, capabilities)


@app.get("/store/{pid}", response_class=HTMLResponse)
async def store_detail(pid: str) -> str:
    item = get_part_full(pid)
    if not item:
        raise HTTPException(404, f"Part {pid} not found")
    return render_detail(item)


@app.post("/store/{pid}/purchase", response_class=HTMLResponse)
async def store_purchase(pid: str) -> str:
    item = get_part_full(pid)
    if not item:
        raise HTTPException(404, f"Part {pid} not found")
    return render_purchase(item)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("storefront:app", host="0.0.0.0", port=8000, reload=True)
