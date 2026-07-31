# Handoff

**Last updated:** 2026-07-30 (fifth session) · **Version:** 0.1.0 · **State:** working, published, adopted by its first consumer — one vendored copy deleted, three to go. Contrast false-positive fixed; all 16 undertale-vera views visible (was 9); semantic accessibility pass added, opt-in.

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
| **Works** | Yes. 108/108 tests green. Used on three live apps (:9092, :9095, :9096). |
| **Published** | `github.com/xsytrance/eyeofthundera` (private) |
| **Consumed by** | **`undertale-vera`** — its `inspector.py` is deleted, its `thundera.toml` is committed. `ember-lite`, `ember-pro`, `fft-psx-vera` still carry copies. |
| **Version** | 0.1.0, not on PyPI |
| **CI** | GitHub Actions — pytest on push/PR (`.github/workflows/ci.yml`) |

### What's proven

- Zero-config sweep of an arbitrary URL (`thundera look http://host`)
- Full config sweep — 20 surfaces × 2 viewports on undertale-vera (40 page-views)
- Both engines (`browser` via Playwright, `http` via urllib)
- Baseline round-trip stable across two live runs (0 new, 0 fixed — no jitter)
- Montage renders correctly (verified by eye, 16 distinct views)
- `examples/fft-psx-vera.toml` validates and reproduces the original registry
- The ASCII eye animates in a real tty and stays entirely out of stdout
- **It has found a bug nobody knew about** — see *First real catch* below
- **The contrast compositor is now correct under fixed bars** — undertale-vera
  m390 went 7 warnings → 0, all 7 having been the artifact, while ember-pro's
  genuine 2.2:1 finding still reports. Both directions have tests.
- Preconditions (`setup` steps, cookies, headers, `${VAR}`) reach states seeds
  cannot — verified end to end with a real file upload
- `--retries` demotes a non-reproducing error to a flaky warning, on both engines
- `navigate = "once"` carries in-memory precondition state across surfaces —
  which is what made undertale-vera's seven save-gated views reachable
- **Semantic accessibility pass** (`[a11y] enabled = true`, opt-in). Live: two
  real findings on ember-lite, two on undertale-vera across five surfaces, and
  no noise — both apps already set `lang` and have a `<main>`.

### What is *not* proven

- **The fft config has never been run.** `examples/fft-psx-vera.toml` passes
  `thundera check` but the fft stack wasn't up. Expect the first real run to
  find config bugs — that's the point of running it.
- **Vision (`--vision`) has never been exercised here.** Code carried over
  unchanged from fft, where it worked; unverified in this package.
- **Three of the four copies are still out there** (`ember-lite`, `ember-pro`,
  `fft-psx-vera`). The drift problem is one-quarter solved.

### First real catch (2026-07-29)

On `ember-pro` :9096, a link rendering at **2.2:1 contrast** — unstyled default
browser blue (`rgb(0,0,238)`) on black. `app.js` injects an `<a>` into
`#power-status`; the stylesheet only colours links under `.commons`, `.hiw` and
`.cm-hero-credit`. Only appears on "locked" (shared) instances, so ember-lite is
clean and the public-facing one is not. **Not yet fixed — it is another repo's
bug, reported to Rod.**

## Get running in two minutes

