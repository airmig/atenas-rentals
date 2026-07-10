#!/usr/bin/env python3
"""Deterministic static site renderer for the Atenas rentals tracker.

Reads data/listings.json and writes docs/index.html, docs/status.json,
and docs/style.css. Run after data/listings.json has been updated for
the current cycle (see UPDATE_PROMPT.md for the full run sequence).
"""
import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "listings.json"
DOCS_DIR = ROOT / "docs"
REMOVED_RETENTION_DAYS = 7


def load_listings():
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text()).get("listings", [])


def fmt_price(listing):
    price = listing.get("price")
    currency = listing.get("currency") or "USD"
    if price is None:
        return "Price on request"
    symbol = "$" if currency == "USD" else currency + " "
    return f"{symbol}{price:,.0f}/mo"


def fmt_facts(listing):
    parts = []
    if listing.get("bedrooms") is not None:
        parts.append(f"{listing['bedrooms']} bed")
    if listing.get("bathrooms") is not None:
        parts.append(f"{listing['bathrooms']} bath")
    if listing.get("area_m2") is not None:
        parts.append(f"{listing['area_m2']:,.0f} m²")
    return " · ".join(parts) if parts else ""


def render_card(listing, is_new, is_removed):
    title = html.escape(listing.get("title") or "Untitled listing")
    source = html.escape(listing.get("source") or "Unknown source")
    location = html.escape(listing.get("location") or "")
    url = html.escape(listing.get("url") or "#", quote=True)
    price = html.escape(fmt_price(listing))
    facts = html.escape(fmt_facts(listing))

    badge = '<span class="badge badge-new">NEW</span>' if is_new else ""
    card_class = "card card-removed" if is_removed else "card"
    link = (
        ""
        if is_removed
        else f'<a class="card-link" href="{url}" target="_blank" rel="noopener noreferrer">View original listing →</a>'
    )

    return f"""
    <article class="{card_class}">
      <div class="card-head">
        <h3>{title}</h3>
        {badge}
      </div>
      <p class="card-price">{price}</p>
      <p class="card-facts">{facts}</p>
      <p class="card-meta">{location} · {source}</p>
      {link}
    </article>"""


def render_site(listings, new_count, removed_count):
    now = datetime.now(timezone.utc)
    active = [l for l in listings if l.get("status") == "active"]
    removed = [l for l in listings if l.get("status") == "removed"]

    active.sort(key=lambda l: l.get("first_seen") or "", reverse=True)
    removed.sort(key=lambda l: l.get("removed_at") or "", reverse=True)

    new_ids = {l["id"] for l in active if l.get("first_seen") == l.get("last_seen")} if new_count else set()

    active_cards = "\n".join(
        render_card(l, is_new=(new_count and l.get("first_seen") == l.get("last_seen")), is_removed=False)
        for l in active
    ) or '<p class="empty">No active listings tracked yet.</p>'

    removed_section = ""
    if removed:
        removed_cards = "\n".join(render_card(l, is_new=False, is_removed=True) for l in removed)
        removed_section = f"""
    <section class="removed-section">
      <h2>Recently removed <span class="muted">(last {REMOVED_RETENTION_DAYS} days)</span></h2>
      <div class="grid">{removed_cards}</div>
    </section>"""

    updated_str = now.strftime("%b %d, %Y · %H:%M UTC")

    by_source = {}
    for l in active:
        by_source[l.get("source", "Unknown")] = by_source.get(l.get("source", "Unknown"), 0) + 1
    source_summary = " · ".join(f"{k}: {v}" for k, v in sorted(by_source.items()))

    html_out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Atenas Rentals Tracker</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="site-header">
    <h1>Atenas Rentals Tracker</h1>
    <p class="subtitle">Long-term rental listings around Atenas, Alajuela, Costa Rica — refreshed hourly.</p>
    <div class="status-banner">
      <span>Last updated: <strong>{updated_str}</strong></span>
      <span class="sep">·</span>
      <span><strong>{new_count}</strong> new</span>
      <span class="sep">·</span>
      <span><strong>{removed_count}</strong> no longer available</span>
      <span class="sep">·</span>
      <span><strong>{len(active)}</strong> active total</span>
    </div>
    <p class="source-summary muted">{source_summary}</p>
  </header>

  <main>
    <section>
      <div class="grid">{active_cards}</div>
    </section>
    {removed_section}
  </main>

  <footer class="site-footer">
    <p>Data aggregated from public rental listing sites for personal informational use. No images stored — click through to the original listing. Not affiliated with any listed brokerage.</p>
  </footer>
