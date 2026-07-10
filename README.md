# Atenas Rentals Tracker

Tracks current long-term rental listings around Atenas, Alajuela, Costa Rica and
publishes them as a free, static, image-free website via GitHub Pages. Refreshes
hourly using a local Claude Code job — Claude does the fetching, parsing, and
new/removed diffing itself; a deterministic script renders the site so the
output styling stays consistent every run.

## How it works

1. `run_update.sh` invokes `claude -p` headlessly with the instructions in
   [`UPDATE_PROMPT.md`](UPDATE_PROMPT.md): fetch RE/MAX Costa Rica and
   Century21 Costa Rica directly, discover other current Atenas rental sources
   with a web search, normalize everything into `data/listings.json`, and
   diff against the previous run to compute new / removed counts.
2. `build_site.py` deterministically renders `docs/index.html`,
   `docs/status.json`, and `docs/style.css` from `data/listings.json`.
3. The run commits and pushes `data/` and `docs/` if anything changed.
   GitHub Pages (configured to serve from `main` / `/docs`) publishes the
   update automatically.
4. A `launchd` job on your Mac runs `run_update.sh` hourly once you're ready
   to go live (see "Going live" below) — it currently is **not** installed,
   by design, until you've tested it.

No images are ever stored — every listing links back to the original post.

## One-time setup

### 1. Install & authenticate GitHub CLI
```bash
brew install gh        # already done
gh auth login           # run this yourself — it's an interactive browser sign-in
```

### 2. Create the GitHub repo and push
```bash
gh repo create atenas-rentals --public --source=. --remote=origin --push
```

### 3. Enable GitHub Pages
In the repo on github.com: **Settings → Pages → Build and deployment → Source:
Deploy from a branch → Branch: `main`, folder `/docs` → Save.**
Your site will be live at `https://<your-username>.github.io/atenas-rentals/`.

### 4. Grant the permissions the unattended job needs
Because `run_update.sh` runs non-interactively (no one there to click
"approve"), Claude Code needs pre-granted permission to run `git`
commands, write files in this repo, and use WebFetch/WebSearch. Add a
`.claude/settings.json` in this repo with an `allow` list scoped to those
actions (or approve them interactively the first few times you run
`./run_update.sh` by hand — Claude Code will remember what you approve).
This is left for you to configure deliberately rather than something set up
automatically, since it governs what an unattended job is allowed to do
without you present.

## Testing (do this before going live)

Run it manually and check the output each time:
```bash
./run_update.sh
open docs/index.html          # or: python3 -m http.server 8000 --directory docs
cat docs/status.json
```
Run it a second time and confirm `new_since_last_update` correctly drops to 0
if nothing changed on the source sites. To test the "removed" path, manually
edit an entry's `url` in `data/listings.json` to something that won't be
found again, run `./run_update.sh`, and confirm it shows up under "Recently
removed" with `removed_since_last_update: 1`.

Check `logs/update-YYYYMMDD.log` after each run for a summary of which
sources succeeded, which were skipped (and why), and whether the commit/push
happened.

## Going live (hourly automation)

Only do this once you've reviewed several manual test runs and are happy
with the output:
```bash
cp launchd/com.airmig.atenasrentals.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.airmig.atenasrentals.plist
```
To stop it later:
```bash
launchctl unload ~/Library/LaunchAgents/com.airmig.atenasrentals.plist
```
Note: `launchd` runs with a minimal environment. If the job can't find the
`claude` command, edit the plist's `ProgramArguments` to call the full path
(find it with `which claude` in your normal terminal).

## Siri: "How many new rentals since the last update?"

Apple doesn't expose a way to provision Shortcuts remotely, so this part is
a quick one-time setup on your iPhone or Mac, once `docs/status.json` is
live:

1. Open the **Shortcuts** app → **+** to create a new shortcut.
2. Add action **Get Contents of URL** → set the URL to
   `https://<your-username>.github.io/atenas-rentals/status.json`.
3. Add action **Get Dictionary Value** → key `new_since_last_update`,
   from the previous step's output.
4. Add action **Text** → `There are [Dictionary Value] new Atenas rentals since the last update.`
   (tap the blue token to insert the value from step 3 into the sentence).
5. Add action **Speak Text** → the text from step 4.
6. Name the shortcut something like "Atenas Update" (this becomes the Siri
   phrase — "Hey Siri, Atenas Update").

Optional: in the shortcut's settings (the ⓘ icon), add it to **Automations**
as a Personal Automation (e.g. "When I open [app]" or "At a scheduled
time") so it can speak automatically instead of needing to be triggered by
voice each time.

## Repo layout

```
UPDATE_PROMPT.md      instructions Claude follows each run
run_update.sh          entry point (manual or scheduled)
build_site.py            deterministic site renderer
data/listings.json         current snapshot (source of truth)
data/previous.json           snapshot from the start of the last run
data/history/                   dated snapshots, pruned after 30 days
docs/                              published static site (GitHub Pages root)
launchd/                             plist template for hourly scheduling
logs/                                   local run logs (gitignored)
```