```bash
cd ~/eye-of-thundera
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/playwright install chromium      # if ~/.cache/ms-playwright is empty
.venv/bin/python -m pytest -q              # expect 108 passed
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
tests/            108 tests; test_browser.py auto-skips without Playwright
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
5. **`COLLECT_JS` thresholds do not move.** It was tuned against a real app over
   six themes, and that tuning is most of the value. Noisy for your project? Set
   `severity.<kind> = "off"` in *your* config. The collector has been edited
   exactly once, on 2026-07-29, and only because it was reading the wrong input
   — the contrast compositor treated elements painted *above* the text as its
   background. A correctness fix is not a threshold change, and that distinction
   is the whole rule.
6. **`schema_version` is additive-only.** Agents parse this. Bump the version if
   you must change a key's meaning.
7. **An abstention is reported, not hidden.** `summary.unverified` counts what
   the collector declined to judge, and it is counted **regardless of whether
   `obscured` is emitted as a finding**. Turning the finding off must hide the
   noise, never the fact. Three outcomes: pass, fail, *I could not tell*.

8. **A demoted flaky finding is still a finding.** `--retries` downgrades a
   non-reproducing error to a warning; it never deletes it. An error that comes
   and goes means the app is unreliable, which is its own bug.

9. **The Eye does not replace behavioural tests.** When migrating a consumer,
   delete its *inspector*; do not touch its functional smoke, even when that
   smoke also drives Playwright. The Eye judges how a page looks and has no
   notion of a content assertion — "the route badge reads Pacifist", "chat
   replied", "the roster reseated" are all outside it. An earlier draft of this
   file suggested deleting `undertale-vera/tools/frontend_smoke.py`; that would
   have removed the front end's only CI merge gate.

## Known gaps and rough edges

- `settle_ms` is per-surface, not per-viewport. A slow mobile view has to make
  the desktop one wait too.
- `pre_clicks` are per-surface, not per-viewport. The `?` optional prefix covers
  the responsive-nav case; anything more complex needs duplicate surfaces.
- No video/trace capture — you get the final screenshot, not the path there.
- The `http` engine can't verify hash routes (it says so in `engine_note`), and
  does nothing beyond status codes even though stdlib `html.parser` would let it
  check titles, `lang`, `alt`, and 404ing assets.
- Vision is Ollama-only, and **still never exercised here**.
- The eye animation is a fixed 6-frame sequence; it does not reflect sweep
  progress while a long run is under way.
- `thundera init` writes a static template; it doesn't crawl the app to suggest
  surfaces.
- No accessibility checks beyond contrast and tap targets, despite
  "accessibility" being a package keyword.
- The baseline compares *findings*, not pixels — a layout can break in ways no
  named check catches.
- **Contrast abstains on gradients and background images.** It always did; as of
  this session it says so. `summary.unverified` counts them (undertale-vera
  reports 93). That is not a defect count — it is the answer to "how much did
  you actually see?". Set `severity.obscured = "warn"` for the per-element list.
- Only one origin per config. `fft-psx-vera` serves its API on :7900 and its app
  on :7901; the API origin is currently baked into `discovery.url`, so switching
  environments means editing the TOML.

## Next steps, in order

1. ~~**Migrate a consumer.**~~ **Done** — `undertale-vera`, 2026-07-29. Its
   `inspector.py` is deleted; `thundera.toml` + `requirements-qa.txt` are
   committed there. See the BUILDLOG entry for what the example config was
   missing (`commons`, and the four `/api/*` surfaces).

2. ~~**Add the seven hidden undertale-vera views.**~~ **Done** — 2026-07-30.
   `examples/undertale-vera.toml` now covers **20 surfaces, 40 page-views**, up
   from 13 and 26. The `with-save` profile uploads a synthetic save once per
   context; `navigate = "once"` stops the per-surface reload from throwing it
   away. Immediate payoff: nine genuine `tap_target` warnings on `council` at
   m390 (56×21px "talk" buttons), on a view that had never been looked at.

   Three things learned, all worth keeping:

   - **The fixtures already existed.** An earlier draft of this file asked Rod
     to supply one. `undertale-vera/tests/fixtures/file0_pacifist` (30 bytes)
     and `undertale_pacifist.ini` (96 bytes) have been there since July and are
     already synthetic. Both are now copied into `examples/fixtures/`.
   - **A loaded save lives in memory only** — nothing in `localStorage` — so the
     engine's per-surface `page.goto()` destroyed it. That is what `navigate =
     "once"` exists to fix.
   - **Under `navigate = "once"` every surface must select its own view**,
     including the one the app opens by default, because the page arrives
     showing whatever the previous surface left. `chat` needed an explicit
     `[data-view="chat"]` click it never needed before.

   **A warning about verifying work like this.** The first attempt reported
   seven clean surfaces with seven distinct screenshot checksums — and all seven
   were the same saves view. This app re-randomises its ambient quote and lore
   panels every load, so byte differences prove nothing. The build log's
   "byte-identical sizes" tell is necessary, not sufficient. Assert with a
   `wait_for` on the view's own container, which fails honestly, and then open a
   screenshot and look at it. Every surface in the example config now carries
   such an assertion; that is the pattern to copy.

3. **Give the remaining consumers the same treatment.** The example config's
   `wait_for`-per-surface pattern should be the default for any click-routed
   app, and `undertale-vera`'s own `thundera.toml` is now behind this copy —
   syncing it is Rod's call, and it is what would put the seven views under his
   local gate too.

4. **Then `ember-lite` / `ember-pro`.** Correction to an earlier draft of this
   file: it said "neither app has been surveyed for views yet", implying a
   survey is the work. It mostly isn't — both are forks of the undertale-vera
   app, expose the **same fifteen `data-view` names**, and use the same `uv_*`
   localStorage keys. Their `thundera.toml` is close to a copy with a different
   `name` and `base`. Re-verify the saves opener and the drawer selector, keep
   the four `/api/*` surfaces. ember-pro's own 2.2:1 contrast bug is still
   unfixed in that repo, so it cannot be a clean baseline until it is.

5. **Run the fft config for real** with its stack up. Expect and fix config
   bugs. Note it is the one consumer needing two origins (see *Known gaps*), and
   the only one that exercises `--vision`, which has never run in this package.

6. **MCP server** — after step 5, so the tool surface is designed against real
   usage. `api.look()` is the seam; this is an adapter, not a rewrite. Return
   screenshots as MCP *image content*, not paths, so a vision-capable agent
   actually sees the app.

7. Answer the open questions in `docs/VISION.md` (public vs private; is "eyes"
   web-only; does it grow a memory; who else runs it — that last one would
   reorder step 6).

### Deferred, with the reasoning intact

Worked up in the fourth session as part of a list of twelve; Rod took the first
three and deferred these. Roughly in order of value:

- **Decide whether the a11y pass should default on.** It ships opt-in so that
  upgrading cannot change an existing run, but the noise that justified that is
  not visible on the three live apps (2 findings each, no `no_lang`/`no_landmark`
  at all). Revisit once ember and fft have run it. The open question is the two
  document-level checks: on a single-page app they are one fact repeated per
  page-view, and may belong in `meta` rather than in `findings`.
- **Focus visibility** — the one a11y check considered and not built. Detecting
  `:focus { outline: none }` with no replacement needs the CSSOM rather than
  computed style, and a wrong answer here is worse than no answer.
- **Visual diffing** — store baseline screenshots, emit `visual_diff` above a
  configurable changed-pixel ratio. Pillow extra; degrades to a stated skip.
- **Per-viewport `settle_ms` / `pre_clicks`** — accept a table keyed by viewport
  label as well as today's scalar.
- **Multi-origin** — an `[origins]` table plus `--origin name=url`.
- **A smarter `http` engine** — stdlib `html.parser` only, no new dependency.
- **Perf/weight budgets** — `[budgets]`, off unless declared, because
  environment-sensitive numbers should never fail a run nobody opted into.
- **`init --crawl`** — scaffold a config by clicking through the app. Worth
  noting this does *not* unblock ember (see step 3); it matters for the fifth
  app and every one after.
- **Waivers** — accept one finding on one surface with a reason and an expiry,
  between the blunt instruments of `severity = "off"` and a whole baseline.
- Cheaper: evidence capture (trace + DOM snapshot on error), parallel sweep
  (`--concurrency`, one browser *per worker thread* — the sync dispatcher is
  per-thread, so sharing a browser across threads is not safe), a self-contained
  HTML report, run-dir pruning, a global `--deadline`.

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
