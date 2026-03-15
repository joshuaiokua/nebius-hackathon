from html import escape

STYLE = """\
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #0a0a0a; color: #e0e0e0; line-height: 1.6; }
a { color: #6ee7b7; text-decoration: none; }
a:hover { text-decoration: underline; }

.container { max-width: 1200px; margin: 0 auto; padding: 0 24px; }

/* Nav */
nav { background: #111; border-bottom: 1px solid #222; padding: 16px 0; }
nav .container { display: flex; justify-content: space-between; align-items: center; }
nav .brand { font-size: 1.4rem; font-weight: 700; color: #6ee7b7; }
nav .links a { margin-left: 24px; color: #aaa; font-size: 0.9rem; }
nav .links a:hover { color: #fff; }

/* Hero */
.hero { padding: 80px 0 60px; text-align: center; }
.hero h1 { font-size: 2.8rem; font-weight: 800; color: #fff; margin-bottom: 16px; }
.hero h1 span { color: #6ee7b7; }
.hero p { font-size: 1.2rem; color: #888; max-width: 600px; margin: 0 auto 32px; }
.hero .cta { display: inline-block; background: #6ee7b7; color: #000; padding: 12px 32px;
             border-radius: 8px; font-weight: 600; font-size: 1rem; }
.hero .cta:hover { background: #5ddba6; text-decoration: none; }

/* Search */
.search-bar { margin: 32px 0; display: flex; gap: 12px; }
.search-bar input { flex: 1; padding: 12px 16px; background: #1a1a1a; border: 1px solid #333;
                    border-radius: 8px; color: #fff; font-size: 1rem; }
.search-bar input::placeholder { color: #666; }

/* Filters */
.filters { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 24px; }
.pill { padding: 6px 16px; border-radius: 20px; background: #1a1a1a; border: 1px solid #333;
        color: #aaa; font-size: 0.85rem; cursor: pointer; }
.pill:hover, .pill.active { background: #6ee7b7; color: #000; border-color: #6ee7b7; }

/* Grid */
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 24px;
        padding-bottom: 60px; }
.card { background: #141414; border: 1px solid #222; border-radius: 12px; overflow: hidden;
        transition: border-color 0.2s; }
.card:hover { border-color: #6ee7b7; }
.card img { width: 100%; height: 200px; object-fit: cover; background: #222; }
.card .body { padding: 16px; }
.card .name { font-weight: 600; font-size: 1rem; color: #fff; margin-bottom: 4px; }
.card .meta { font-size: 0.85rem; color: #888; margin-bottom: 8px; }
.card .price { font-size: 1.3rem; font-weight: 700; color: #6ee7b7; }
.card .badge { display: inline-block; padding: 2px 10px; border-radius: 12px;
               background: #1e3a2f; color: #6ee7b7; font-size: 0.75rem; margin-right: 4px; }
.card .stock { font-size: 0.8rem; }
.card .stock.yes { color: #6ee7b7; }
.card .stock.no { color: #ef4444; }

/* Detail */
.detail { padding: 40px 0; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }
.detail img { width: 100%; border-radius: 12px; background: #222; }
.detail h1 { font-size: 2rem; color: #fff; margin-bottom: 8px; }
.detail .price-big { font-size: 2rem; font-weight: 800; color: #6ee7b7; margin: 16px 0; }
.specs-table { width: 100%; margin: 16px 0; }
.specs-table td { padding: 8px 12px; border-bottom: 1px solid #222; }
.specs-table td:first-child { color: #888; width: 40%; }
.btn { display: inline-block; padding: 14px 32px; border-radius: 8px; font-weight: 600;
       font-size: 1rem; cursor: pointer; border: none; }
.btn-primary { background: #6ee7b7; color: #000; }
.btn-primary:hover { background: #5ddba6; text-decoration: none; }
.btn-secondary { background: #222; color: #fff; border: 1px solid #333; }
pre.skill { background: #111; border: 1px solid #333; border-radius: 8px; padding: 16px;
            overflow-x: auto; font-size: 0.85rem; color: #ccc; line-height: 1.5; }

/* API section */
.api-section { background: #111; border: 1px solid #222; border-radius: 12px; padding: 32px;
               margin: 40px 0; }
.api-section h2 { color: #6ee7b7; margin-bottom: 16px; }
.api-section code { background: #1a1a1a; padding: 2px 8px; border-radius: 4px; font-size: 0.9rem; }

/* Footer */
footer { border-top: 1px solid #222; padding: 32px 0; text-align: center; color: #555;
         font-size: 0.85rem; }

@media (max-width: 768px) {
  .detail-grid { grid-template-columns: 1fr; }
  .hero h1 { font-size: 2rem; }
}
"""

