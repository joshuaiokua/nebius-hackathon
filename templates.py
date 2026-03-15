from html import escape

STYLE = """\
:root {
  --bg: #050507;
  --surface: #0e0f12;
  --surface-2: #161820;
  --border: #1e2028;
  --border-hover: #2a2d38;
  --text: #e2e4ea;
  --text-muted: #7a7f8e;
  --text-dim: #4e5260;
  --accent: #6ee7b7;
  --accent-dim: #1a3a2e;
  --accent-hover: #5ddba6;
  --danger: #ef4444;
  --radius: 12px;
  --radius-sm: 8px;
  --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { font-family: var(--font); background: var(--bg); color: var(--text); line-height: 1.6;
       -webkit-font-smoothing: antialiased; }
a { color: var(--accent); text-decoration: none; transition: color 0.15s; }
a:hover { color: var(--accent-hover); }

.container { max-width: 1200px; margin: 0 auto; padding: 0 24px; }

/* Nav */
nav { background: rgba(14,15,18,0.85); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border); padding: 14px 0; position: sticky; top: 0; z-index: 100; }
nav .container { display: flex; justify-content: space-between; align-items: center; }
nav .brand { font-size: 1.3rem; font-weight: 700; color: var(--accent); letter-spacing: -0.02em; }
nav .brand span { color: var(--text-muted); font-weight: 400; }
nav .links { display: flex; gap: 8px; }
nav .links a { color: var(--text-muted); font-size: 0.85rem; padding: 6px 14px; border-radius: 6px;
               transition: all 0.15s; }
nav .links a:hover { color: var(--text); background: var(--surface-2); }

/* Hero */
.hero { padding: 100px 0 80px; text-align: center; position: relative; }
.hero::before { content: ''; position: absolute; top: 0; left: 50%; transform: translateX(-50%);
                width: 600px; height: 400px; background: radial-gradient(ellipse, rgba(110,231,183,0.06) 0%, transparent 70%);
                pointer-events: none; }
.hero h1 { font-size: 3.2rem; font-weight: 800; color: #fff; margin-bottom: 16px;
            letter-spacing: -0.03em; line-height: 1.1; }
.hero h1 span { background: linear-gradient(135deg, var(--accent) 0%, #34d399 100%);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.hero .subtitle { font-size: 1.15rem; color: var(--text-muted); max-width: 560px;
                  margin: 0 auto 40px; line-height: 1.7; }
.hero .cta-group { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
.btn { display: inline-flex; align-items: center; gap: 8px; padding: 12px 28px; border-radius: var(--radius-sm);
       font-weight: 600; font-size: 0.9rem; cursor: pointer; border: none; transition: all 0.15s;
       text-decoration: none; }
.btn-primary { background: var(--accent); color: #000; }
.btn-primary:hover { background: var(--accent-hover); color: #000; text-decoration: none; transform: translateY(-1px); }
.btn-ghost { background: transparent; color: var(--text); border: 1px solid var(--border); }
.btn-ghost:hover { border-color: var(--border-hover); background: var(--surface); color: var(--text);
                   text-decoration: none; }

/* Stats row */
.stats { display: flex; justify-content: center; gap: 48px; padding: 48px 0; border-top: 1px solid var(--border);
         border-bottom: 1px solid var(--border); margin: 0 0 60px; }
.stat { text-align: center; }
.stat .num { font-size: 2rem; font-weight: 800; color: #fff; letter-spacing: -0.02em; }
.stat .label { font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em;
               margin-top: 4px; }

/* Feature cards */
.features { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 60px; }
.feature { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
           padding: 28px; transition: border-color 0.2s; }
.feature:hover { border-color: var(--border-hover); }
.feature .icon { font-size: 1.5rem; margin-bottom: 12px; }
.feature h3 { font-size: 1rem; font-weight: 600; color: #fff; margin-bottom: 6px; }
.feature p { font-size: 0.85rem; color: var(--text-muted); line-height: 1.6; }

/* API showcase */
.api-showcase { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
                padding: 40px; margin: 0 0 60px; display: grid; grid-template-columns: 1fr 1fr; gap: 40px;
                align-items: center; }
.api-showcase h2 { font-size: 1.5rem; font-weight: 700; color: #fff; margin-bottom: 12px; }
.api-showcase p { color: var(--text-muted); font-size: 0.9rem; margin-bottom: 20px; line-height: 1.7; }
.api-showcase .endpoints { display: flex; flex-direction: column; gap: 8px; }
.endpoint-tag { display: inline-flex; align-items: center; gap: 8px; font-family: var(--mono);
                font-size: 0.8rem; }
.endpoint-tag .method { padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.7rem; }
.endpoint-tag .method.get { background: #1a2e3a; color: #60a5fa; }
.endpoint-tag .method.post { background: #2e1a3a; color: #c084fc; }
pre.code-block { background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-sm);
                 padding: 20px; overflow-x: auto; font-family: var(--mono); font-size: 0.8rem;
                 color: #c4c8d4; line-height: 1.7; }
pre.code-block .comment { color: var(--text-dim); }
pre.code-block .string { color: var(--accent); }
pre.code-block .key { color: #c084fc; }

/* Search & Filters */
.catalog-header { padding: 40px 0 0; }
.catalog-header h1 { font-size: 1.8rem; font-weight: 700; color: #fff; margin-bottom: 4px; }
.catalog-header p { color: var(--text-muted); font-size: 0.9rem; margin-bottom: 24px; }
.search-bar { display: flex; gap: 12px; margin-bottom: 16px; }
.search-bar input { flex: 1; padding: 12px 16px; background: var(--surface); border: 1px solid var(--border);
                    border-radius: var(--radius-sm); color: #fff; font-size: 0.9rem; font-family: var(--font);
                    transition: border-color 0.15s; outline: none; }
.search-bar input::placeholder { color: var(--text-dim); }
.search-bar input:focus { border-color: var(--accent); }
.filters { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 28px; }
.pill { padding: 6px 14px; border-radius: 20px; background: var(--surface); border: 1px solid var(--border);
        color: var(--text-muted); font-size: 0.8rem; cursor: pointer; transition: all 0.15s;
        font-family: var(--font); }
.pill:hover { border-color: var(--border-hover); color: var(--text); }
.pill.active { background: var(--accent); color: #000; border-color: var(--accent); font-weight: 600; }

/* Product Grid */
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 16px;
        padding-bottom: 60px; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
        overflow: hidden; transition: all 0.2s; display: flex; flex-direction: column; }
.card:hover { border-color: var(--accent); transform: translateY(-2px);
              box-shadow: 0 8px 24px rgba(110,231,183,0.06); text-decoration: none; }
.card .img-wrap { position: relative; height: 180px; background: var(--surface-2); overflow: hidden; }
.card .img-wrap img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s; }
.card:hover .img-wrap img { transform: scale(1.03); }
.card .img-wrap .cap-badge { position: absolute; top: 10px; left: 10px; padding: 3px 10px;
                              border-radius: 6px; background: rgba(0,0,0,0.7); backdrop-filter: blur(4px);
                              color: var(--accent); font-size: 0.7rem; font-weight: 600;
                              text-transform: uppercase; letter-spacing: 0.04em; }
.card .body { padding: 16px; flex: 1; display: flex; flex-direction: column; }
.card .name { font-weight: 600; font-size: 0.9rem; color: #fff; margin-bottom: 6px; line-height: 1.3; }
.card .meta { font-size: 0.78rem; color: var(--text-muted); margin-bottom: auto; padding-bottom: 12px; }
.card .bottom { display: flex; justify-content: space-between; align-items: center;
                border-top: 1px solid var(--border); padding-top: 12px; }
.card .price { font-size: 1.15rem; font-weight: 700; color: var(--accent); }
.card .stock { font-size: 0.72rem; font-weight: 500; }
.card .stock.yes { color: var(--accent); }
.card .stock.no { color: var(--danger); }

/* Detail Page */
.detail { padding: 40px 0 60px; }
.breadcrumb { font-size: 0.8rem; color: var(--text-dim); margin-bottom: 24px; }
.breadcrumb a { color: var(--text-muted); }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 48px; }
.detail .img-main { width: 100%; border-radius: var(--radius); background: var(--surface-2); aspect-ratio: 4/3;
                    object-fit: cover; }
.detail h1 { font-size: 1.8rem; font-weight: 700; color: #fff; margin-bottom: 4px; line-height: 1.2; }
.detail .mfg { color: var(--text-muted); font-size: 0.85rem; margin-bottom: 16px; }
.detail .price-big { font-size: 2.2rem; font-weight: 800; color: var(--accent); margin-bottom: 20px;
                     letter-spacing: -0.02em; }
.detail .tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 20px; }
.tag { padding: 3px 10px; border-radius: 6px; background: var(--accent-dim); color: var(--accent);
       font-size: 0.72rem; font-weight: 500; }
.specs-table { width: 100%; margin: 20px 0; }
.specs-table td { padding: 10px 14px; border-bottom: 1px solid var(--border); font-size: 0.85rem; }
.specs-table td:first-child { color: var(--text-muted); width: 40%; }
.specs-table td:last-child { color: #fff; font-weight: 500; }
.detail .actions { display: flex; gap: 12px; margin-top: 24px; }

/* Tabs */
.tabs { margin-top: 48px; }
.tab-header { display: flex; gap: 0; border-bottom: 1px solid var(--border); }
.tab-btn { padding: 10px 20px; background: none; border: none; color: var(--text-muted); cursor: pointer;
           font-size: 0.85rem; font-family: var(--font); border-bottom: 2px solid transparent;
           transition: all 0.15s; }
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
.tab-panel { display: none; padding: 24px 0; }
.tab-panel.active { display: block; }
pre.skill { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-sm);
            padding: 20px; overflow-x: auto; font-family: var(--mono); font-size: 0.8rem;
            color: #c4c8d4; line-height: 1.7; }

/* Purchase page */
.purchase-success { text-align: center; padding: 80px 0; }
.purchase-success .check { font-size: 3rem; margin-bottom: 16px; }
.purchase-success h1 { font-size: 1.8rem; color: #fff; margin-bottom: 8px; }
.purchase-success p { color: var(--text-muted); margin-bottom: 32px; }

/* Footer */
footer { border-top: 1px solid var(--border); padding: 32px 0; text-align: center;
         color: var(--text-dim); font-size: 0.8rem; }

/* Responsive */
@media (max-width: 768px) {
  .hero h1 { font-size: 2.2rem; }
  .features { grid-template-columns: 1fr; }
  .api-showcase { grid-template-columns: 1fr; }
  .detail-grid { grid-template-columns: 1fr; }
  .stats { gap: 24px; flex-wrap: wrap; }
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
  // update count
  const visible = document.querySelectorAll('.card[style=""], .card:not([style])').length;
  const counter = document.getElementById('result-count');
  if (counter) counter.textContent = visible + ' parts';
}
function setCap(el) {
  document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
  if (el.dataset.cap) el.classList.add('active');
  filterCards();
}
"""

