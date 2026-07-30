# Build log

Append-only. Newest entry at the top. One entry per session or substantive
change: what was done, **why**, and anything that surprised us.

This is the archaeological record — when someone asks "why on earth does it do
*that*", the answer should be findable here. Do not rewrite history; if an
earlier decision was reversed, add a new entry saying so.

---

## 2026-07-29 (fourth session) — The truth pass

**What:** Three changes, chosen from a worked-up list of twelve. Rod picked the
cut: fix what is actually wrong before adding anything new. 69 → 97 tests.

### 1. The contrast compositor was reading the wrong pixels

The known false-positive class from the last session is fixed, and the root
cause was smaller and worse than the handoff guessed.

`document.elementsFromPoint()` returns the hit-test stack **topmost first**. The
layer walk did this:

```js
for (const n of chain) {
  if (n === el || el.contains(n)) continue;   // self / children
  ...treat n as a background layer...
}
```

Everything that was not the element or its descendant was treated as background
— including the elements painted **above** it. A `position: fixed` bottom bar
covering text at scroll 0 therefore *became* that text's background. The fix is
one line: find the element's own index in the stack and composite only
`chain.slice(idx + 1)`.

**What surprised us:** the bug did not only invent findings, it also *hid* them.
White-on-black under a white bar reported as "white on white, 1:1" — but
dark-grey-on-black under the same bar read as dark-grey-on-*white*, which passes
WCAG comfortably and was silently dropped. Both directions are covered by tests
now; reintroducing the one-line bug fails both.

Verified against the live app: undertale-vera at m390 went from 7 contrast
warnings to 0, and all 7 were the artifact. ember-pro's genuine
`span#power-status > a — 2.2:1` still reports (at both viewports now), which is
the canary that the fix did not simply blind the check.

**A second case, found while verifying.** 41 elements had no hit-test result at
all — they are clipped by a scroll container, so the point belongs to whatever
*is* painted there. The first draft abstained on those. That was worse than
necessary: the ancestor chain is exactly what sits behind the text in normal
flow, and a fixed overlay can never be an ancestor. Falling back to it recovered
all 41 with correct backgrounds.

**This is the first deliberate edit to `COLLECT_JS`,** which guardrail 5 says is
carried over unchanged. That rule exists to stop thresholds being loosened to
quiet a noisy project. No threshold moved here — the collector was reading the
wrong input — and `docs/HANDOFF.md` proposed this exact fix as one of two
candidates. The other candidate (`scrollIntoView` then re-sample) was rejected:
it mutates page state mid-measure, so the screenshot would no longer show what
was measured.

### 2. A third outcome: "I could not tell"

The collector has always skipped text on gradients and background images —
guessing at pixels it cannot read would be a lie. But it skipped them
*silently*, which is indistinguishable from a pass. A page whose text all sat on
gradients reported "no contrast problems" having checked nothing.

Now every abstention is counted: `rec.unverified` per page-view, summed into
`summary.unverified`. The finding kind `obscured` carries the per-element reason
and defaults to `"off"` — one decorative hero can produce a dozen and none is a
defect — but **the count is reported regardless of the severity setting**, so
switching the finding off hides the noise without hiding the fact. undertale-vera
reports 93 of these; that number was always true, it was just never said.

Three outcomes now, not two: pass, fail, and *I could not tell*. Additive, so
`schema_version` stays 1.

### 3. Preconditions — the Eye could not see most of its flagship consumer

`examples/undertale-vera.toml` carried a note that seven views (council,
timeline, journal, constellation, chronicle, judgment, reports) bounce to the
saves view unless a save has been read, "so they are not listed here — add them
once a save is seeded." Seeds only reach `localStorage`, and what those views
need is a **file upload**. So 7 of 16 views were permanently invisible, and the
config said so in a comment nobody had actioned.