JS_FILTER = """\
function filterCards() {
  const q = document.getElementById('search').value.toLowerCase();
  const cap = document.querySelector('.pill.active')?.dataset.cap || '';
  document.querySelectorAll('.card').forEach(c => {
    const matchQ = !q || c.dataset.search.toLowerCase().includes(q);
    const matchCap = !cap || c.dataset.cap === cap;
    c.style.display = (matchQ && matchCap) ? '' : 'none';
  });
}
function setCap(el) {
  document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
  if (el.dataset.cap) el.classList.add('active');
  filterCards();
}
"""


def _nav() -> str:
    return (
        '<nav><div class="container">'
        '<a class="brand" href="/">RoboStore</a>'
        '<div class="links">'
        '<a href="/store">Catalog</a>'
        '<a href="/api/v1/health">API</a>'
        '</div></div></nav>'
    )


def _footer() -> str:
    return '<footer><div class="container">RoboStore — Self-expanding robot parts</div></footer>'


def _page(title: str, body: str, extra_js: str = "") -> str:
    return (
        f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{escape(title)}</title>"
        f"<style>{STYLE}</style></head><body>"
        f"{_nav()}{body}{_footer()}"
        f"<script>{extra_js}</script></body></html>"
    )


def render_landing() -> str:
    body = (
        '<div class="container hero">'
        '<h1>Parts that teach your <span>robot</span> new tricks</h1>'
        '<p>Browse real hardware modules — each one ships with a skill file '
        'your robot can ingest instantly. Human or bot, everyone shops here.</p>'
        '<a class="cta" href="/store">Browse Catalog</a>'
        '</div>'
        '<div class="container api-section">'
        '<h2>Robot API</h2>'
        '<p>Your agent can self-expand by calling the API directly:</p>'
        '<pre class="skill">'
        'POST /api/v1/search\n'
        '{"need": "depth_perception", "power_budget_w": 15, "platform": "Unitree A1"}\n\n'
        'POST /api/v1/purchase/{pid}\n'
        '{"robot_id": "unitree-a1-sim"}'
        '</pre>'
        '</div>'
    )
    return _page("RoboStore", body)


def render_catalog(items: list[dict], capabilities: list[str]) -> str:
    pills = '<span class="pill" data-cap="" onclick="setCap(this)">All</span>'
    for cap in sorted(capabilities):
        label = cap.replace("_", " ").title()
        pills += f'<span class="pill" data-cap="{escape(cap)}" onclick="setCap(this)">{escape(label)}</span>'

    cards = ""
    for item in items:
        stock_cls = "yes" if item.get("in_stock") else "no"
        stock_txt = "In stock" if item.get("in_stock") else "Out of stock"
        search_data = f"{item['name']} {' '.join(item.get('tags', []))} {item.get('capability', '')}"
        cards += (
            f'<a href="/store/{escape(str(item["pid"]))}" class="card" '
            f'data-search="{escape(search_data)}" data-cap="{escape(item.get("capability", ""))}">'
            f'<img src="{escape(item.get("image_url", ""))}" alt="{escape(item["name"])}" loading="lazy">'
            f'<div class="body">'
            f'<div class="name">{escape(item["name"])}</div>'
            f'<span class="badge">{escape(item.get("capability", "").replace("_", " "))}</span>'
            f'<span class="stock {stock_cls}">{stock_txt}</span>'
            f'<div class="meta">{escape(item.get("interface_type", ""))} · '
            f'{item.get("power_draw_watts", "?")}W · {escape(item.get("mount_type", ""))}</div>'
            f'<div class="price">${item["price"]:.2f}</div>'
            f'</div></a>'
        )

    body = (
        '<div class="container">'
        f'<div class="search-bar"><input id="search" type="text" placeholder="Search parts..." oninput="filterCards()"></div>'
        f'<div class="filters">{pills}</div>'
        f'<div class="grid">{cards}</div>'
        '</div>'
    )
    return _page("Catalog — RoboStore", body, JS_FILTER)


