"""SQLite + FTS5 catalog database for fuzzy part search and filtering."""

import json
import sqlite3
from pathlib import Path

import yaml

_BASE_DIR = Path(__file__).parent
DB_PATH = _BASE_DIR / "catalog.db"
CATALOG_JSON = _BASE_DIR / "store_catalog.json"


def _get_conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    """Create tables and FTS5 index, then load catalog data."""
    conn = _get_conn(db_path)
    cur = conn.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS parts_fts;
        DROP TABLE IF EXISTS parts;

        CREATE TABLE parts (
            pid TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            price REAL NOT NULL,
            url TEXT NOT NULL DEFAULT '',
            image_url TEXT NOT NULL DEFAULT '',
            in_stock INTEGER NOT NULL DEFAULT 1,
            manufacturer TEXT NOT NULL DEFAULT '',
            capability TEXT NOT NULL,
            interface_type TEXT NOT NULL DEFAULT '',
            power_draw_watts REAL NOT NULL DEFAULT 0,
            mount_type TEXT NOT NULL DEFAULT '',
            compatible_platforms TEXT NOT NULL DEFAULT '[]',
            tags TEXT NOT NULL DEFAULT '[]',
            skill_yaml TEXT NOT NULL DEFAULT '',
            skill_id TEXT NOT NULL DEFAULT '',
            tools_json TEXT NOT NULL DEFAULT '[]',
            agent_context_update TEXT NOT NULL DEFAULT ''
        );

        CREATE VIRTUAL TABLE parts_fts USING fts5(
            pid UNINDEXED,
            name,
            description,
            capability,
            tags,
            manufacturer,
            tools_text,
            content='parts_fts_content',
            tokenize='porter unicode61'
        );

        CREATE TABLE parts_fts_content (
            pid TEXT,
            name TEXT,
            description TEXT,
            capability TEXT,
            tags TEXT,
            manufacturer TEXT,
            tools_text TEXT
        );
    """)

    # Load catalog JSON
    if not CATALOG_JSON.exists():
        conn.close()
        return

    catalog = json.loads(CATALOG_JSON.read_text())
    for item in catalog:
        # Parse tools from skill_yaml
        tools = []
        agent_context = ""
        try:
            skill = yaml.safe_load(item.get("skill_yaml", ""))
            if skill:
                tools = [
                    {"name": t["name"], "description": t["description"]}
                    for t in skill.get("agent_tools", [])
                ]
                agent_context = skill.get("agent_context_update", "")
        except Exception:
            pass

        # Build a text blob of tool names and descriptions for FTS
        tools_text = " ".join(
            f"{t['name']} {t['description']}" for t in tools
        )

        # Tags as space-separated string for FTS
        tags_list = item.get("tags", [])
        tags_str = " ".join(tags_list)

        cur.execute("""
            INSERT INTO parts (pid, name, description, price, url, image_url,
                in_stock, manufacturer, capability, interface_type,
                power_draw_watts, mount_type, compatible_platforms, tags,
                skill_yaml, skill_id, tools_json, agent_context_update)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(item["pid"]),
            item["name"],
            item.get("description", ""),
            item["price"],
            item.get("url", ""),
            item.get("image_url", ""),
            1 if item.get("in_stock", True) else 0,
            item.get("manufacturer", ""),
            item["capability"],
            item.get("interface_type", ""),
            item.get("power_draw_watts", 0),
            item.get("mount_type", ""),
            json.dumps(item.get("compatible_platforms", [])),
            json.dumps(tags_list),
            item.get("skill_yaml", ""),
            item.get("skill_id", ""),
            json.dumps(tools),
            agent_context,
        ))

        # Insert into FTS content table and index
        cur.execute("""
            INSERT INTO parts_fts_content (pid, name, description, capability, tags, manufacturer, tools_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(item["pid"]),
            item["name"],
            item.get("description", ""),
            item["capability"].replace("_", " "),
            tags_str,
            item.get("manufacturer", ""),
            tools_text,
        ))

    # Rebuild FTS index from content table
    cur.execute("INSERT INTO parts_fts(parts_fts) VALUES('rebuild')")

    conn.commit()
    conn.close()


def _row_to_dict(row: sqlite3.Row, include_skill_yaml: bool = False) -> dict:
    """Convert a sqlite3.Row to a dict, deserializing JSON fields."""
    d = dict(row)
    d["in_stock"] = bool(d["in_stock"])
    d["compatible_platforms"] = json.loads(d.get("compatible_platforms", "[]"))
    d["tags"] = json.loads(d.get("tags", "[]"))
    d["tools"] = json.loads(d.get("tools_json", "[]"))
    del d["tools_json"]
    if not include_skill_yaml:
        del d["skill_yaml"]
    return d


def get_all_parts(db_path: Path = DB_PATH) -> list[dict]:
    """Get all parts (slim, no skill_yaml)."""
    conn = _get_conn(db_path)
    rows = conn.execute("SELECT * FROM parts ORDER BY capability, price").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_part(pid: str, db_path: Path = DB_PATH) -> dict | None:
    """Get a single part by pid (slim, no skill_yaml)."""
    conn = _get_conn(db_path)
    row = conn.execute("SELECT * FROM parts WHERE pid = ?", (pid,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def get_part_skill_yaml(pid: str, db_path: Path = DB_PATH) -> str | None:
    """Get raw skill YAML for a part."""
    conn = _get_conn(db_path)
    row = conn.execute("SELECT skill_yaml FROM parts WHERE pid = ?", (pid,)).fetchone()
    conn.close()
    return row["skill_yaml"] if row else None


def get_part_full(pid: str, db_path: Path = DB_PATH) -> dict | None:
    """Get a single part with skill_yaml included (for purchase)."""
    conn = _get_conn(db_path)
    row = conn.execute("SELECT * FROM parts WHERE pid = ?", (pid,)).fetchone()
    conn.close()
    return _row_to_dict(row, include_skill_yaml=True) if row else None


def get_capabilities(db_path: Path = DB_PATH) -> list[dict]:
    """Get all capabilities with part counts and price ranges."""
    conn = _get_conn(db_path)
    rows = conn.execute("""
        SELECT capability,
               COUNT(*) as parts_count,
               MIN(price) as min_price,
               MAX(price) as max_price,
               GROUP_CONCAT(pid || '::' || name || '::' || price, '|||') as parts_info
        FROM parts
        GROUP BY capability
        ORDER BY capability
    """).fetchall()
    conn.close()

    results = []
    for row in rows:
        parts_info = row["parts_info"].split("|||") if row["parts_info"] else []
        example_parts = []
        for info in parts_info[:2]:
            pid, name, price = info.split("::")
            example_parts.append({"pid": pid, "name": name, "price": float(price)})

        results.append({
            "capability": row["capability"],
            "label": row["capability"].replace("_", " ").title(),
            "parts_count": row["parts_count"],
            "price_range": {"min": row["min_price"], "max": row["max_price"]},
            "example_parts": example_parts,
        })
    return results


def search_parts(
    query: str = "",
    capability: str = "",
    interface: str = "",
    max_price: float | None = None,
    max_power_watts: float | None = None,
    in_stock: bool | None = None,
    platform: str = "",
    mount: str = "",
    db_path: Path = DB_PATH,
) -> list[dict]:
    """Search parts using FTS5 fuzzy matching with BM25 ranking + SQL filters.

    Args:
        query: Free-text search (FTS5 with porter stemming).
        capability: Exact capability filter.
        interface: Exact interface type filter.
        max_price: Maximum price filter.
        max_power_watts: Maximum power draw filter.
        in_stock: Stock availability filter.
        platform: Platform compatibility filter.
        mount: Mount point filter.

    Returns:
        List of matching parts sorted by relevance (BM25 rank).
    """
    conn = _get_conn(db_path)

    if query:
        # FTS5 search with BM25 ranking
        # Weights: name(10), description(5), capability(8), tags(4), manufacturer(2), tools_text(3)
        fts_query = _build_fts_query(query)
        sql = """
            SELECT p.*, bm25(parts_fts, 10, 5, 8, 4, 2, 3) as rank
            FROM parts_fts
            JOIN parts p ON p.pid = parts_fts.pid
            WHERE parts_fts MATCH ?
        """
        params: list = [fts_query]
    else:
        sql = "SELECT p.*, 0 as rank FROM parts p WHERE 1=1"
        params = []

    if capability:
        sql += " AND p.capability = ?"
        params.append(capability)
    if interface:
        sql += " AND LOWER(p.interface_type) = LOWER(?)"
        params.append(interface)
    if max_price is not None:
        sql += " AND p.price <= ?"
        params.append(max_price)
    if max_power_watts is not None:
        sql += " AND p.power_draw_watts <= ?"
        params.append(max_power_watts)
    if in_stock is not None:
        sql += " AND p.in_stock = ?"
        params.append(1 if in_stock else 0)
    if platform:
        sql += " AND p.compatible_platforms LIKE ?"
        params.append(f'%"{platform}"%')
    if mount:
        sql += " AND p.mount_type = ?"
        params.append(mount)

    if query:
        sql += " ORDER BY rank"  # BM25 rank (lower = more relevant)
    else:
        sql += " ORDER BY p.capability, p.price"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    results = []
    for row in rows:
        d = _row_to_dict(row)
        if query:
            # BM25 returns negative scores (more negative = better match)
            # Convert to positive relevance score for the API
            d["relevance_score"] = round(-float(row["rank"]), 2)
        results.append(d)
    return results


def recommend_for_task(
    task: str,
    current_capabilities: list[str] | None = None,
    power_budget_w: float = 15.0,
    platform: str = "",
    max_price: float | None = None,
    db_path: Path = DB_PATH,
) -> list[dict]:
    """Recommend parts for a task, grouped by capability.

    Uses FTS5 to match task description against part catalog,
    then groups results by capability and picks the best per group.
    """
    if current_capabilities is None:
        current_capabilities = []

    # Search using FTS5
    all_matches = search_parts(
        query=task,
        max_power_watts=power_budget_w,
        platform=platform,
        max_price=max_price,
        in_stock=True,
        db_path=db_path,
    )

    # Filter out capabilities the robot already has
    matches = [m for m in all_matches if m["capability"] not in current_capabilities]

    # Group by capability
    cap_groups: dict[str, list[dict]] = {}
    for m in matches:
        cap = m["capability"]
        if cap not in cap_groups:
            cap_groups[cap] = []
        cap_groups[cap].append(m)

    # Build recommendations: best part per capability + alternatives
    recommendations = []
    for cap, parts in cap_groups.items():
        best = parts[0]  # already sorted by relevance
        alternatives = [
            {"pid": p["pid"], "name": p["name"], "price": p["price"],
             "relevance_score": p.get("relevance_score", 0)}
            for p in parts[1:]
        ]
        recommendations.append({
            "capability": cap,
            "relevance_score": best.get("relevance_score", 0),
            "recommended": best,
            "alternatives": alternatives,
        })

    # Sort by relevance score descending
    recommendations.sort(key=lambda r: r["relevance_score"], reverse=True)
    return recommendations


def _build_fts_query(raw_query: str) -> str:
    """Convert a natural language query into an FTS5 query.

    Handles:
    - Tokenization and stop word removal
    - OR-joining terms so partial matches still return results
    - Prefix matching with * for better recall
    """
    stop_words = {
        "the", "a", "an", "to", "and", "or", "of", "in", "on", "at", "for",
        "is", "it", "its", "with", "from", "by", "that", "this", "into", "up",
        "back", "i", "my", "me", "need", "want", "can", "should", "would",
    }
    tokens = []
    for word in raw_query.lower().split():
        # Strip non-alphanumeric
        clean = "".join(c for c in word if c.isalnum())
        if clean and clean not in stop_words and len(clean) > 1:
            tokens.append(clean)

    if not tokens:
        return raw_query.lower()

    # Use OR so partial matches still rank; FTS5 + porter stemmer handles morphology
    # Add prefix matching (*) for better recall
    parts = [f'"{t}"' if len(t) > 3 else t for t in tokens]
    return " OR ".join(parts)


if __name__ == "__main__":
    print("Initializing catalog database...")
    init_db()
    print(f"Database created at {DB_PATH}")

    print(f"\nTotal parts: {len(get_all_parts())}")
    print(f"Capabilities: {len(get_capabilities())}")

    print("\n--- FTS5 Search Tests ---")

    tests = [
        ("camera", "Should find vision/depth cameras"),
        ("grab objects pick up", "Should find grippers"),
        ("see obstacles depth", "Should find depth/distance sensors"),
        ("navigate patrol", "Should find lidar/GPS/navigation"),
        ("hear voice speak", "Should find audio parts"),
        ("temperature air quality", "Should find environmental sensor"),
    ]
    for query, description in tests:
        results = search_parts(query=query)
        print(f"\n  '{query}' — {description}")
        for r in results[:3]:
            score = r.get("relevance_score", 0)
            print(f"    [{score:6.2f}] {r['name']} ({r['capability']})")

    print("\n--- Recommend Tests ---")
    recs = recommend_for_task(
        "Navigate to the red box on the table, pick it up, and bring it back",
        current_capabilities=["locomotion", "imu"],
        platform="Unitree A1",
    )
    print(f"\n  Task: 'pick up red box' — {len(recs)} capabilities recommended:")
    for rec in recs:
        print(f"    [{rec['relevance_score']:6.2f}] {rec['capability']}: {rec['recommended']['name']}")