`setup` steps fix that: `click`, `fill`, `upload`, `wait_for`, `eval`, `goto`,
with the same `?` optional prefix `pre_clicks` uses. Profile-level setup runs
once per browser context (state persists across the navigations that follow);
surface-level runs after load and before `pre_clicks` — setup establishes the
state, `pre_clicks` navigates to the view.

Per-profile `cookies` and `headers` came along with it, because ember-pro's
known contrast bug only appears on "locked" shared instances and that is
server-side state a `localStorage` seed cannot reach.

A failed required step is `setup_failed`, an **error**, for exactly the reason
`pre_click_failed` is. A failed *profile-level* step taints every record in that
context — one bad precondition must not let nine surfaces report clean.

`${VAR}` expansion landed here too, so a token never has to be committed. An
unset variable is a hard `ConfigError` rather than an empty string: a blank
`Authorization` header produces a sweep of 401s that look like the app's fault.
A missing `upload` fixture fails at config-load for the same reason — better
than discovering it mid-sweep with nine surfaces already measured wrong.

### 4. `--retries N`

`networkidle` never settles on polling/SSE apps and clicks miss transiently. The
retry re-runs **only** the page-views that errored, via an `only` allowlist of
`(surface, profile, viewport)` triples — `cfg.select()` would have re-run the
whole cross product those triples happen to span. An error that reproduces
stands; one that does not is marked `"flaky": true` and demoted to `warn`.

Demoted, **never deleted.** An error that comes and goes is still information —
it means the app is unreliable, which is its own kind of bug. Silently dropping
it would be the same class of lie as a silent pass. Retry screenshots go to
`retry-N/` so the first run's evidence survives.

### Also

Stale metadata corrected: `CLAUDE.md` said 60 tests, `pyproject.toml`'s
`Homepage` pointed at `eye-of-thundera` when the remote is `eyeofthundera`, and
`README.md` advertised a PyPI install for a package that is not on PyPI. The
README's config reference was also missing `[network]` and `[vision]`, both of
which the reference example uses.

**Left undone, deliberately:** the other nine of the twelve — a real
accessibility pass, visual diffing, per-viewport `settle_ms`, multi-origin, a
smarter `http` engine, perf budgets, `init --crawl`, waivers, and the MCP
server. They are listed in `docs/HANDOFF.md` § *Next steps* with the reasoning
intact. MCP stays after a third consumer, per VISION — the tool surface should
be designed against real usage, not guessed at.

---

## 2026-07-29 (later still) — First consumer: undertale-vera

**What:** No change to `thundera/` at all. `undertale-vera` deleted its vendored
`inspector.py` and adopted the package — the first time a copy has actually
died, which is the outcome the project exists for. One of four down.

**How it landed there:** `examples/undertale-vera.toml` copied to that repo's
root as `thundera.toml` (found by upward search, so `thundera look` works from
anywhere in the tree), plus a `requirements-qa.txt` pinning
`eye-of-thundera[all] @ git+https://github.com/xsytrance/eyeofthundera.git`.
Its `.thundera/` is gitignored. Nothing in its CI installs or runs us — the
sweep stays a local/manual gate there, deliberately.

**Two things the example config was missing**, now true of both copies:
- The `commons` view was never listed. It exists, has a `[data-view]` button,
  and was simply overlooked — 9 UI surfaces, not 8.
- The four `/api/*` paths the old inspector probed (`health`, `characters`,
  `projects`, `lore`) had no equivalent, so adopting us would have *lost*
  coverage. Added as `group = "api"`. Worth recording: they produce **zero**
  noise. A JSON document rendered in a browser has no layout, so the visual
  checks find nothing on it by construction, and what you get is the status
  code — exactly what was wanted, with no severity tuning needed.

**What was deliberately not carried over:** the inspector's `REQUIRED_ASSETS`
list (three hardcoded static paths, fetched over HTTP to prove they exist). The
browser engine already records every request the real page makes, so a missing
`app.js` shows up as a `network` finding on the surface that needed it. A
hand-maintained asset list is strictly worse: it drifts, and it only ever
proves the files it happens to name.

