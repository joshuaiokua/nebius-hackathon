import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from templates import render_landing, render_catalog, render_detail, render_purchase

CATALOG: list[dict] = []
CATALOG_BY_PID: dict[str, dict] = {}


_BASE_DIR = Path(__file__).parent


def _load_catalog() -> None:
    catalog_path = _BASE_DIR / "store_catalog.json"
    if not catalog_path.exists():
        return
    raw = json.loads(catalog_path.read_text())
    CATALOG.clear()
    CATALOG.extend(raw)
    CATALOG_BY_PID.clear()
    CATALOG_BY_PID.update({str(item["pid"]): item for item in raw})


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _load_catalog()
    yield


app = FastAPI(
    title="RoboStore",
    description="Self-expanding robot parts storefront — human and bot friendly",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------- JSON API ----------


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok", "catalog_size": len(CATALOG)}


@app.get("/api/v1/capabilities")
async def list_capabilities() -> list[str]:
    return sorted({item["capability"] for item in CATALOG})


@app.get("/api/v1/parts")
async def list_parts(
    capability: str | None = Query(None),
    interface: str | None = Query(None),
    max_price: float | None = Query(None),
    max_power_watts: float | None = Query(None),
    in_stock: bool | None = Query(None),
    q: str | None = Query(None),
) -> list[dict]:
    results = CATALOG
    if capability:
        results = [i for i in results if i["capability"] == capability]
    if interface:
        results = [i for i in results if i["interface_type"].lower() == interface.lower()]
    if max_price is not None:
        results = [i for i in results if i["price"] <= max_price]
    if max_power_watts is not None:
        results = [i for i in results if i["power_draw_watts"] <= max_power_watts]
    if in_stock is not None:
        results = [i for i in results if i["in_stock"] == in_stock]
    if q:
        q_lower = q.lower()
        results = [
            i for i in results
            if q_lower in i["name"].lower() or q_lower in " ".join(i.get("tags", []))
        ]
    return results


@app.get("/api/v1/parts/{pid}")
async def get_part(pid: str) -> dict:
    item = CATALOG_BY_PID.get(pid)
    if not item:
        raise HTTPException(404, f"Part {pid} not found")
    return item


class SearchRequest(BaseModel):
    need: str
    power_budget_w: float = 15.0
    mount_points: list[str] = []
    platform: str = ""


@app.post("/api/v1/search")
async def search_parts(req: SearchRequest) -> list[dict]:
    """Bot-oriented search: find parts matching a capability gap."""
    results = [i for i in CATALOG if i["capability"] == req.need]

    results = [i for i in results if i["power_draw_watts"] <= req.power_budget_w]

    if req.mount_points:
        results = [i for i in results if i.get("mount_type") in req.mount_points]

    if req.platform:
        results = [
            i for i in results
            if req.platform in i.get("compatible_platforms", [])
        ]

    results.sort(key=lambda i: i["price"])
    return results


class PurchaseRequest(BaseModel):
    robot_id: str = "unitree-a1-sim"


@app.post("/api/v1/purchase/{pid}")
async def purchase_part(pid: str, req: PurchaseRequest) -> dict:
    """Simulated purchase: returns the skill YAML for immediate ingestion."""
    item = CATALOG_BY_PID.get(pid)
    if not item:
        raise HTTPException(404, f"Part {pid} not found")
    return {
        "status": "purchased",
        "robot_id": req.robot_id,
        "part_name": item["name"],
        "price": item["price"],
        "skill_id": item.get("skill_id", ""),
        "skill_yaml": item.get("skill_yaml", ""),
    }


# ---------- HTML Pages ----------


@app.get("/", response_class=HTMLResponse)
async def landing() -> str:
    return render_landing()


@app.get("/store", response_class=HTMLResponse)
async def store_catalog() -> str:
    capabilities = sorted({item["capability"] for item in CATALOG})
    return render_catalog(CATALOG, capabilities)


@app.get("/store/{pid}", response_class=HTMLResponse)
async def store_detail(pid: str) -> str:
    item = CATALOG_BY_PID.get(pid)
    if not item:
        raise HTTPException(404, f"Part {pid} not found")
    return render_detail(item)


@app.post("/store/{pid}/purchase", response_class=HTMLResponse)
async def store_purchase(pid: str) -> str:
    item = CATALOG_BY_PID.get(pid)
    if not item:
        raise HTTPException(404, f"Part {pid} not found")
    return render_purchase(item)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("storefront:app", host="0.0.0.0", port=8000, reload=True)
