# Architecture

Ten modules, one entry point, one data shape that survives end to end.

```
                    thundera.toml
                         │
                    ┌────▼─────┐
                    │  config  │  parse, validate, resolve {params}
                    └────┬─────┘
                         │  Config
                    ┌────▼─────┐
              ┌─────│   api    │────────────┐   look() — the single entry point
              │     └────┬─────┘            │
              │          │ Config+params    │
              │     ┌────▼─────┐            │
              │     │  driver  │ browser ── │ ──► Playwright ──► page
              │     │          │ http    ── │ ──► urllib
              │     └────┬─────┘            │
              │          │ raw measurements │
              │     ┌────▼─────┐            │
              │     │  checks  │ COLLECT_JS + analyze() → findings
              │     └────┬─────┘            │
              │          │  records         │
    ┌─────────┴───┬──────┴──────┬───────────┴──┐
    │  montage    │   vision    │   baseline   │   optional passes
    └─────────┬───┴──────┬──────┴───────┬──────┘
              │          │              │
         ┌────▼──────────▼──────────────▼────┐
         │              report               │  findings.json + report.md
         └────────────────┬──────────────────┘
                          │
                     ┌────▼────┐
                     │   cli   │  argv → look() → stdout/exit code
                     └─────────┘
```

## Modules

| Module | Lines | Responsibility |
|---|---|---|
| `config.py` | ~340 | `thundera.toml` → validated `Config`. Surfaces, viewports, profiles, `{param}` resolution. **The layer that makes the Eye app-agnostic.** |
| `checks.py` | ~290 | `COLLECT_JS` (the in-page collector) + `analyze()` (raw → findings with severities). |
| `driver.py` | ~230 | Two engines. Visits every (surface × profile × viewport), measures, screenshots. |
| `api.py` | ~180 | `look()` — orchestrates discovery, sweep, vision, montage, baseline, artifacts. |
| `report.py` | ~150 | The JSON contract + Markdown report + exit codes. |
| `cli.py` | ~250 | `look` / `init` / `check` / `surfaces`. Thin over `api`. |
| `baseline.py` | ~70 | Flatten, diff, save. "What's new since accepted?" |
| `vision.py` | ~65 | Optional Ollama vision-model critique. Best-effort by contract. |
| `montage.py` | ~85 | Health-coloured thumbnail grids. Needs Pillow. |
| `eye.py` | ~145 | The ASCII eye: opening animation + verdict. **stderr only, tty only.** |

## The one entry point

Everything goes through `api.look(config, **options) -> LookResult`.

The CLI is an argument parser over it. The planned MCP server will be a tool
definition over it. Neither gets its own logic, so the two can never drift
apart, and any behaviour fix lands in all consumers at once.

**If you are adding a feature, it belongs in `api.look()` or below it — never
in `cli.py`.** The only things that legitimately live in `cli.py` are argument
parsing, stdout formatting, and exit-code translation.

## Data shapes

### `Config` (frozen dataclasses)

```
Config
├── name, base, routing ("path" | "hash"), navigate ("always" | "once")
├── viewports  : tuple[Viewport]   label, width, height, scale, mobile
├── profiles   : tuple[Profile]    name, seeds{}, setup(), cookies(), headers{}
├── surfaces   : tuple[Surface]    key, path, group, settle_ms,
│                                  inventory{}, pre_clicks(), profiles?, setup()
├── discovery  : Discovery | None  url, params{param: path-expression}
├── params     : dict              static {param} values (win over discovery)
├── seeds      : dict              localStorage under every profile
├── severity   : dict              kind → error|warn|off
└── net_ignore : tuple             URL substrings whose 4xx/5xx is expected

Step                               one precondition action
├── kind      : str                click|fill|upload|wait_for|eval|goto
├── value     : str | dict         selector, or {selector, text|path}
└── optional  : bool               the "?" prefix — allowed not to apply
```

`navigate` decides whether each surface gets a fresh page load. `"always"` (the
default) reloads before every surface, which is isolation: nothing surface A did
can reach surface B. `"once"` reuses the page whenever the resolved URL is
unchanged — necessary when a precondition establishes state the app holds in
memory, because a reload destroys it, and on a click-routed SPA where every
surface is `/` the reload was buying nothing anyway.

