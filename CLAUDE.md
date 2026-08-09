# Eye of Thundera — project instructions

<!-- CANON:BEGIN v2 2026-08-09 — managed by the Singularity Event. Edit the source, not this block. -->
## The Dominion — standing canon (v2)

**Theme.** Everything in this fleet is named and spoken in the register of
**magic, science, and military** — *"Doctor Doom meets Master Chief."* Imperial,
arcane, martial, over real engineering. Music is the soul that runs through all
three. The Lexicon (`hermes360/docs/codex/lexicon.json`) is the source of truth
for names; a themed name with no Lexicon entry is a bug, not creativity.

> **The Iron Rule.** The theme is a **naming / lore / presentation layer over
> stable technical identifiers. It NEVER renames the substrate.** Ports stay
> numeric in code; unit names, API paths, file names, env vars, and DB tables are
> unchanged. Themed names appear in agent speech, UIs, docs, and conversation —
> never in code identifiers. Renaming the substrate would break every running
> system, backup, and timer on the fleet.

Core terms: fleet → **the Dominion** · owner → **the Sovereign** · host →
**Realm** · PRIME → **the Citadel** · exxo-1 → **the Foundry** · tailnet →
**the Ley Lines** · service → **Engine** · agent → **Champion** · port →
**Portal** · endpoint → **Gate** · code → **Spell** · function → **Incantation**
· database → **Vault** · config → **Ward** · secret → **Seal** · doc → **Tome**
· log/receipt → **Chronicle** · backup → **Wardstone** · monitor → **the Augury**
· LLM → **Familiar** · notification → **a Sending** · Singularity → **the Grand
Archive**. *(Top names blessed by the Sovereign 2026-08-07.)*

**The Tongue.** The Dominion speaks a blessed language — lexicon + spellbook,
all canon as of 2026-08-08 (`hermes360/docs/codex/lexicon.json`; human copy
`TOME.md` beside it). **Spells are orders** — execute the expansion, not the
words: ISI · sitrep · feed this · Forge on (continue autonomously) · Seal it
(commit+push+docs) · Scry <realm> (health-probe) · Consult the Archive · Sound
the horn (notify now) · Muster (roster+liveness) · Hold the line (observe only)
· Stand down (wrap up) · By the Iron Rule (naming veto). **Correction canon
(bidirectional):** when the Sovereign uses a plain phrase with a blessed
equivalent, offer once per term per session: 📜 Tongue: "<plain>" → **<blessed>**
— never blocking the work. Anyone coins (`status: "proposed"`); only the
Sovereign blesses.

**Reporting.** Every substantive reply ends with a `## TL;DR` — last, after the
detail, 3–5 bullets. Lead with anything the Sovereign must act on. Corrections
go **in** the TL;DR, never buried in the body.

**ISI.** On a big feature, a big change, a security posture, a schema change, or
a new project: **Intent** (what is he really trying to achieve?), **Sanity** (is
this the right approach? say so plainly, once), **Improvement** (is there a
better way? what would I add?). Verify with commands — measured beats plausible.
ISI is advisory, not a veto: raise it, recommend, then build. If he reaffirms,
that's the decision. Not permission to stall, and not permission to gold-plate.

**Secrets.** `~/.config/<system>/env`, mode 600. Never in a chat box, a commit,
or a screenshot. Exposed once = rotate the same day. `docs/SECURITY.md` is law.

**The Five Foundations.** One network (the tailnet) · one wallet (OpenRouter,
named key per system) · one secrets pattern · one memory (this) · one ark
(exxo-1). Full text: `docs/MASTER_PLAN.md`.

**Birth and death.** A new system gets, on day 0: `git init`, an env file (600),
a named key if it spends, a **Lexicon entry**, a row in `docs/SYSTEMS.md`, and an
Eye config if it has a UI. *A system not in the registry does not exist.* Cold
for 60 days → `~/archive/`. Archiving is honorable; drift is not.
<!-- CANON:END -->

<!-- BULLETIN:BEGIN 2026-08-09T05:34 — managed by the Singularity Event. Facts, not rules. Edit the registry, not this block. -->
## The Dominion — the roster (41 systems)

You are in **eye-of-thundera**. sight beyond sight, for agents. Point it at a running web app and it reports what a careful reviewer would notice: broken images, console and network…

**Tell the Archive anything that matters:** `tell-singularity "…"` (`--birth <sys>` · `--death <sys>` · `--change <sys>` · `--ask "…"`)
**Find out what you missed:** `~/singularity/scripts/brief.sh`

### Born or changed in the last 14 days
- **planet-studio** — 2026-08-08 — satellite (music) — Android studio companion for x1c7.com: the Wall, galaxy, cover studio…
- **audiex** (the Warhorn) — 2026-08-08 — satellite (music) — standalone offline-first player for the Suno catalog; the planet-studio…
- **stem-racer** — 2026-08-07 — satellite (music/game) — stem-based racing game; APK served from ~/apk-share.
- **cadence** — 2026-08-07 — the Dominion's ceremony bus (Portal 8114). Any Engine posts a rite; it decides how it is felt…
- **vgclan** — 2026-08-02 — satellite — VG Clan revival site; re-recruit the founders, deploy to vgclan.x1c7.com.
- **NEXUS** — 2026-07-31 — command vault (obsidian) — Gradle project with mobile-web application components.
- **memguard** — 2026-07-31 — utility — guards against memory exhaustion on Prime; the GPU is shared (16 GB) and a runaway…
- **singularity** (the Grand Archive) — 2026-07-31 — the Grand Archive. System of record for a life: every chat, doc, photo and receipt, dated…

### The full roster
`sayhai` · `stem-racer` · `va-academy` · `vgclan` · `cadence` · `entangled-private` · `entangled-tools` · `xsyverse` · `fft-psx-vera` · `hermes360-c2-artifacts` · `argus-risk-adviser` · `clawdpad-app` · `aurex16pp` · `ember-lite` · `kinetica` · `planet-studio` · `audiex` · `vAIb` · `pokepad` · `ossicle-backups` · `Hermes` · `ossicle` · `singularity-integration` · `x1c7.com` · `AGENOR-Horology` · `atlas` · `entangled` · `undertale-vera` · `eye-of-thundera` · `hermes360` · `xsywatch` · `NEXUS` · `memguard` · `singularity` · `skynet` · `xsynet` · `ossicle-worktrees` · `dazzler` · `claudeblock` · `ember-pro` · `prism`

Live: `GET :8801/api/event/roster` · Canonical: `singularity/docs/SYSTEMS.md`
<!-- BULLETIN:END -->

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