</body>
</html>
"""

    status = {
        "last_updated": now.isoformat(),
        "total_listings": len(active),
        "new_since_last_update": new_count,
        "removed_since_last_update": removed_count,
        "by_source": by_source,
    }

    return html_out, status


CSS = """
:root {
  --bg: #f7f6f3;
  --surface: #ffffff;
  --text: #1c1b19;
  --muted: #6b6862;
  --border: #e7e4dd;
  --accent: #2f6f4f;
  --accent-soft: #e6f0ea;
  --removed-bg: #f1efe9;
  --radius: 10px;
  --shadow: 0 1px 2px rgba(0,0,0,0.04), 0 1px 8px rgba(0,0,0,0.03);
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16181a;
    --surface: #1e2124;
    --text: #eceae6;
    --muted: #9a978f;
    --border: #2c2f33;
    --accent: #6fbf95;
    --accent-soft: #23342a;
    --removed-bg: #1a1c1e;
    --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 1px 8px rgba(0,0,0,0.25);
  }
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
}

.site-header {
  max-width: 960px;
  margin: 0 auto;
  padding: 2.5rem 1.25rem 1.5rem;
}

.site-header h1 {
  margin: 0 0 0.25rem;
  font-size: 1.75rem;
  letter-spacing: -0.02em;
}

.subtitle {
  margin: 0 0 1rem;
  color: var(--muted);
}

.status-banner {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: baseline;
  background: var(--accent-soft);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.75rem 1rem;
  font-size: 0.95rem;
}

.status-banner .sep { color: var(--muted); }

.source-summary {
  margin: 0.6rem 0 0;
  font-size: 0.85rem;
}

.muted { color: var(--muted); }

main {
  max-width: 960px;
  margin: 0 auto;
  padding: 0 1.25rem 3rem;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.1rem;
  box-shadow: var(--shadow);
}

.card-removed {
  background: var(--removed-bg);
  opacity: 0.7;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.5rem;
}

.card-head h3 {
  margin: 0;
  font-size: 1.02rem;
  line-height: 1.35;
}

.badge {
  flex-shrink: 0;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
}

.badge-new {
  background: var(--accent);
  color: #fff;
}

.card-price {
  margin: 0.5rem 0 0.15rem;
  font-weight: 600;
}

.card-facts, .card-meta {
  margin: 0.15rem 0;
  color: var(--muted);
  font-size: 0.9rem;
}

.card-link {
  display: inline-block;
  margin-top: 0.6rem;
  font-size: 0.88rem;
  color: var(--accent);
  text-decoration: none;
}

.card-link:hover { text-decoration: underline; }

.removed-section {
  margin-top: 2.5rem;
}

.removed-section h2 {
  font-size: 1.1rem;
  margin-bottom: 0.9rem;
}

.empty {
  color: var(--muted);
}

.site-footer {
  max-width: 960px;
  margin: 0 auto;
  padding: 1.5rem 1.25rem 3rem;
  color: var(--muted);
  font-size: 0.82rem;
  border-top: 1px solid var(--border);
}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--new", type=int, default=0, dest="new_count")
    parser.add_argument("--removed", type=int, default=0, dest="removed_count")
    args = parser.parse_args()

    listings = load_listings()
    html_out, status = render_site(listings, args.new_count, args.removed_count)

    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "index.html").write_text(html_out)
    (DOCS_DIR / "status.json").write_text(json.dumps(status, indent=2))
    (DOCS_DIR / "style.css").write_text(CSS)

    print(f"Wrote docs/index.html, docs/status.json, docs/style.css "
          f"({status['total_listings']} active, {args.new_count} new, {args.removed_count} removed)")


if __name__ == "__main__":
    sys.exit(main())
