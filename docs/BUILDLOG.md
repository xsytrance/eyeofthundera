# Build log

Append-only. Newest entry at the top. One entry per session or substantive
change: what was done, **why**, and anything that surprised us.

This is the archaeological record — when someone asks "why on earth does it do
*that*", the answer should be findable here. Do not rewrite history; if an
earlier decision was reversed, add a new entry saying so.

---

## 2026-07-30 — Public, and a way to hand it over

**What:** The repo is public and MIT. `SUMMONING.md` is a prompt you paste to an
agent; it installs the Eye, opens it on your app and reports back, so handing
the tool to somebody costs one message rather than a tutorial.

**Audited before flipping the switch, not after.** Publishing is not reversible
in practice — things get cached and indexed. Checked: no secret-shaped strings
outside documentation *about* env vars and one fake `s3cret` test literal; no
emails in tracked files; the committed save fixtures are the synthetic ones,
named "Frisk", which is Undertale's default protagonist and not a person. 34
tracked files, all intended.

Commit author email is public now, as it is for every public repo. Called out
because it is the one thing an audit of *files* would miss.

**The install command in the docs was run before being handed to anybody.** A
clean venv, the public git URL, verbatim the string in `SUMMONING.md`. It
installs, the binary reports its version, and the first sweep drew the eye and
found three errors and nine warnings on a throwaway page. A broken first command
is a bad introduction, and "it should work" is not evidence.

**On `SUMMONING.md` rather than more README.** The README is for someone
deciding whether to use this. The summoning is for someone who has already
decided and wants it in their agent's hands in one paste. Two audiences, two
documents; merging them would serve neither.

---

## 2026-07-30 (fifth session, later still) — Making it usable by somebody else

**What:** The work of getting the Eye ready to hand to a second person with a
second machine and a different fleet of agents. Two real gaps found by *using*
it as a stranger would rather than reading it. 108 → 110 tests.

**Gap one: the accessibility pass was unreachable from zero-config.** Found by
installing the package into a clean venv and doing the thing the README leads
with — `thundera look http://host`. There is no toml in that mode, so `[a11y]`
had no way to be set, and the eight semantic checks were invisible to anyone who
had not yet written a config. That is the opposite of the zero-config promise.
Fixed with `--a11y` / `--no-a11y`.

**Gap two, and the more interesting one: an agent could not draw the eye at
all.** `enabled()` animates only when stderr is a terminal. An agent's stderr is
a pipe. Every flag that existed forced it *off*; there was no way to force it
*on*. So the eye — the thing the project is named for, whose iris carries the
verdict — was structurally unavailable to its actual audience.

`--animation` fixes it. The non-tty path already drew one static frame with no
escape codes, so a forced eye is readable in a captured log rather than a spray
of control characters. `--json` still outranks it: stdout stays pure JSON, and
no decoration gets to break the contract.

**The guidance matters as much as the flag.** Both "always" and "never" are
wrong. The README now says: first use in a session, the start of a new mission,
or a run whose answer you are about to act on — and *not* all forty runs of a
tight loop, because an eye on every invocation is wallpaper and wallpaper is
ignored. The iris is the verdict, so a drawn eye should carry a result, not just
announce itself.

**Verified rather than assumed, for the second machine:**

- No platform-specific calls anywhere in `thundera/` — no `signal`, `fcntl`,
  `termios`, `/proc`, `subprocess`, no `sys.platform` branches.
- The art is pure ASCII. The only non-ASCII byte in any output is the `·`
  separator in the verdict line, and it survives `LANG=C LC_ALL=C` without
  raising — checked, because a `UnicodeEncodeError` on somebody else's laptop is
  a bad first impression.
- Cold install into a clean venv works, and zero-config against a throwaway
  static site found six errors and seven warnings first try, including the
  contrast case that used to be a false positive.
- README now names the Python 3.11 floor and the macOS stumble explicitly: the
  system `python3` there is still 3.9, which is the single most likely way a new
  user's first command fails.

**Still not verified:** nobody has run this on macOS. The evidence above is
strong — no Linux-shaped code, portable stdlib only — but it is inference, not
execution, and this file should not pretend otherwise.

**The doc hook earned its keep.** The first attempt at this commit was rejected
by `tools/hooks/pre-commit` for touching `thundera/` without updating this file.
Working as designed.

---

## 2026-07-30 (fifth session, later) — The accessibility pass

**What:** `thundera/a11y.py`, a second in-page collector with eight semantic
checks. 103 → 108 tests. `main` fast-forwarded to `first-consumer` first, since
that branch had stopped describing its contents four commits ago.

