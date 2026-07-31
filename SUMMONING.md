# The Summoning

*How to hand the Eye to an agent.*

Copy one of the blocks below and give it to your agent. That is the whole
handover — no setup instructions, no repo tour, no explaining what a
`thundera.toml` is. The agent reads this file and knows what to do.

---

## The short one

> **Sight beyond sight.** Install the Eye of Thundera from
> `https://github.com/xsytrance/eyeofthundera`, open it on `http://localhost:3000`,
> and show me what it sees. This is your first time wielding it — draw the eye.

Change the URL to whatever you're running. That's it.

---

## The long one

Use this when you want the agent to do the whole ritual properly and report
back like it means it.

> You are about to wield the **Eye of Thundera** — an inspector that gives you
> actual sight of a running web app, instead of guessing from the HTML.
>
> 1. Install it:
>    `pip install "eye-of-thundera[all] @ git+https://github.com/xsytrance/eyeofthundera.git"`
>    then `playwright install chromium`. You need Python 3.11+.
> 2. Open it on `http://localhost:3000` — use `--animation`, because this is
>    your first time and the eye should open for it.
> 3. Read `findings.json`. It names its own screenshots — go and **look** at
>    them, don't just read the JSON.
> 4. Report what a careful reviewer would have noticed, worst first. Say plainly
>    what the Eye could *not* verify (`summary.unverified`) rather than implying
>    a clean bill of health.
>
> Then tell me whether the thing I just built is actually alright.

---

## What your agent should know

Four rules. Everything else is in the [README](README.md).

**The verdict is machine-readable.** `--json` puts the findings JSON on stdout
and nothing else; progress and the eye go to stderr. Exit `0` clean, `1`
findings, `2` your mistake.

```bash
thundera look http://localhost:3000 --json -q
```

**Draw the eye deliberately, not habitually.** Your stderr is a pipe, so the eye
is off unless you pass `--animation`. Use it the first time you wield the Eye in
a session, at the start of a new mission, and before a run whose answer you're
about to act on. Not on all forty runs of a tight loop — an eye on every
invocation is wallpaper, and wallpaper gets ignored.

The closing iris **is** the verdict: green clean, amber warnings, red `(x)`
errors. When you draw it, it carries the result.

```
     .------------------------------.
    (     .--------------------.     )
    (     |                    |     )
    (     |        (x)         |     )
    (     |                    |     )
    (     '--------------------'     )
     '------------------------------'
        3 errors · 3 warnings
```

**Go and look at the screenshots.** The JSON names its own artifacts —
`artifacts.run_dir`, `artifacts.json`, `artifacts.montages`. If you can see
images, open them. A montage is one PNG of every view with a coloured border per
health. That is the point of the tool: you have eyes now, so use them.

**Never claim it saw something it didn't.** `summary.unverified` counts what the
Eye declined to judge — text on a gradient, where guessing at pixels would be a
lie. A run reporting zero warnings and forty unverified measurements has not
told you the page is fine. Report both numbers.

---

## Going further

`thundera look <url>` works on any URL with no configuration at all. When you
want more than the front page:

```bash
thundera init            # writes an annotated thundera.toml
thundera check           # validates it without sweeping
thundera look            # sweeps everything it declares
thundera look --a11y     # add the semantic accessibility pass
```

A `thundera.toml` teaches it your app: which views exist, how to reach the ones
behind a click or a login, which screen sizes and themes matter, and what to
stop complaining about. The [README](README.md) has the full shape.

---

*The Eye grants sight beyond sight — seeing what is really there, at a distance,
including what you would otherwise miss. That is the product requirement, not
the decoration.*