**The correction that matters — `tools/frontend_smoke.py` is NOT ours to
replace.** `docs/HANDOFF.md` had listed it as a second deletion candidate
("and ideally `tools/frontend_smoke.py`"). That was wrong, and reading it
properly is what caught it. Both use Playwright and that is the entire
resemblance. The smoke uploads save fixtures, asserts the route badge reads
Pacifist, sends a chat message and waits for the reply, checks a Deltarune save
flips the app to Dark World and reseats the roster, and fires an easter egg. It
is a *functional* test, and it is that front end's only CI merge gate. The Eye
has no notion of a content assertion — it judges how a page looks, not what the
app does. Deleting it would have silently removed a merge gate. **The Eye does
not subsume behavioural testing, and the HANDOFF should never have implied it
could.** Fixed there.

**Result on the consumer:** 13 surfaces × 2 viewports = 26 page views, 0 errors,
0 skipped, 57 warnings (42 tap-target, 15 contrast), all mobile. The old
inspector knew 5 URL paths and could see none of the 8 click-reached views,
because that app has no routing. `--engine http` re-verified there: 13/13 200.

**Still open:** `ember-lite` and `ember-pro` (byte-identical copies of the file
undertale-vera just deleted, so this entry is most of their thinking), then
`fft-psx-vera`, whose config has still never been run against a live stack.

---

## 2026-07-29 (later) — The Eye itself, and first use in anger

**What:** Added `thundera/eye.py` — an ASCII eye that opens while the sweep
runs and closes on a verdict. Then used the tool on three live apps.

### Why decoration was the right call here

Rod asked to see "your ASCII animation", which didn't exist. For a project
named after an artefact that grants *sight beyond sight*, a CLI that opens an
eye is the brand doing work rather than a gag — and it was made to earn its
place: **the iris colour at the end of a run is the verdict.** Cyan while
looking, then green / amber / red. The thing you watch is the thing you read.

### Containment, which is the part that actually mattered

The agent contract says stdout is the product. So the eye:

- writes to **stderr only**, never stdout (test asserts it)
- is off unless stderr is a terminal
- is forced off under `--json`, `--quiet`, `--no-animation`, `THUNDERA_NO_ANIM=1`
- respects `NO_COLOR`

Frames are **generated on a fixed grid**, not hand-drawn — the hand-drawn first
pass had misaligned parens on two frames, which is exactly the kind of thing
this tool exists to catch in other people's software.

**A real bug found by its own test:** cursor-rewind escapes (`\033[3A\033[J`)
were being written even to a non-tty stream, so redirected stderr would collect
control codes. Now a non-tty draws the open eye once with no escapes at all.
`test_a_plain_stream_gets_no_escape_codes_at_all` guards it.

### Using it — three live apps

| App | Result |
|---|---|
| `undertale-vera` :9092 | 3 warnings — tap targets under the 32px floor |
| `ember-lite` :9095 | the same 3 |
| `ember-pro` :9096 | those 3 **plus a genuine accessibility bug** |

The ember-pro find is the first thing the Eye caught that nobody knew about:

```
contrast | span#power-status > a — 2.2:1 (needs 4.5:1)
           [rgb(0, 0, 238) on rgb(0, 0, 0)] "run Ember yourself..."
```

`rgb(0,0,238)` is **unstyled default browser blue**. `app.js` injects an `<a>`
into `#power-status`, and the stylesheet only colours links under `.commons`,
`.hiw` and `.cm-hero-credit` — so this one falls back to the UA default on a
black background. It appears only when the instance is "locked" (the shared
deployment), which is why ember-pro has it and ember-lite doesn't: the bug is
on the public-facing instance, in the very sentence telling people how to run
Ember themselves.

Worth noting *why* the deterministic check caught it: the contrast check
composites the real paint stack, so it read the true black behind the link
rather than guessing from an ancestor.

Tests: 60 → 69.

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