**Why a separate module rather than more `COLLECT_JS`.** Three reasons, and the
first is the one that matters: `COLLECT_JS` is frozen by guardrail, and growing
it invites exactly the edits that rule exists to prevent. Second, this pass asks
the DOM about *meaning*, not geometry — a label is missing or it isn't, and
there is no threshold to tune. Third, it can be switched off wholesale, which is
what a project buried in a11y debt will want on day one.

**Everything is `warn`, deliberately.** A control a screen reader cannot name is
broken, not untidy — but shipping these as errors would turn a green CI red for
every consumer on the day they upgrade. Projects promote what they have cleaned
up: `severity.no_accessible_name = "error"`.

**It is opt-in, and that was a reversal mid-build.** The first version defaulted
on. Running the suite immediately failed four unrelated browser tests with
`no_lang` and `no_landmark` — the minimal fixture pages have neither. That was
the feature telling on itself: those two are facts about the *document*, so on a
single-page app where forty page-views share one document they would be forty
identical findings. VISION says a finding must mean *"a human would call this
sloppy"*, and forty copies of one fact is the a11y equivalent of pixel trivia.

So: `[a11y] enabled = true`, off by default, same posture as `--vision`.
Upgrading the package cannot change what an existing run reports. That all 103
pre-existing tests then passed untouched is the evidence the change is
non-breaking, and is worth more than any assertion about it.

**What surprised us: the noise never showed up.** With the pass on against the
live apps, ember-lite reports **two** findings and undertale-vera **two** across
five surfaces — no `no_lang`, no `no_landmark`, no `img_no_alt`. Both apps
already do those correctly. The findings that did land are specific and real:
`input#chat-input` labelled only by a placeholder (which disappears on focus and
is not a label), and an `h2 → h4` skip in the workshop view. The fear that drove
the opt-in decision was mostly unfounded *for these apps* — but the decision
still stands on the upgrade-safety argument alone, and now there are real
numbers for whoever revisits the default.

**The tests are as much about silence as noise.** One fixture page carries one
instance of each defect *and* the correct-and-quiet counterparts beside it:
`alt=""` next to a missing `alt`, an `aria-label`led icon button next to an
empty one, three correctly-labelled inputs next to a placeholder-only one. Each
assertion is `count(kind) == 1`, so a check that also fires on the correct
markup fails. There is a second control page that is simply valid, and must
produce nothing at all. A check that cries wolf on good markup is worse than no
check — it teaches people to ignore the tool.

Contrast is deliberately *not* in this pass; `COLLECT_JS` already does it
properly by compositing the real paint stack.

---

## 2026-07-30 (later) — `navigate = "once"`, and the seven views finally open

**What:** One small feature, and the payoff it was built for. 97 → 103 tests.
`examples/undertale-vera.toml` goes from 13 surfaces to **20**, 26 page-views to
**40**. The Eye now sees all 16 of that app's views; this morning it saw 9.

**The feature.** `[app] navigate = "always" | "once"`, default unchanged. Under
`"once"` the browser engine reuses the page whenever the resolved URL is
unchanged, instead of calling `page.goto()` before every surface. Three lines in
`sweep_browser`. It exists because the previous entry found the blocker: a
loaded save lives in a JS closure, `localStorage` holds nothing, and the
per-surface reload threw it away.

Reuse is keyed on the **URL**, not on "skip everything after the first load", so
a surface with a genuinely different path still navigates — there is a test for
exactly that, because the lazy implementation would have passed the other two.
Records carry `"nav_note": "reused page (navigate = once)"`; a page-view
measured without a fresh load is a different claim and the JSON says so.

**The cost, which is why it is opt-in and why the tests are a matched pair.**
With reuse, each surface arrives showing whatever the last one left on screen.
`chat` — which had needed no clicks at all, because a fresh load opens there —
now needs an explicit `[data-view="chat"]`. The test that proves the feature
works (`in-memory state survives`) and the test that proves the default still
isolates (`the default reloads and therefore loses it`) are the same page with
one config key flipped. Neither is meaningful alone.

**What surprised us: the config got *more* honest, not less.** Every surface in
the example now ends its `setup` with `{ wait_for = "#view-<key>" }`. That was
not tidiness — it is the direct lesson of this morning's false pass. A bare
click reports success even when the app redirects, and the only reason the
first attempt was caught was that somebody opened a PNG. `wait_for` turns "I
clicked it" into "I got there", checkable by the machine. `pre_clicks` is now
absent from that config entirely; `setup` supersedes it for click-routed apps,
because `pre_clicks` cannot express an assertion.

**Caught by the tool, on the first full run.** Desktop passed; all twenty mobile
surfaces failed with `setup_failed`, 54 errors. At 390px the nav is a drawer and
`#add-save-btn` is unreachable until `#save-pill` opens it — the profile setup
had no `?#save-pill` guard, so the upload never happened and every record was
correctly tainted. Exactly the class of bug that used to report clean.

