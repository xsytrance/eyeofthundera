# Vision

> **Status of this document.** Written 2026-07-29 from what Rod actually said
> when commissioning the project, plus what the code makes evident. Sections
> are marked **Stated**, **Inferred**, or **Open** so nobody downstream mistakes
> a reasonable guess for a decision. Rod: correct the Inferred parts and answer
> the Open ones, and delete these markers as they firm up.

---

## The one-line version

**Give every agent eyes.** An agent writing frontend code is otherwise working
blind — it can run the tests and read the HTML, but it cannot see that the
button it just shipped is 20px tall on a phone, or grey-on-grey, or that the
view it "verified" was never actually on screen.

## Stated — what Rod asked for

Verbatim framing, 2026-07-29:

> *"so you know those 'eyes' you have? I want to make them their own project for
> any of my agents or Claude or whomever to use. I want to call it The Eye of
> Thundera"*

Three decisions carried in that sentence, and one made right after:

1. **Extract, don't invent.** The capability already existed and worked. The
   project is about *liberating* it from one codebase, not building a new thing.
2. **Not for one app, and not for one agent.** "Any of my agents or Claude or
   whomever" — the audience is a fleet, including agents that aren't Claude and
   people who aren't Rod.
3. **The name is the spec.** The Eye of Thundera grants *sight beyond sight* —
   seeing what is really there, at a distance, including what you'd otherwise
   miss. That is the product requirement, not decoration.
4. **CLI + JSON contract first, MCP eventually.** Chosen explicitly over
   MCP-first and skill-first: *"CLI plus json but also eventually mcp"*.

## Inferred — the problem it's actually solving

Rod runs a fleet of projects (the Vera family, Ember, and others) and a fleet
of agents across them. The Inspector had already been hand-ported into four
codebases and had begun to diverge: `fft-psx-vera` grew a seven-module package
with vision critique and montages, while `undertale-vera`, `ember-lite` and
`ember-pro` carried a 193-line single-file ancestor. Every new project meant
another port, and every improvement landed in exactly one copy.

So the project is shared infrastructure in the MultiVera spirit: **one engine,
many consumers, each supplying only its own config.** The measure of success is
copies deleted, not features added.

## Principles the code already commits to

These are load-bearing. Changing one is a decision, not a refactor.

**A tool that lies about what it looked at is worse than no tool.**
The first real sweep found seven mobile surfaces being measured as the wrong
page and reported *clean*, because the click that should have opened them
silently missed. A failed required click is now an error. Anything the Eye
cannot actually verify must say so — skipped with a stated reason, never a
silent pass.

**Findings must mean something.** Thresholds are tuned so a finding reads as
*"a human would call this sloppy"*, not *"pixel trivia"*. The escape hatch for a
check you've decided you don't care about is config (`severity.x = "off"`), never
loosening the check for everyone.

**The delta is the product.** An absolute count is nearly useless on a mature
app — every real UI carries a tail of accepted warnings. "38 findings" tells an
agent nothing; "2 new since your change" tells it everything.

**Degrade, never refuse.** No Playwright → status-code sweep. No Pillow → no
montages. No Ollama → no critique. The core has zero dependencies on purpose.

**The engine knows nothing about any app.** Every app-specific word lives in a
`thundera.toml`. If a product name appears in `thundera/`, that's a bug.

**The JSON is the interface.** Humans get the Markdown report and the montage;
agents get a versioned, additive-only contract. Both are generated from one run.

## Where it's going

Ordered by conviction, highest first.

1. **Delete the copies.** Migrate `undertale-vera`, `ember-lite`, `ember-pro`
   and `fft-psx-vera` onto the package and remove their vendored inspectors.
   This is the whole point; until it happens the drift problem is unsolved.
2. **MCP server** — the same `look()` behind tool definitions, for agents
   without shell access. Deliberately *after* a third app has used the CLI, so
   the tool surface is designed against real usage rather than guessed at.
3. **Beyond web.** *(Inferred, unconfirmed.)* "Eyes" needn't mean a browser
   forever — a desktop window, a TUI, a screenshot on disk. The `driver` module
   is already an engine interface with two implementations, so the seam exists.

## Open questions for Rod

- **Public or private?** The repo is private today. It's MIT-licensed and has
  no secrets — publishing costs nothing and makes "or whomever" literal. Your
  call whether the fleet is the audience or the world is.
- **Is "eyes" web-only?** Item 3 above is my inference, not your instruction.
  If you want desktop/TUI sight, that changes the engine interface now rather
  than later.
- **Does it grow a memory?** Right now every run is stateless apart from an
  opt-in baseline file. A version that tracked a surface's polish over weeks is
  a different, larger product — worth knowing if that's where this is headed.
- **Who else runs it?** If non-Claude agents are real consumers today, that
  raises MCP's priority above item 1.

---

*Keep this honest. If a principle above stops being true of the code, change
one of them — don't let the document drift into aspiration.*
