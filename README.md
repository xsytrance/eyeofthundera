# Eye of Thundera

**Sight beyond sight — for agents.**

Point it at a running web app. It comes back with what a careful reviewer would
have noticed: broken images, console and network failures, horizontal overflow,
clipped text, misaligned rows, off-centre boxes, cramped tap targets, failing
contrast — across every screen size and theme you declare, with screenshots and
a machine-readable verdict.

An agent writing frontend code is otherwise working blind. It can run the tests
and read the HTML, but it cannot see that the button it just added is 20px tall
on a phone, or that its text is grey-on-grey. This gives it eyes.

```console
$ thundera look http://127.0.0.1:9092
Eye of Thundera — app @ http://127.0.0.1:9092 [browser]
  [default/m390] home: 0 err, 3 warn
  [default/d1280] home: OK
1 clean · 1 warn · 0 error · 0 skipped  (0 errors, 3 warnings)
findings: .thundera/runs/20260729-081207/findings.json
```

Those three warnings were real: two 23×19px refresh buttons and an 80×28px menu
button, all below the 32px tap-target floor, on a view that looked fine to
everyone who had only ever opened it on a desktop.

---

## Install

Not on PyPI yet — install from the repo:

```bash
pip install "eye-of-thundera[all] @ git+https://github.com/xsytrance/eyeofthundera.git"
playwright install chromium
```

The core has **zero dependencies** — that is deliberate. Without Playwright it
degrades to a status-code sweep rather than refusing to run, so it still tells
you something true on a bare box.

| Extra | Gets you |
|---|---|
| *(none)* | `http` engine: status codes only |
| `[browser]` | the real eyes — layout, console, screenshots |
| `[montage]` | thumbnail grids, health-coloured |
| `[vision]` | local vision-model critique (needs Ollama) |
| `[all]` | everything |

## 30 seconds

```bash
thundera look http://localhost:3000       # zero config, front page, 2 viewports
thundera init                             # write a thundera.toml
thundera check                            # validate it, no sweep
thundera look                             # sweep everything it declares
```

## For agents

The contract, which is the whole point of the project:

```
stdout   the product. With --json it is the findings JSON and nothing else.
stderr   progress chatter, and the eye. Always safe to discard.
exit 0   clean
exit 1   findings that count as failure
exit 2   usage or config error
```

The eye animation draws on **stderr and only when stderr is a terminal**, so it
can never contaminate what you parse. It is additionally forced off by `--json`,
`--quiet`, `--no-animation` and `THUNDERA_NO_ANIM=1`, and respects `NO_COLOR`.

```bash
thundera look http://localhost:3000 --json -q
```

```jsonc
{
  "schema_version": 1,
  "tool": "eye-of-thundera",
  "meta": { "when": "...", "app": "...", "base": "...", "engine": "browser",
            "profiles": ["default"], "viewports": ["m390", "d1280"],
            "params": {}, "unresolved_params": {}, "duration_s": 6.2 },
  "summary": { "page_views": 2, "clean": 1, "with_warnings": 1, "with_errors": 0,
               "skipped": 0, "errors": 0, "warnings": 3, "unverified": 4 },
  "records": [
    { "surface": "home", "profile": "default", "viewport": "m390",
      "url": "http://localhost:3000/", "screenshot": "screenshots/home__default__m390.png",
      "inventory": { "nav": { "x": 0, "y": 0, "w": 390, "h": 56, "font": "16px" } },
      "unverified": { "contrast": 4 },
      "findings": [
        { "kind": "tap_target", "severity": "warn",
          "detail": "button#refresh 23×19.2px “↻”", "anchor": "button#refresh" }
      ] }
  ],
  "artifacts": { "json": "...", "run_dir": "...", "montages": ["..."] }
}
```

`schema_version` is additive-only: new keys may appear, existing keys never
change meaning or vanish without a bump.