JS_TABS = """\
function switchTab(name) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'tab-' + name));
}
"""


def _nav() -> str:
    return (
        '<nav><div class="container">'
        '<a class="brand" href="/">Robo<span>Store</span></a>'
        '<div class="links">'
        '<a href="/store">Catalog</a>'
        '<a href="/api/v1/health">API</a>'
        '<a href="https://github.com" target="_blank">GitHub</a>'
        '</div></div></nav>'
    )


def _footer() -> str:
    return (
        '<footer><div class="container">'
        'RoboStore &mdash; Self-expanding robot parts &middot; Built for embodied AI'
        '</div></footer>'
    )


def _page(title: str, body: str, extra_js: str = "") -> str:
    return (
        f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{escape(title)}</title>"
        f"<link rel='preconnect' href='https://fonts.googleapis.com'>"
        f"<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        f"<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&"
        f"family=JetBrains+Mono:wght@400;500&display=swap' rel='stylesheet'>"
        f"<style>{STYLE}</style></head><body>"
        f"{_nav()}{body}{_footer()}"
        f"<script>{extra_js}</script></body></html>"
    )


def render_landing(catalog_size: int = 0, capability_count: int = 0) -> str:
    body = (
        '<div class="container hero">'
        '<h1>Parts that teach your<br><span>robot new tricks</span></h1>'
        '<p class="subtitle">Browse real hardware modules &mdash; each one ships with a skill file '
        'your robot can ingest instantly. Human or bot, everyone shops here.</p>'
        '<div class="cta-group">'
        '<a class="btn btn-primary" href="/store">Browse Catalog</a>'
        '<a class="btn btn-ghost" href="#api">View API Docs</a>'
        '</div>'
        '</div>'

        # Stats
        '<div class="container">'
        '<div class="stats">'
        f'<div class="stat"><div class="num">{catalog_size}</div><div class="label">Parts</div></div>'
        f'<div class="stat"><div class="num">{capability_count}</div><div class="label">Capabilities</div></div>'
        '<div class="stat"><div class="num">100%</div><div class="label">Skill Files</div></div>'
        '<div class="stat"><div class="num">&lt;5s</div><div class="label">API Response</div></div>'
        '</div></div>'

        # Features
        '<div class="container">'
        '<div class="features">'
        '<div class="feature">'
        '<div class="icon">&#x1f50d;</div>'
        '<h3>Gap Detection</h3>'
        '<p>Tell us what task your robot needs to do. Our agent detects which capabilities are missing '
        'and finds the right hardware to fill the gap.</p>'
        '</div>'
        '<div class="feature">'
        '<div class="icon">&#x1f4e6;</div>'
        '<h3>Skill Files Included</h3>'
        '<p>Every part ships with a YAML skill file containing install instructions, ROS2 launch commands, '
        'and ready-to-call agent tools.</p>'
        '</div>'
        '<div class="feature">'
        '<div class="icon">&#x1f916;</div>'
        '<h3>Bot-Native API</h3>'
        '<p>Robots can search, filter, and purchase parts programmatically. '
        'Self-expanding hardware procurement in a single POST request.</p>'
        '</div>'
        '</div></div>'

        # API showcase
        '<div class="container" id="api">'
        '<div class="api-showcase">'
        '<div>'
        '<h2>Built for robots first</h2>'
        '<p>Your agent can search by capability, filter by power budget and platform, '
        'and purchase parts &mdash; all through a clean JSON API.</p>'
        '<div class="endpoints">'
        '<div class="endpoint-tag"><span class="method get">GET</span> /api/v1/parts</div>'
        '<div class="endpoint-tag"><span class="method get">GET</span> /api/v1/parts/{pid}</div>'
        '<div class="endpoint-tag"><span class="method get">GET</span> /api/v1/parts/{pid}/skill</div>'
        '<div class="endpoint-tag"><span class="method post">POST</span> /api/v1/search</div>'
        '<div class="endpoint-tag"><span class="method post">POST</span> /api/v1/purchase/{pid}</div>'
        '</div>'
        '</div>'
        '<pre class="code-block">'
        '<span class="comment"># Robot self-purchase flow</span>\n'
        'POST /api/v1/search\n'
        '{\n'
        '  <span class="key">"need"</span>: <span class="string">"depth_perception"</span>,\n'
        '  <span class="key">"power_budget_w"</span>: 15,\n'
        '  <span class="key">"platform"</span>: <span class="string">"Unitree A1"</span>\n'
        '}\n\n'
        '<span class="comment"># Returns matching parts with skill files</span>\n'
        '<span class="comment"># → Purchase → Ingest skill → Retry task</span>'
        '</pre>'
        '</div></div>'
    )
    return _page("RoboStore — Self-Expanding Robot Parts", body)