def render_detail(item: dict) -> str:
    stock_cls = "yes" if item.get("in_stock") else "no"
    stock_txt = "In stock" if item.get("in_stock") else "Out of stock"
    tags_html = " ".join(f'<span class="badge">{escape(t)}</span>' for t in item.get("tags", []))

    specs_rows = (
        f'<tr><td>Capability</td><td>{escape(item.get("capability", "").replace("_", " ").title())}</td></tr>'
        f'<tr><td>Interface</td><td>{escape(item.get("interface_type", ""))}</td></tr>'
        f'<tr><td>Power Draw</td><td>{item.get("power_draw_watts", "?")}W</td></tr>'
        f'<tr><td>Mount Point</td><td>{escape(item.get("mount_type", ""))}</td></tr>'
        f'<tr><td>Platforms</td><td>{escape(", ".join(item.get("compatible_platforms", [])))}</td></tr>'
        f'<tr><td>Manufacturer</td><td>{escape(item.get("manufacturer", ""))}</td></tr>'
        f'<tr><td>Stock</td><td><span class="stock {stock_cls}">{stock_txt}</span></td></tr>'
    )

    body = (
        '<div class="container detail">'
        '<div class="detail-grid">'
        f'<img src="{escape(item.get("image_url", ""))}" alt="{escape(item["name"])}">'
        '<div>'
        f'<h1>{escape(item["name"])}</h1>'
        f'<div>{tags_html}</div>'
        f'<div class="price-big">${item["price"]:.2f}</div>'
        f'<table class="specs-table">{specs_rows}</table>'
        f'<form method="post" action="/store/{escape(str(item["pid"]))}/purchase">'
        f'<button type="submit" class="btn btn-primary">Purchase & Get Skill File</button>'
        f'</form>'
        '</div></div>'
        '<h2 style="margin-top:40px;color:#fff;">Skill File Preview</h2>'
        f'<pre class="skill">{escape(item.get("skill_yaml", ""))}</pre>'
        '</div>'
    )
    return _page(f'{item["name"]} — RoboStore', body)


def render_purchase(item: dict) -> str:
    body = (
        '<div class="container detail">'
        '<h1 style="color:#6ee7b7;margin-top:40px;">Purchase Complete</h1>'
        f'<p style="margin:16px 0;color:#aaa;">You acquired <strong style="color:#fff;">{escape(item["name"])}</strong>. '
        f'The skill file below is ready for your robot to ingest.</p>'
        f'<a class="btn btn-secondary" href="/api/v1/parts/{escape(str(item["pid"]))}" '
        f'style="margin-bottom:24px;">Download as JSON</a>'
        '<h2 style="margin-top:24px;color:#fff;">Skill File</h2>'
        f'<pre class="skill">{escape(item.get("skill_yaml", ""))}</pre>'
        f'<a href="/store" class="btn btn-primary" style="margin-top:24px;">Back to Catalog</a>'
        '</div>'
    )
    return _page(f'Purchased {item["name"]} — RoboStore', body)