The JSON names its own artifacts, so an agent that reads it can find the
screenshots without being told where they went — and can then *look* at them.

Or use it as a library — same code path as the CLI:

```python
from thundera import Config, look

result = look(Config.discover() or Config.minimal("http://localhost:3000"))
print(result.summary)                       # {'page_views': 2, 'clean': 1, ...}
for rec in result.body["records"]:
    for f in rec["findings"]:
        print(rec["surface"], f["kind"], f["detail"])
```

## The eye

Run it in a terminal and it opens an eye while it looks, then closes on a
verdict whose iris colour *is* the result — cyan while working, then green,
amber or red.

```
     .------------------------------.
    (     .--------------------.     )
    (     |                    |     )
    (     |                    |     )
    (     |        (o)         |     )
    (     |                    |     )
    (     |                    |     )
    (     '--------------------'     )
     '------------------------------'
              sight beyond sight
```

Turn it off with `--no-animation` or `THUNDERA_NO_ANIM=1`. It is already off
whenever stderr is not a terminal.

## What it checks

| Kind | Default | Means |
|---|---|---|
| `broken_img` | error | `<img>` that resolved to nothing |
| `console_error` | error | anything the page logged at error level |
| `net_4xx` | error | a request that came back ≥400 |
| `js_error` | error | an uncaught exception |
| `doc_overflow` | error | the page scrolls sideways |
| `pre_click_failed` | error | a required click missed — **the surface was never reached** |
| `setup_failed` | error | a required precondition didn't apply — **measured in the wrong state** |
| `contrast` | warn | text below WCAG AA against its composited background |
| `obscured` | off | text whose background could not be resolved — see below |
| `clipped_text` | warn | `overflow:hidden` cutting real text off |
| `row_misalign` | warn | same-tag siblings in a row with mismatched tops |
| `off_center` | warn | an element claiming to be centred that isn't |
| `tap_target` | warn | interactive element under 32px (mobile viewports only) |
| `spacing` | warn | a stack whose gaps are near-misses of each other |

Thresholds are conservative on purpose: a finding should mean *"a human would
call this sloppy"*, not *"pixel trivia"*. If you have decided you don't care
about one, turn it off in config rather than loosening the check for everyone:

```toml
[severity]
spacing = "off"
contrast = "error"     # or promote it, once you're clean
```

### What it *couldn't* check

Contrast needs to know the colour behind the text. Sometimes it can't: the
background is a gradient or an image, and guessing at pixels is exactly the kind
of lie this tool refuses to tell. Those elements are skipped — but never
silently. Every run reports the total:

```json
"summary": { "clean": 13, "errors": 0, "warnings": 0, "unverified": 93 }
```

`unverified` is not a failure count. It is the answer to *"how much did you
actually see?"*, which a run reporting zero warnings cannot otherwise tell you.
For the per-element list and the reason each was skipped, promote the finding:

```toml
[severity]
obscured = "warn"
```

## Baselines — "did my change break anything?"

An absolute count is nearly useless on a mature app; every real UI carries a
tail of accepted warnings, and "38 findings" tells an agent nothing. The delta
is what matters.

```bash
thundera look --update-baseline               # record today as accepted
# ... make changes ...
thundera look --baseline .thundera/baseline.json
# vs baseline: 2 new, 1 fixed
```

New **errors** fail the run on their own. `--fail-on-new` fails on any new
finding, warnings included — the strict setting for CI on a clean codebase.

Findings are matched on an *anchor* (usually the CSS path), not on the detail
string, so a box that moves half a pixel stays the same finding instead of
showing up as one fixed and one new.

## Configuring it

Everything app-specific lives in `thundera.toml`; the engine knows none of it.
`thundera init` writes an annotated starter. The shape:

```toml
[app]
name = "my-app"
base = "http://127.0.0.1:3000"
routing = "path"           # or "hash", for /#/dashboard SPAs
navigate = "always"        # or "once" — see below

[[surfaces]]
key = "dashboard"
path = "/project/{project_id}"
group = "core"             # montage grouping
settle_ms = 2000
inventory = { hero = ".hero" }        # named boxes to record sizes for
pre_clicks = ["?#menu-toggle", ".tab-settings"]
profiles = ["dark"]                   # only shoot under these

[[viewports]]
label = "m390"
width = 390
height = 844
scale = 2
mobile = true

[[profiles]]               # themes, locales, logged-in states
name = "dark"
seeds = { theme = "dark" }             # localStorage, planted before first paint
cookies = [{ name = "sess", value = "${SESSION}" }]
headers = { Authorization = "Bearer ${API_TOKEN}" }
setup = [                              # run once, before any surface
  { click = "#load-save" },
  { upload = { selector = "#save-file", path = "fixtures/pacifist.sav" } },
  { wait_for = "[data-view='council']" },
]

[seeds]                    # applied under every profile
welcome_seen = "1"

[discovery]                # where {param} values come from at run time
url = "http://127.0.0.1:8000/api/diag/ui-map"
params.project_id = "entities.project_ids.0"
params.character_id = "entities.character_ids.{project_id}.0"

[network]                  # 4xx/5xx that is expected and must not fail a run
ignore = ["favicon", "/api/optional-thing"]

[severity]                 # "error" | "warn" | "off" per check kind
spacing = "off"

[vision]                   # surfaces worth the slow local-model critique
sample = ["dashboard"]
```

Four details worth knowing, because they are what make it work on real apps:

**Surfaces without URLs.** Plenty of SPAs switch views on a click, not a route.
`pre_clicks` handles those: same path, different click.

**Optional clicks.** A `?` prefix means "click it if it's there". That is how
you express a responsive nav — a hamburger that exists on mobile and isn't
rendered at all on desktop:

```toml
pre_clicks = ["?#drawer-open", "[data-view='credits']"]
```

A click *without* `?` that misses is an **error**, not a note. This matters
more than it sounds: if the click that opens a view silently fails, everything
after it measures some other page wearing that surface's name — and reports it
clean. The first thing this tool caught when pointed at a real app was seven
mobile surfaces doing exactly that.

**Entity ids stay out of config.** `[discovery]` reads them from the app at run
time. A surface whose params can't be satisfied is *skipped with a stated
reason* — never guessed at, never silently passed.

**Preconditions, when localStorage isn't enough.** Some views only exist once
the app is in a particular state — a save has been loaded, a session exists, a
feature flag is on. `setup` reaches those states:

| Step | Does |
|---|---|
| `click = "#go"` | clicks it (`?` prefix = optional) |
| `fill = { selector, text }` | types into a field |
| `upload = { selector, path }` | sets a file input |
| `wait_for = "#thing"` | waits for a selector |
| `eval = "js"` | runs JS in the page |
| `goto = "/path"` | navigates |

On a `[[profiles]]` block, `setup` runs **once per browser context**, before any
surface — whatever it establishes persists across the navigations that follow.
On a `[[surfaces]]` block it runs per surface, after load and *before*
`pre_clicks`: setup establishes the state, `pre_clicks` navigates to the view.

A required step that doesn't apply is a `setup_failed` **error**, for the same
reason a missed required click is. If a profile-level step fails, every surface
in that context is marked — one bad precondition must not let nine surfaces
report clean.

`${VAR}` in any cookie, header, seed or param is read from the environment, so
a token never has to be committed. An unset variable is a hard error rather than
an empty string, because a blank `Authorization` header produces a sweep of 401s
that look like the app's fault.

**`navigate = "once"`, when the app keeps state in memory.** By default the Eye
reloads before every surface — clean isolation, so one surface can't affect the
next. But plenty of SPAs hold their state in a JS closure rather than
`localStorage`, and for those a reload throws away whatever your `setup` just
established. Set `navigate = "once"` and the page is reused whenever the
resolved URL is unchanged, which on a click-routed app is the entire matrix.

