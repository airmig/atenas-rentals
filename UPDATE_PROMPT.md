# Atenas Rentals — Hourly Update Job

You are running as a scheduled local job (via `run_update.sh`) inside the `atenas-rentals` repo working directory. Do the following, in order, and do not stop for confirmation — this is a non-interactive run.

## 1. Snapshot the previous state

- Read `data/listings.json`. Copy it to `data/previous.json` (overwrite).

## 2. Gather current listings

Collect rental listings for **Atenas and the surrounding Alajuela area, Costa Rica** from as many legitimate, reachable sources as you can, in this order:

**a. Always attempt these two named sources directly** (use your fetch/browser tools):
- RE/MAX Costa Rica: `https://www.remax-costa-rica.com/advanced-search-results-properties/?filter_search_type%5B%5D=house-villa&advanced_city=alajuela-province&advanced_area=&size-min-meters=&bedrooms-min=&bathrooms-min=&price-min=&price-max=&submit=SEARCH+PROPERTIES`
- Also try the cleaner Atenas-specific RE/MAX page if the above is thin: `https://www.remax-costa-rica.com/in/atenas/`
- Century21 Costa Rica: `https://www.century21costarica.com/v/resultados/operacion_renta/en-pais_costa-rica/en-estado_alajuela/ordenado-por_visitas_descendiente` (also try `https://www.century21costarica.com/v/results/type_house/listing-type_rent/in-country_costa-rica/in-state_alajuela/in-municipality_alajuela-atenas/`). **This site is known to block automated requests at the network level.** If it fails to load (connection error, timeout, or a blocked/challenge response), log one line noting it was unreachable this run and move on immediately. Never retry aggressively, never try to work around the block.

**b. Discover additional current sources with a web search** each run, e.g.:
`WebSearch("casa alquiler Atenas Alajuela Costa Rica rental listing <current month/year>")`
From the results, fetch listing pages from legitimate real-estate sites (examples seen previously: `atenasbestclimate.com`, `atenas-realty.com`, `puravidaparadise.com`, `casas24.com`, `anuntico.com` — the exact set will vary run to run, that's expected and fine).

**c. Hard rules for every source, no exceptions:**
- Check `robots.txt` before fetching a new domain for the first time in a run; skip any path it disallows.
- **Never attempt to solve or bypass a CAPTCHA or a Cloudflare/bot-challenge page** ("Attention Required," "Verify you are human," etc.). If you land on one, treat that source as unreachable this run, log it, and move on. This applies even if it seems like it might just be a simple click-through.
- Never download or store images. Only extract structured text facts.
- Never copy long descriptions verbatim — summarize in your own words if needed, but the schema below only needs short structured fields anyway.
- Always keep the original listing URL so the site can link back to the source.
- Only include long-term rentals (not vacation/nightly rentals like Airbnb/Vrbo-style listings) unless nothing else is available — this is a rental-housing tracker, not a vacation-booking site.
- **Dedupe across sources:** the same physical property is often syndicated to multiple sites (e.g. RE/MAX Costa Rica and its local Atenas affiliate RE/MAX Best Climate frequently list the identical property). Before adding a listing found this run, check if one with the same price + bedrooms + bathrooms + closely matching title/location was already added this run from a different source; if so, keep only the first one found and skip the duplicate rather than showing the same property twice.

## 3. Normalize each listing to this schema

```json
{
  "id": "<stable hash of source+url, e.g. sha1>",
  "source": "<site name, e.g. 'RE/MAX Costa Rica'>",
  "title": "...",
  "price": <number or null>,
  "currency": "USD or CRC",
  "bedrooms": <number or null>,
  "bathrooms": <number or null>,
  "area_m2": <number or null>,
  "location": "...",
  "url": "...",
  "first_seen": "<ISO timestamp — only set when creating a brand-new entry>",
  "last_seen": "<ISO timestamp — always update to now for anything still found>",
  "status": "active",
  "removed_at": null
}
```

Use a stable id (e.g. sha1 of `source + url`) so the same listing keeps the same id across runs.

## 4. Diff against `data/previous.json`

- For each listing found in step 2: if its id is new, set `first_seen = now`; otherwise carry over the existing `first_seen` and update `last_seen = now`. Set `status: "active"`.
- For each listing in `previous.json` that had `status: "active"` but was **not** found in this run: set `status: "removed"`, `removed_at = now`, keep it in the array (don't delete). If a listing has had `status: "removed"` for more than 7 days, drop it from `data/listings.json` (it still lives in the dated snapshot under `data/history/` from when it was last active, so nothing is truly lost).
- Compute `new_since_last_update` = count of ids that are new this run.
- Compute `removed_since_last_update` = count of ids newly marked removed this run.

## 5. Write outputs

- Write the updated array to `data/listings.json` (pretty-printed JSON, stable key order).
- Copy `data/listings.json` to `data/history/YYYY-MM-DD-HHmm.json`. Delete any history files older than 30 days.
- Run `python3 build_site.py` — this deterministically regenerates `docs/index.html`, `docs/status.json`, and `docs/style.css` from `data/listings.json`. Do not hand-write the HTML yourself; always go through this script so output stays visually consistent run to run. Pass it `--new N --removed M` where N and M are the counts from step 4 (see `build_site.py --help` for the exact flags).

## 6. Commit and publish

From the repo root:
```
git add -A
git diff --cached --quiet || git commit -m "Update: $(date -u +'%Y-%m-%d %H:%M UTC') (+${NEW} new, -${REMOVED} removed)"
git push
```
Only commit/push if something actually changed (the `git diff --cached --quiet ||` guard handles this). If there is nothing to commit, that's a normal, successful run — just say so in your summary.

## 7. Summary

End with a one-line summary: how many sources were checked, how many succeeded/were skipped (and why), total active listings, new count, removed count, and whether the commit/push happened.
