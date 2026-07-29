# Build log

Append-only. Newest entry at the top. One entry per session or substantive
change: what was done, **why**, and anything that surprised us.

This is the archaeological record — when someone asks "why on earth does it do
*that*", the answer should be findable here. Do not rewrite history; if an
earlier decision was reversed, add a new entry saying so.

---

## 2026-07-29 — Extraction, v0.1.0

**What:** Created the project. Extracted the Vera Inspector into a standalone,
app-agnostic, pip-installable package with a CLI and a versioned JSON contract.
60 tests, green. Published to `xsytrance/eyeofthundera`.

### Why now

The capability existed in four places and had begun to diverge:

| Where | What it was |
|---|---|
| `fft-psx-vera/tools/inspector/` | the mature version — 7 modules, vision critique, montages, theme matrix |
| `undertale-vera/inspector.py` | a 193-line single-file ancestor |
| `ember-pro/app/inspector.py` | byte-identical copy of undertale-vera's |
| `ember-lite/app/inspector.py` | byte-identical copy of undertale-vera's |

Every new project meant another hand-port; every improvement landed in exactly
one copy. Also `tools/frontend_smoke.py` existed in three of the four.

Both lineages described themselves as *"eyes"* in their own docstrings, which
is what identified the target when Rod asked to extract "those eyes you have".

### What the extraction changed

The fft Inspector was coupled to its app in four places. All four became config:

1. `registry.py` hardcoded 23 surfaces → `[[surfaces]]`
2. six theme ids + their localStorage keys → `[[profiles]]` with `seeds`
3. `resolve_path()` hardcoded `{project_id}`/`{character_id}`/`{team_id}`/
   `{room_code}` → generic `{param}` + `[discovery]` path expressions
4. `run.py` hardcoded `/api/diag/ui-map` → `discovery.url`

Also generalised: `kind = "static"` (a special case meaning "shoot this once,
it has a fixed palette") became `profiles = ["obsidian"]` on the surface — the
general form of the same idea.

Carried over **unchanged**: `checks.COLLECT_JS`. It was tuned against six themes
× two viewports of a real app and that tuning is most of the value.

### Added beyond the port

- **`http` engine** — the bare-box fallback the undertale-vera lineage had and
  fft's version had lost. Core package has zero dependencies so it always works.
- **Baseline diffing** — anchored on CSS path, not on the detail string, so
  sub-pixel jitter doesn't churn. Verified 0-new/0-fixed across two live runs.
- **Failed clicks as findings** — see the surprise below.
- **Optional clicks** (`?` prefix) — for responsive nav.
- **Versioned, self-describing JSON** — `schema_version`, and the body names
  its own artifacts.
- **`init` / `check` / `surfaces` subcommands** — config authoring without a
  sweep.

### What surprised us

**Two silent-pass bugs, one in the tool and one it then found.**

`undertale-vera` turned out to have *no URL routing at all* — every view is
reached by clicking a nav button. That's handled by `pre_clicks`, which already
existed. But the first real sweep exposed something worse: a `pre_click` that
missed produced a *note*, and the surface still counted **clean**.

At 390px undertale-vera's nav lives in a slide-in drawer, so seven nav-driven
surfaces were being measured as the *chat* view wearing another name — and
reported clean, at both viewports, for the whole first run. The give-away was
`saves__default__d1280.png` being byte-for-byte the same size as
`chat__default__d1280.png`.

Fixed by making a failed required `pre_click` an **error** (`pre_click_failed`),
which promoted the principle in `docs/VISION.md`: *a tool that lies about what
it looked at is worse than no tool.* Once the config was corrected, mobile
warning counts went from a uniform "3" to 5/6/15/4 — the Sound Test room has 15
genuine mobile warnings that had been invisible.

That fix immediately needed a companion: `#save-pill` opens the drawer on mobile
and isn't a click target on desktop, so a click had to be expressible as
*optional*. Hence the `?` prefix.

**An artifacts ordering bug.** `body["artifacts"]` was being set *after*
`write_json()`, so the findings file on disk lacked the artifact paths that
made it self-describing. Caught by reading the actual output rather than
trusting the run summary. Now guarded by a test.

### First real findings on a live app

`undertale-vera` on :9092, zero config: two 23×19px refresh buttons and an
80×28px menu button, all under the 32px tap-target floor, on a view that had
only ever been opened on a desktop.

### Numbers

- 9 modules, ~1,660 lines of Python
- 60 tests (50 no-browser + 10 Chromium), green
- `examples/fft-psx-vera.toml` reproduces the original registry exactly:
  23 surfaces × 6 profiles × 2 viewports = 226 page-views per run
- `examples/undertale-vera.toml`: 8 surfaces, 16 page-views per run

### Left undone deliberately

- **MCP server** — Rod chose "CLI plus json but also eventually mcp". Waiting
  until a third app has used the CLI so the tool surface is designed against
  real usage.
- **Migrating the four copies** — the actual payoff, and the next job.
