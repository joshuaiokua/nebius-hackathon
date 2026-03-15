import json
import os

import httpx
from dotenv import load_dotenv

from agent.planner import llm_call, _strip_fences
from schemas import CapabilityGap, RobotProfile, SelectedModule

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")


async def search_tavily(query: str, max_results: int = 5) -> list[dict]:
    """Search the web via Tavily.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        List of {title, url, snippet} dicts.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                headers={"Content-Type": "application/json"},
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                },
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", ""),
                }
                for r in results
            ]
    except Exception as e:
        print(f"⚠️  Tavily search failed: {e}")
        return []


_adafruit_cache: list[dict] | None = None


async def _fetch_adafruit_catalog() -> list[dict]:
    """Fetch and cache the full Adafruit product catalog (rate-limited to 5 req/min)."""
    global _adafruit_cache
    if _adafruit_cache is not None:
        return _adafruit_cache
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get("https://www.adafruit.com/api/products")
        resp.raise_for_status()
        _adafruit_cache = resp.json()  # flat array
    return _adafruit_cache


async def search_adafruit(query: str, limit: int = 5) -> list[dict]:
    """Search Adafruit's product catalog via client-side filtering.

    Args:
        query: Search query string.
        limit: Maximum number of results to return.

    Returns:
        List of {name, price, url, pid, in_stock} dicts.
    """
    try:
        catalog = await _fetch_adafruit_catalog()
        keywords = query.lower().split()
        matches = []
        for p in catalog:
            name = p.get("product_name", "").lower()
            if all(kw in name for kw in keywords):
                in_stock = p.get("product_stock", "0") not in ("0", "-1", "-2", "-3")
                matches.append({
                    "name": p.get("product_name", ""),
                    "price": float(p.get("product_price", 0) or 0),
                    "url": f"https://www.adafruit.com/product/{p.get('product_id', '')}",
                    "pid": str(p.get("product_id", "")),
                    "in_stock": in_stock,
                })
            if len(matches) >= limit:
                break
        return matches
    except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as e:
        print(f"⚠️  Adafruit search failed: {e}")
        return []


async def search_and_select_module(
    gap: CapabilityGap, profile: RobotProfile
) -> SelectedModule:
    """Search hardware catalogs and select the best module for a capability gap.

    Args:
        gap: The capability gap to fill.
        profile: Robot profile for compatibility filtering.

    Returns:
        The best matching SelectedModule.
    """
    query = f"{gap.hardware_category} robot ROS2 USB"
    print(f"  🔍  Searching Tavily: '{query}'")
    tavily_results = await search_tavily(query)

    print(f"  🔍  Searching Adafruit: '{gap.hardware_category}'")
    adafruit_results = await search_adafruit(gap.hardware_category)

    # Fallback: widen search if both returned nothing
    if not tavily_results and not adafruit_results:
        print("  ⚠️  Both searches returned nothing, widening query...")
        tavily_results = await search_tavily(gap.hardware_category)
        adafruit_results = await search_adafruit(gap.hardware_category.split()[0])

    system = (
        "You are a robotics hardware procurement specialist. Select the single best hardware module "
        "to fill a capability gap for a robot.\n\n"
        "Output ONLY valid JSON — no markdown, no explanation, no code fences.\n\n"
        "Output format:\n"
        '{"name": "...", "price": 99.99, "url": "...", "pid": "...", '
        '"specs": {"interface": "USB-C", "power_watts": 5, "weight_g": 120}, '
        '"rationale": "..."}\n\n'
        "Selection criteria (in order):\n"
        "1. Compatible with Unitree G1 / ROS2 Humble\n"
        f"2. Power draw ≤ {profile.power_budget_w}W\n"
        "3. USB interface (USB-A or USB-C preferred)\n"
        "4. Lowest price among suitable options\n"
        "5. In stock if from Adafruit\n\n"
        "If a real Adafruit product matches, prefer it (it has a real pid). "
        "Otherwise use the best web result. Always return something — never leave fields empty."
    )

    user = (
        f"Capability gap: {gap.need}\n"
        f"Reason: {gap.reason}\n"
        f"Hardware category: {gap.hardware_category}\n\n"
        f"Adafruit results:\n{json.dumps(adafruit_results, indent=2)}\n\n"
        f"Web search results:\n{json.dumps(tavily_results, indent=2)}"
    )

    raw = await llm_call(system, user)
    data = json.loads(_strip_fences(raw))

    return SelectedModule(
        name=data["name"],
        price=float(data.get("price", 0)),
        url=data.get("url", ""),
        pid=str(data.get("pid", "")),
        specs=data.get("specs", {}),
        rationale=data.get("rationale", ""),
    )


if __name__ == "__main__":
    import asyncio

    from schemas import CapabilityGap, RobotProfile

    async def main():
        profile = RobotProfile()
        gap = CapabilityGap(
            need="vision",
            reason="Robot needs a camera to see the environment",
            hardware_category="stereo camera",
            priority="critical",
        )
        print(f"Searching for: {gap.hardware_category}")
        module = await search_and_select_module(gap, profile)
        print(f"Selected: {module.name} (${module.price})")
        print(f"  URL: {module.url}")
        print(f"  Rationale: {module.rationale}")

    asyncio.run(main())