Reuse is keyed on the URL, not on "skip everything after the first load", so a
surface with a genuinely different path still navigates. Records carry
`"nav_note": "reused page (navigate = once)"` — a page-view measured without a
fresh load is a different claim, and the JSON should not quietly imply
otherwise. The cost, and the reason it is opt-in: each surface arrives showing
whatever the previous one left, so every surface must select its own view.

`seeds` only reach localStorage. `Step` is how the Eye reaches states that need
more than that — a save file uploaded, a session cookie, a logged-in profile.
Profile-level `setup` runs **once per browser context** before any surface;
surface-level `setup` runs per surface, after load and *before* `pre_clicks`
(setup establishes the state, `pre_clicks` navigates to the view).

`${VAR}` in any cookie, header, seed or param is expanded from the environment
at config-load time. An unset variable raises `ConfigError` rather than
substituting an empty string, and a missing `upload` fixture fails at load
rather than mid-sweep — both so that a credential problem is never reported as
the app's fault.

Frozen throughout. `select()` and `with_base()` return narrowed copies rather
than mutating — so a CLI filter can never corrupt the loaded config.

### `record` — one page-view

```jsonc
{
  "surface": "home", "group": "core", "profile": "dark", "viewport": "m390",
  "path": "/", "url": "http://host/",
  "screenshot": "screenshots/home__dark__m390.png",
  "inventory": { "nav": {"x":0,"y":0,"w":390,"h":56,"font":"16px"} },
  "findings": [ { "kind": "...", "severity": "...", "detail": "...", "anchor": "...",
                  "flaky": true } ],       // flaky: did not reproduce on retry

  // any of these may appear:
  "skipped": "no value for {project_id}",     // never reached — and says why
  "unverified": { "contrast": 4 },            // looked at, could not judge
  "nav_note": "TimeoutError (continuing after settle)",
  "click_notes": ["#menu: never appeared or never became clickable"],
  "setup_notes": ["click #load: skipped (optional) — never appeared"],
  "measure_error": "...", "screenshot_error": "...",
  "status": 200, "engine_note": "status-code only (no browser available)"
}
```

`detail` is human prose and may carry pixel values that jitter between runs.
`anchor` is the stable identity (usually the CSS path) — **baseline diffing keys
on `anchor`, never on `detail`.** Get that backwards and every run reports the
whole app as changed.

`unverified` counts measurements the collector *declined* to make — text whose
background is a gradient or an image, where guessing at pixels would be a lie.
It is summed into `summary.unverified`, and it is reported independently of
`severity.obscured`, so switching the finding off hides the noise without hiding
the fact that something went unchecked. Three outcomes, not two: pass, fail, and
*I could not tell*.

### The findings body — the public contract

See `README.md` § *For agents* for the full example. Rules:

- `schema_version` is **additive-only**. New keys may appear; existing keys
  never change meaning and never disappear without a version bump.
- The body names its own artifacts (`artifacts.run_dir`, `.json`, `.montages`)
  so a reader can find the screenshots without being told where they went.
- It is written to disk **after** artifacts are recorded into it — the file on
  disk and the in-memory body are identical. (This was a real bug once; the
  test `test_findings_json_is_written_and_parseable` guards it.)

## How `{param}` resolution works

Entity ids must never be hardcoded in config, so surfaces declare placeholders
and the app supplies the values at run time.

1. `[params]` static values are seeded first — they always win.
2. `[discovery]` GETs a JSON document from the app.
3. Each `params.X = "dotted.path.0"` expression is looked up in that document.
   Numeric segments index lists.
4. An expression may reference an **already-resolved** param —
   `entities.character_ids.{project_id}.0` — so resolution loops until it stops
   making progress. That also terminates circular references instead of hanging.
5. A surface whose placeholders can't all be filled is **skipped with a stated
   reason**. Not an error, never a guess.

A dead discovery endpoint degrades the same way: the sweep runs, parameterised
surfaces skip, `meta.discovery.ok` is `false`.

