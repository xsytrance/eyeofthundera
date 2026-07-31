# Eye of Thundera — project instructions

## What this is

An app-agnostic UI inspector that gives agents sight of a running web app.
Point it at a URL; get screenshots plus a versioned JSON verdict.

Read `docs/VISION.md` for why it exists, `docs/HANDOFF.md` for what is true
right now, `docs/ARCHITECTURE.md` for the module map.

## Documentation is part of the work — not an afterthought

**Every change that alters behaviour updates the docs in the same commit.**
This is the project's standing rule, and a `pre-commit` hook enforces the
handoff half of it.

| File | When | How |
|---|---|---|
| `docs/HANDOFF.md` | any behaviour change | **edit in place** — update *Last updated*, *Current state*, *Next steps* |
| `docs/BUILDLOG.md` | any session of substance | **append at the top** — what, why, and what surprised you |
| `docs/VISION.md` | intent or a principle changes | rare; be deliberate |
| `docs/ARCHITECTURE.md` | modules, data shapes, contracts change | keep the diagram true |
| `README.md` | user-facing behaviour, flags, config keys change | it is the front door |

The build log is **append-only**. If an earlier decision was reversed, add a new
entry saying so — don't rewrite history.

Write the handoff for someone who has never seen this repo and has no access to
the conversation that produced it. Assume that person is you, in six months,
with none of the context.

## Guardrails

1. **`api.look()` is the only entry point.** The CLI is a thin wrapper and MCP
   will be too. New features go in `api.py` or below it — never in `cli.py`.
   Only arg parsing, stdout formatting and exit-code translation live there.
2. **Never let the tool claim it saw something it didn't.** Anything
   unverifiable is skipped *with a stated reason* or reported as a finding.
   A silent pass is the worst possible bug here — it has happened once already
   (see the 2026-07-29 build log entry).
3. **The engine stays app-agnostic.** If a product name, a theme id, or a CSS
   selector for somebody's app appears anywhere in `thundera/`, that's a bug.
   It belongs in a `thundera.toml`.
4. **The core package keeps zero dependencies.** Playwright and Pillow are
   extras. The `http` engine must keep working on a bare box.
5. **`checks.COLLECT_JS` is carried over unchanged from the Vera Inspector.**
   Don't loosen a threshold to quiet one noisy project — that project sets
   `severity.<kind> = "off"` in its own config.
6. **`schema_version` is additive-only.** Agents parse the findings JSON. New
   keys may appear; changing what a key means requires a version bump.
7. **Baseline identity keys on `anchor`, never `detail`.** `detail` carries
   jittering pixel values.

## Commands

```bash
.venv/bin/python -m pytest -q          # 103 tests; browser suite auto-skips
.venv/bin/thundera check -c examples/undertale-vera.toml
.venv/bin/thundera look http://127.0.0.1:9092
python3 -m py_compile thundera/*.py    # quick syntax check
tools/install-hooks.sh                 # once per clone
```

Always run `pytest -q` before committing.

## Testing style

Real servers, not mocks of the thing under test. `test_end_to_end.py` and
`test_browser.py` both spin up a `ThreadingHTTPServer` over a temp directory.
The browser suite asserts what only a renderer can prove — seeds landing before
first paint, a missed required click failing the run, an optional one not.

When you fix a bug, add the test that would have caught it. Both bugs found on
2026-07-29 now have one.