def render_catalog(items: list[dict], capabilities: list[str]) -> str:
    pills = '<span class="pill active" data-cap="" onclick="setCap(this)">All</span>'
    for cap in sorted(capabilities):
        label = cap.replace("_", " ").title()
        pills += (
            f'<span class="pill" data-cap="{escape(cap)}" onclick="setCap(this)">'
            f'{escape(label)}</span>'
        )

    cards = ""
    for item in items:
        stock_cls = "yes" if item.get("in_stock") else "no"
        stock_txt = "In stock" if item.get("in_stock") else "Out of stock"
        cap_label = item.get("capability", "").replace("_", " ")
        search_data = f"{item['name']} {' '.join(item.get('tags', []))} {item.get('capability', '')}"
        cards += (
            f'<a href="/store/{escape(str(item["pid"]))}" class="card" '
            f'data-search="{escape(search_data)}" data-cap="{escape(item.get("capability", ""))}">'
            f'<div class="img-wrap">'
            f'<img src="{escape(item.get("image_url", ""))}" alt="{escape(item["name"])}" loading="lazy" '
            f'onerror="this.style.display=\'none\'">'
            f'<span class="cap-badge">{escape(cap_label)}</span>'
            f'</div>'
            f'<div class="body">'
            f'<div class="name">{escape(item["name"])}</div>'
            f'<div class="meta">{escape(item.get("manufacturer", ""))} &middot; '
            f'{escape(item.get("interface_type", ""))} &middot; '
            f'{item.get("power_draw_watts", "?")}W</div>'
            f'<div class="bottom">'
            f'<span class="price">${item["price"]:.2f}</span>'
            f'<span class="stock {stock_cls}">{stock_txt}</span>'
            f'</div></div></a>'
        )

    body = (
        '<div class="container catalog-header">'
        f'<h1>Parts Catalog</h1>'
        f'<p><span id="result-count">{len(items)} parts</span> across {len(capabilities)} capabilities</p>'
        f'<div class="search-bar">'
        f'<input id="search" type="text" placeholder="Search parts, capabilities, tags..." oninput="filterCards()">'
        f'</div>'
        f'<div class="filters">{pills}</div>'
        f'</div>'
        f'<div class="container"><div class="grid">{cards}</div></div>'
    )
    return _page("Catalog — RoboStore", body, JS_FILTER)