## The two engines

| | `browser` | `http` |
|---|---|---|
| Needs | Playwright + Chromium | nothing |
| Sees | layout, console, network, JS errors, screenshots | status codes |
| Matrix | surface × profile × viewport | surface only |
| Purpose | the actual product | still say something true on a bare box |

`engine="auto"` picks `browser` when Playwright imports, else `http`. Both emit
the same record shape, so `report` and `baseline` never branch on engine.

The `http` engine is honest about its limits: a hash-routed path lives entirely
client-side, so it checks the shell and says
`"hash route not verifiable without a browser"` rather than implying it verified
the route.

## The in-page collector

`checks.COLLECT_JS` is one `page.evaluate()` returning raw measurements. It came
over from the Vera Inspector, where it was tuned against six themes × two
viewports of a real app. That tuning is most of the value here, and the standing
rule is that thresholds do not move.

It has been edited exactly once, on 2026-07-29, to fix the contrast compositor:
`elementsFromPoint` returns the stack topmost-first, and the walk was treating
elements painted *above* the text as its background. The stack is now sliced at
the element's own position so only what is genuinely beneath it composites. See
the build log for why that counted as a correctness fix rather than a threshold
change.

Notes for anyone tempted to edit it:

- Every check caps its output (`>= 12`, `>= 15`, `>= 20`) so a pathological page
  can't produce a hundred-thousand-item array.
- **Centering** only judges elements *alone* in their centering context. An icon
  flex-centered beside its text sibling is correctly off-centre.
- **Contrast** composites the real paint stack via `elementsFromPoint`, so it
  sees overlay siblings and translucent scrims an ancestor walk misses — but
  only the part of the stack *below* the element. When the hit test does not
  reach the element at all (clipped by a scroll container), it falls back to the
  ancestor chain, which is what sits behind the text in normal flow and can
  never include a fixed overlay. It **skips gradients and background images**
  rather than guessing at pixels, and every skip is counted in `unverified`.
- **Tap targets** apply on mobile viewports only (`MOBILE_ONLY` in `checks.py`).

If a threshold is noisy for one project, that project sets
`severity.<kind> = "off"`. Do not loosen the check for everyone.

## Severity and exit codes

```
error   fails the run          broken_img, console_error, net_4xx, js_error,
                               doc_overflow, pre_click_failed, setup_failed
warn    reported only          contrast, clipped_text, row_misalign,
                               off_center, tap_target, spacing
off     not emitted at all     obscured (by default), plus anything config
                               turns off
```

```
exit 0   clean
exit 1   errors present, or --warn-as-error with warnings,
         or new errors vs baseline, or --fail-on-new with any new finding
exit 2   usage or config error
```

`pre_click_failed` and `setup_failed` are **errors** by design. If the click
that opens a view misses, or the save that unlocks it never uploaded, everything
measured afterwards is some other page wearing that surface's name — and would
otherwise report clean. See `docs/VISION.md` § *Principles*.

`--retries N` re-runs only the page-views that errored, via an `only` allowlist
of `(surface, profile, viewport)` triples passed to the sweep. An error that
reproduces stands; one that does not is marked `flaky` and demoted to `warn`.
Demoted, never deleted — an error that comes and goes is still information.
Retry screenshots go to `retry-N/` so first-run evidence survives.

## Testing

```
tests/test_config.py       config parsing, validation, {param} resolution
tests/test_findings.py     analyze(), the report contract, baseline diffing
tests/test_end_to_end.py   real sweeps + the CLI, http engine, no browser needed
tests/test_browser.py      real Chromium; auto-skipped without Playwright
tests/test_eye.py          the animation, and proof it never touches stdout
```

`test_end_to_end.py` and `test_browser.py` spin up a real `ThreadingHTTPServer`
over a temp directory — no mocks of the thing under test. The browser suite
asserts the properties only a renderer can prove: seeds landing before first
paint, a required click that misses failing the run, an optional one not.

Run: `.venv/bin/python -m pytest -q` (103 tests, ~90s with the browser suite).