The trade-off is real and it is why this is opt-in: with reuse, each surface
arrives showing whatever the last one left on screen. **Every surface then has
to select its own view**, including the one the app opens by default. Records
say `"nav_note": "reused page (navigate = once)"` so the JSON never implies a
fresh load it didn't do.

Pair it with a `wait_for` on the view's own container. A bare click reports
success even when the app quietly redirects you somewhere else — `wait_for` is
what turns "I clicked it" into "I got there":

```toml
setup = [
  { click = '[data-view="council"]' },
  { wait_for = "#view-council" },      # without this, a bounce looks like a pass
]
```

## Flaky runs

`networkidle` never settles on apps with polling or SSE, and a click can miss
because an animation was still running. `--retries N` re-runs **only** the
page-views that errored:

```bash
thundera look --retries 1
```

An error that reproduces stands. One that doesn't is demoted to a warning and
marked `"flaky": true`, with the reason appended to its detail. It is never
deleted — an error that comes and goes is still information, and dropping it
would be its own kind of lie.

## Vision (optional, advisory)

```bash
thundera look --vision           # sample key surfaces
thundera look --vision all       # every screenshot (slow)
```

Sends screenshots to a local Ollama vision model for the judgment call the
deterministic checks can't make — *"does this read as professional?"* It never
fails a run and never overrides a real finding; a missing Ollama degrades to a
note. Set `THUNDERA_VISION_MODEL` (default `qwen3-vl:8b`) and `OLLAMA_HOST`.

## In CI

```yaml
- run: |
    pip install "eye-of-thundera[all] @ git+https://github.com/xsytrance/eyeofthundera.git"
    playwright install --with-deps chromium
- run: ./start-my-app &
- run: thundera look --report docs/inspector-report.md
```

Exit 1 on errors gates the merge; the Markdown report is a readable artifact.

## Documentation

| | |
|---|---|
| [`docs/VISION.md`](docs/VISION.md) | why this exists, and the principles that are load-bearing |
| [`docs/HANDOFF.md`](docs/HANDOFF.md) | **what is true right now** — start here if you're picking it up cold |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | modules, data shapes, how `{param}` resolution works |
| [`docs/BUILDLOG.md`](docs/BUILDLOG.md) | append-only history — *"why does it do that?"* |
| [`CLAUDE.md`](CLAUDE.md) | working rules for agents in this repo |

Docs are kept current by rule, not by good intentions: a change to `thundera/`
that doesn't touch `docs/HANDOFF.md` is blocked by a pre-commit hook. Install it
once per clone with `tools/install-hooks.sh`.

## Lineage

Extracted from the Vera Inspector, itself the third iteration of the same idea,
which by mid-2026 existed as four diverging copies across four projects. The
in-page collector is carried over unchanged — it was tuned against six themes ×
two viewports of a real app, and that tuning is most of the value.

What the extraction added: config instead of a hardcoded registry, generalised
`{param}` discovery, per-surface profile pinning (replacing a `kind = "static"`
special case), the `http` fallback engine, baseline diffing, failed clicks as
findings, optional clicks, and a versioned JSON contract.

## Roadmap

- **MCP server** — the same `look()` behind tool definitions, for agents without
  shell access. `api.look()` is already the single entry point so this is an
  adapter, not a rewrite.
- **A real accessibility pass** — alt text, form labels, accessible names,
  heading order, landmarks, focus visibility. Contrast and tap targets are the
  only two today.
- **Visual diffing** — the baseline compares findings, not pixels; a layout can
  break in ways no named check catches.
- Per-viewport `settle_ms` and `pre_clicks`; multi-origin apps; a smarter `http`
  engine; `init --crawl` to scaffold a config; video capture of a click path.

## Licence

MIT.