def render_detail(item: dict) -> str:
    stock_cls = "yes" if item.get("in_stock") else "no"
    stock_txt = "In stock" if item.get("in_stock") else "Out of stock"
    tags_html = " ".join(f'<span class="tag">{escape(t)}</span>' for t in item.get("tags", []))

    specs_rows = (
        f'<tr><td>Capability</td><td>{escape(item.get("capability", "").replace("_", " ").title())}</td></tr>'
        f'<tr><td>Interface</td><td>{escape(item.get("interface_type", ""))}</td></tr>'
        f'<tr><td>Power Draw</td><td>{item.get("power_draw_watts", "?")}W</td></tr>'
        f'<tr><td>Mount Point</td><td>{escape(item.get("mount_type", ""))}</td></tr>'
        f'<tr><td>Platforms</td><td>{escape(", ".join(item.get("compatible_platforms", [])))}</td></tr>'
        f'<tr><td>Manufacturer</td><td>{escape(item.get("manufacturer", ""))}</td></tr>'
        f'<tr><td>Availability</td><td><span class="stock {stock_cls}">{stock_txt}</span></td></tr>'
    )

    pid = escape(str(item["pid"]))

    # API usage snippet
    api_snippet = (
        f'<span class="comment"># Fetch this part via API</span>\n'
        f'GET /api/v1/parts/{pid}\n\n'
        f'<span class="comment"># Purchase and get skill file</span>\n'
        f'POST /api/v1/purchase/{pid}\n'
        f'{{"<span class="key">robot_id</span>": "<span class="string">unitree-a1-sim</span>"}}\n\n'
        f'<span class="comment"># Download raw skill YAML</span>\n'
        f'GET /api/v1/parts/{pid}/skill'
    )

    body = (
        '<div class="container detail">'
        f'<div class="breadcrumb"><a href="/store">Catalog</a> / {escape(item["name"])}</div>'
        '<div class="detail-grid">'
        f'<img class="img-main" src="{escape(item.get("image_url", ""))}" alt="{escape(item["name"])}" '
        f'onerror="this.style.display=\'none\'">'
        '<div>'
        f'<h1>{escape(item["name"])}</h1>'
        f'<div class="mfg">by {escape(item.get("manufacturer", "Unknown"))}</div>'
        f'<div class="tags">{tags_html}</div>'
        f'<div class="price-big">${item["price"]:.2f}</div>'
        f'<table class="specs-table">{specs_rows}</table>'
        '<div class="actions">'
        f'<form method="post" action="/store/{pid}/purchase">'
        '<button type="submit" class="btn btn-primary">Purchase &amp; Get Skill</button>'
        '</form>'
        f'<a class="btn btn-ghost" href="/api/v1/parts/{pid}/skill">Download YAML</a>'
        '</div>'
        '</div></div>'

        # Tabs: Skill File + API Usage
        '<div class="tabs">'
        '<div class="tab-header">'
        '<button class="tab-btn active" data-tab="skill" onclick="switchTab(\'skill\')">Skill File</button>'
        '<button class="tab-btn" data-tab="api" onclick="switchTab(\'api\')">API Usage</button>'
        '</div>'
        f'<div class="tab-panel active" id="tab-skill">'
        f'<pre class="skill">{escape(item.get("skill_yaml", ""))}</pre>'
        '</div>'
        f'<div class="tab-panel" id="tab-api">'
        f'<pre class="code-block">{api_snippet}</pre>'
        '</div>'
        '</div>'

        '</div>'
    )
    return _page(f'{item["name"]} — RoboStore', body, JS_TABS)


def render_purchase(item: dict) -> str:
    pid = escape(str(item["pid"]))
    body = (
        '<div class="container purchase-success">'
        '<div class="check">&#x2705;</div>'
        f'<h1>Skill Acquired</h1>'
        f'<p>You purchased <strong>{escape(item["name"])}</strong>. '
        f'The skill file is ready for ingestion.</p>'
        '<div style="display:flex;gap:12px;justify-content:center;margin-bottom:40px;">'
        f'<a class="btn btn-primary" href="/api/v1/parts/{pid}/skill">Download Skill YAML</a>'
        '<a class="btn btn-ghost" href="/store">Continue Shopping</a>'
        '</div>'
        f'<pre class="skill" style="text-align:left;max-width:700px;margin:0 auto;">'
        f'{escape(item.get("skill_yaml", ""))}</pre>'
        '</div>'
    )
    return _page(f'Purchased {item["name"]} — RoboStore', body)
