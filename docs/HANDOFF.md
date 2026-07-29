# Handoff

**Last updated:** 2026-07-29 · **Version:** 0.1.0 · **State:** working, published, unused by any consumer yet

> This is the living state document. If you are picking this project up cold —
> human or agent — read this file and `docs/VISION.md`, in that order, and you
> will know everything that matters.
>
> **Keeping it current is mandatory.** See § *The rule* at the bottom.

---

## What this is, in three sentences

Eye of Thundera gives agents sight of a running web app. Point it at a URL and
it returns screenshots plus a machine-readable list of what a careful reviewer
would have noticed — broken images, console errors, overflow, clipped text,
misalignment, cramped tap targets, failing contrast — across every screen size
and theme the project declares. It was extracted from the Vera Inspector, which
existed as four diverging copies across Rod's projects.

## Current state

| | |
|---|---|
| **Works** | Yes. 60/60 tests green. Verified against live `undertale-vera` on :9092. |
| **Published** | `github.com/xsytrance/eyeofthundera` (private) |
| **Installed anywhere** | **No.** No project consumes the package yet. |
| **Version** | 0.1.0, not on PyPI |
| **CI** | GitHub Actions — pytest on push/PR (`.github/workflows/ci.yml`) |

### What's proven

- Zero-config sweep of an arbitrary URL (`thundera look http://host`)
- Full config sweep — 8 surfaces × 2 viewports on undertale-vera
- Both engines (`browser` via Playwright, `http` via urllib)
- Baseline round-trip stable across two live runs (0 new, 0 fixed — no jitter)
- Montage renders correctly (verified by eye, 16 distinct views)
- `examples/fft-psx-vera.toml` validates and reproduces the original registry

### What is *not* proven

- **The fft config has never been run.** `examples/fft-psx-vera.toml` passes
  `thundera check` but the fft stack wasn't up. Expect the first real run to
  find config bugs — that's the point of running it.
- **Vision (`--vision`) has never been exercised here.** Code carried over
  unchanged from fft, where it worked; unverified in this package.
- **No consumer migration has happened.** The drift problem the project exists
  to solve is still, technically, unsolved.

## Get running in two minutes

```bash
cd ~/eye-of-thundera
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/playwright install chromium      # if ~/.cache/ms-playwright is empty
.venv/bin/python -m pytest -q              # expect 60 passed
```

Then, with any web app running:

```bash
.venv/bin/thundera look http://127.0.0.1:9092          # zero config
.venv/bin/thundera look -c examples/undertale-vera.toml
```

`~/.cache/ms-playwright` is shared across venvs on this machine — `fft-psx-vera`
populated it, which is why the browser suite ran without a separate download.

## Where things are

```
thundera/          the package — see docs/ARCHITECTURE.md for the module map
examples/          real configs for undertale-vera and fft-psx-vera
tests/             60 tests; test_browser.py auto-skips without Playwright
docs/VISION.md     why this exists, and the principles that are load-bearing
docs/ARCHITECTURE.md   modules, data shapes, how {param} resolution works
docs/BUILDLOG.md   append-only history — "why does it do that?" lives here
tools/hooks/       the pre-commit doc-freshness hook
```

## Decisions you should not casually reverse

Each of these has a reason recorded in `docs/VISION.md` or `docs/BUILDLOG.md`.

1. **`api.look()` is the only entry point.** CLI is a thin wrapper; MCP will be
   too. Features go in `api` or below, never in `cli.py`.
2. **A failed required `pre_click` is an error.** This exists because seven
   surfaces once reported clean while showing the wrong page. Do not downgrade
   it to a warning to make a config pass.
3. **Baseline identity keys on `anchor`, not `detail`.** `detail` carries pixel
   values that jitter. Key on it and every run reports the whole app as changed.
4. **The core package has zero dependencies.** Playwright/Pillow are extras so
   the `http` engine works on a bare box. Don't add a hard dependency.
5. **`COLLECT_JS` is carried over unchanged and stays that way.** It was tuned
   against a real app over six themes. Noisy for your project? Set
   `severity.<kind> = "off"` in *your* config.
6. **`schema_version` is additive-only.** Agents parse this. Bump the version if
   you must change a key's meaning.

## Known gaps and rough edges

- `settle_ms` is per-surface, not per-viewport. A slow mobile view has to make
  the desktop one wait too.
- `pre_clicks` are per-surface, not per-viewport. The `?` optional prefix covers
  the responsive-nav case; anything more complex needs duplicate surfaces.
- No video/trace capture — you get the final screenshot, not the path there.
- The `http` engine can't verify hash routes (it says so in `engine_note`).
- Vision is Ollama-only.
- `thundera init` writes a static template; it doesn't crawl the app to suggest
  surfaces.

## Next steps, in order

1. **Migrate a consumer.** `undertale-vera` first — `examples/undertale-vera.toml`
   already works. Add the package as a dev dependency, replace `inspector.py`
   and ideally `tools/frontend_smoke.py`, then delete them. **This is the payoff;
   until it happens the project hasn't earned its existence.**
2. **Run the fft config for real** with its stack up. Expect and fix config bugs.
3. **Then `ember-lite` / `ember-pro`** (their inspectors are identical copies of
   undertale-vera's, so step 1 does most of the thinking).
4. **MCP server** — after step 3, so the tool surface is designed against real
   usage. `api.look()` is the seam; this is an adapter, not a rewrite.
5. Answer the open questions in `docs/VISION.md` (public vs private; is "eyes"
   web-only; does it grow a memory).

## Gotchas discovered the hard way

- **undertale-vera has no URL routing.** Views switch on nav clicks. Its nav
  buttons are `[data-view="<name>"]`, but **there is no `data-view="saves"`** —
  saves opens via `#add-save-btn`.
- **At 390px undertale-vera's nav is in a drawer.** `#save-pill` opens it.
  `#chat-hero-menu` looks like the opener but measures 0×0 and can't be clicked.
- **Intro modals cover screenshots.** undertale-vera seeds are `uv_seen_<view>`
  plus `uv_power_seen`. Miss one and you screenshot a modal, not the view.
- **Playwright's `page.click` is strict** — a selector matching two elements
  fails. `_click_reason()` in `driver.py` translates that into plain English.
- **Byte-identical screenshot sizes across two surfaces** is the tell that a
  `pre_click` didn't land. Worth remembering even now that it's an error.

## The rule

**Every change that alters behaviour updates this file and appends to
`docs/BUILDLOG.md`, in the same commit.**

- `docs/HANDOFF.md` (this file) — *what is true now*. Edit in place. Update
  **Last updated**, **Current state**, and **Next steps** at minimum.
- `docs/BUILDLOG.md` — *what happened and why*. Append; never rewrite.
- `docs/VISION.md` — only when the intent or a principle changes.
- `docs/ARCHITECTURE.md` — when modules, data shapes, or contracts change.
- `README.md` — when user-facing behaviour, flags, or config keys change.

A `pre-commit` hook enforces the HANDOFF half of this for changes under
`thundera/`. Install it with `tools/install-hooks.sh`. It is a reminder, not a
cage — `SKIP_DOC_CHECK=1 git commit` when you genuinely mean it.