**The payoff, and it is a real one.** With mobile fixed: 19 clean and `council`
at m390 reporting **nine genuine `tap_target` warnings** — 56×21px "talk"
buttons, well under the 32px floor, on a view nobody had ever looked at on a
phone. That is the whole argument for this project in one line: the findings
were always there, and the tool could not see the room they were in.

**Also:** `examples/fixtures/` now holds the two synthetic save files (126 bytes
together) so the example is self-contained and `thundera check` passes in CI —
a missing upload fixture is a config error by design.

**Note for whoever syncs the consumer:** `undertale-vera`'s own `thundera.toml`
is now behind this copy. It does not have the seven views, `navigate = "once"`,
or the `wait_for` assertions.

---

## 2026-07-30 — Verifying the seven hidden views, and being wrong twice

**What:** No code change. An attempt to actually reach undertale-vera's seven
NEEDS_SAVE views with the new `setup` steps, which failed in two instructive
ways before working. Documented because both failures are the kind this project
exists to prevent, and the second one nearly shipped as a claim.

**Wrong the first time — "we need a save fixture."** The previous session's
handoff asked Rod for one. It didn't need to: `undertale-vera/tests/fixtures/`
has had `file0_pacifist` (30 bytes) and `undertale_pacifist.ini` (96 bytes)
since July, and `tools/make_synthetic_fixtures.py` exists precisely because the
originals carried a real player's name. The answer was already in the repo the
migration came from. Look before asking.

**Wrong the second time, and worse.** With the uploads wired up, a sweep of all
seven views reported **0 errors, 7 clean surfaces**. The screenshots had seven
distinct checksums and seven distinct byte sizes, which the last build log entry
names as the tell for a `pre_click` that didn't land. It looked verified.

It wasn't. Opening one screenshot showed the **saves view**, with the text
*"Read a save first to open Council."* in the corner and both file inputs
reading "No file chosen". All seven were the same page.

Two lessons, both worth keeping:

1. **The byte-size tell is necessary, not sufficient.** This app re-randomises
   its ambient quote and lore panels on every load, so seven "different"
   screenshots are the default, not evidence. A heuristic that worked once
   became a way to feel verified without being verified.
2. **The Eye cannot tell that a click bounced.** `[data-view="council"]` exists
   and is clickable, so `pre_click` succeeded; the app then redirected to
   `saves`. The Eye has no notion of a content assertion (decision 9) and never
   will — but `setup` now gives configs a way to assert it themselves. A
   `{wait_for = "#view-council"}` step fails honestly when the view never
   opened, which is what turned the false pass into seven `setup_failed`
   errors. That is the feature earning its place.

**The actual blocker, once the noise cleared.** The upload works and the save
loads — `#route-badge` reads "route: Pacifist (medium)". But the loaded save is
**in-memory only**; `localStorage` holds nothing but `uv_power_seen`. The
browser engine calls `page.goto()` per surface, and that reload discards it.
Profile-level setup therefore cannot carry state across surfaces on this app.

**What surprised us:** saves persist *server-side* even though the loaded state
doesn't. The shelf comes back populated after a reload, so re-clicking a save
card per surface restores everything — which gives a working config today
(confirmed: all seven views reached, and the council screenshot really is Sans,
Toriel and Flowey reacting to a Pacifist run). It depends on the instance
already holding a save, so it isn't self-contained for a fresh deployment.

The clean fix is to skip navigation when the resolved URL matches the current
one, opt-in, since a fresh load per surface is also what stops surface A leaking
into surface B. Added to the deferred list.

**Housekeeping:** the verification runs uploaded five throwaway saves to the
:9092 instance (Frisk / Pacifist / Jul 30). They are real rows in that app's
save list and should be deleted.

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

## 2026-08-08 — the Eye was reporting dead servers as CLEAN

**Fixed.** `thundera look http://127.0.0.1:59999` (nothing listening) returned
`2 clean · 0 error`. Two causes: `except Exception` around `page.goto` swallowed
`ERR_CONNECTION_REFUSED` identically to a networkidle settle timeout, and
nothing ever asserted the page had content.

**Now:** navigation errors are classified (`_nav_failed`) and raised as a
`nav_failed` finding at severity `error`; settle timeouts remain a note, as they
should. A 200 that renders no elements *and* no text is also flagged.

**Watch out:** the first threshold was `< 3 elements` and it failed this
project's own fixtures, which legitimately serve a one-element document. A
minimal page is still a page — only *truly* empty counts.

**Proven:** 110 tests green; dead port → 2 errors; live pages → clean.
