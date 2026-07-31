"""thundera — the command line.

Contract, because agents depend on it:
  stdout  is the product. With --json it is the findings JSON and nothing else.
  stderr  is progress chatter. Always safe to discard.
  exit 0  clean · exit 1 findings that count as failure · exit 2 usage/config error.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from . import __version__
from . import baseline as baseline_mod
from . import eye
from .api import look, preflight
from .config import Config, ConfigError

TEMPLATE = '''# thundera.toml — what the Eye should look at.
# Docs: every table is optional except [app] and at least one surface.

[app]
name = "{name}"
base = "{base}"
routing = "path"        # "hash" if your SPA routes as /#/dashboard

# Quick start: just list paths. Surface keys are derived from them.
# paths = ["/", "/about", "/settings"]

# Full form — one block per page you care about.
[[surfaces]]
key = "home"
path = "/"
group = "core"          # montage grouping
settle_ms = 1500        # wait after load before measuring
# pre_clicks = [".open-menu"]                 # click these first (opens modals)
# inventory = {{ nav = "nav", hero = ".hero" }}  # named boxes to record sizes for
# profiles = ["dark"]                          # only shoot under these profiles

# Screen sizes. Omit for the defaults (390x844 mobile + 1280x800 desktop).
# [[viewports]]
# label = "m390"
# width = 390
# height = 844
# scale = 2
# mobile = true

# Variants of the same app — themes, locales, logged-in states. `seeds` are
# localStorage values planted before first paint.
# [[profiles]]
# name = "dark"
# seeds = {{ theme = "dark" }}

# localStorage applied under every profile — use it to skip onboarding modals
# that would otherwise cover every screenshot.
# [seeds]
# welcome_seen = "1"

# Runtime {{param}} values for parameterised paths, fetched from your app so
# entity ids never get hardcoded here.
# [discovery]
# url = "http://127.0.0.1:8000/api/diag/ui-map"
# params = {{ project_id = "entities.project_ids.0" }}

# Or pin them by hand (these win over discovery).
# [params]
# project_id = "1"

# Quiet a check you have decided you don't care about: "error" | "warn" | "off"
# [severity]
# spacing = "off"

# URLs whose 4xx/5xx is expected and must not fail a run.
# [network]
# ignore = ["favicon", "/api/optional-thing"]

# Surfaces worth the slow local-model style critique (--vision sample).
# [vision]
# sample = ["home"]
'''


def _load_config(args, parser) -> Config:
    if args.base and not args.config:
        cfg = Config.discover() or Config.minimal(args.base)
        return cfg.with_base(args.base)
    if args.config:
        cfg = Config.load(args.config)
    else:
        cfg = Config.discover()
        if cfg is None:
            parser.error(
                "no thundera.toml found and no BASE given.\n"
                "  thundera look http://127.0.0.1:8000     # zero-config\n"
                "  thundera init                           # write a config"
            )
    return cfg.with_base(args.base)


def cmd_look(args, parser) -> int:
    err = sys.stderr
    log = (lambda *a: None) if args.quiet else (lambda *a: print(*a, file=err))
    # The animation is for a human watching a terminal. Under --json or --quiet
    # there is no human, so force it off rather than relying on the tty check.
    #
    # --animation forces it ON, which is the only way an agent can draw it: an
    # agent's stderr is a pipe, never a tty, so the auto-detect says no every
    # time. In a pipe `eye` draws one static frame with no escape codes, so a
    # forced eye stays readable in a captured log. --json still wins — the
    # contract that stdout is pure JSON outranks any decoration.
    animate = None
    if args.quiet or args.json or args.no_animation:
        animate = False
    elif args.animation:
        animate = True

    cfg = _load_config(args, parser).select(
        surfaces=args.surfaces.split(",") if args.surfaces else None,
        profiles=args.profiles.split(",") if args.profiles else None,
        viewports=args.viewports.split(",") if args.viewports else None,
    )
    if args.quick:
        cfg = cfg.select(profiles=[cfg.profiles[0].name])
    if args.a11y is not None:
        # Zero-config mode has no toml to carry [a11y], so without this flag the
        # accessibility pass would be unreachable for anyone doing the thing the
        # README leads with: `thundera look http://host`.
        cfg = replace(cfg, a11y=args.a11y)

    vision_mode = "off"
    if args.vision:
        vision_mode = "all" if args.vision == "all" else "sample"

    eye.open_eye(err, force=animate)

    baseline_path = args.baseline
    if args.update_baseline and not baseline_path:
        baseline_path = None          # nothing to compare against on a first record

    result = look(
        cfg,
        out_dir=args.out,
        engine=args.engine,
        vision_mode=vision_mode,
        make_montage=not args.no_montage,
        baseline_path=baseline_path,
        markdown_path=args.report,
        warn_as_error=args.warn_as_error,
        browser_path=args.browser,
        retries=args.retries,
        log=log,
    )

    status = eye.status_of(result.summary)
    s = result.summary
    eye.verdict(
        status,
        f"{s['errors']} errors · {s['warnings']} warnings",
        err,
        force=animate,
    )

    if args.json:
        print(result.json())
    else:
        from .report import write_text_summary

        print(write_text_summary(result.body))
        print(f"findings: {result.artifacts.get('json')}")
        if result.artifacts.get("markdown"):
            print(f"report:   {result.artifacts['markdown']}")

    if args.update_baseline:
        dest = args.update_baseline if isinstance(args.update_baseline, str) else ".thundera/baseline.json"
        baseline_mod.save(result.body, dest)
        print(f"baseline recorded: {dest}", file=err)

    # A regression against a baseline is a failure even when the absolute
    # counts are unchanged — that is the whole point of having one.
    bl = result.body.get("baseline") or {}
    if bl.get("new_errors"):
        return 1
    if args.fail_on_new and bl.get("new"):
        return 1
    return result.exit_code


def cmd_init(args, parser) -> int:
    dest = Path(args.path or "thundera.toml")
    if dest.exists() and not args.force:
        print(f"{dest} already exists (use --force to overwrite)", file=sys.stderr)
        return 2
    dest.write_text(TEMPLATE.format(name=args.name or Path.cwd().name, base=args.base))
    print(f"wrote {dest}")
    print("next:  thundera check   then   thundera look")
    return 0


def cmd_check(args, parser) -> int:
    cfg = _load_config(args, parser)
    print(f"config:    {cfg.source or '(built-in minimal)'}")
    print(f"app:       {cfg.name} @ {cfg.base} ({cfg.routing} routing)")
    print(f"surfaces:  {len(cfg.surfaces)} — {', '.join(s.key for s in cfg.surfaces)}")
    print(f"profiles:  {', '.join(p.name for p in cfg.profiles)}")
    print(f"viewports: {', '.join(v.label for v in cfg.viewports)}")
    print(f"page views per run: {cfg.page_view_count}")
    notes = preflight(cfg)
    for n in notes:
        print(f"  ! {n}")
    return 0


def cmd_surfaces(args, parser) -> int:
    cfg = _load_config(args, parser)
    rows = [
        {
            "key": s.key,
            "path": s.path,
            "group": s.group,
            "routing": s.routing or cfg.routing,
            "profiles": list(s.profiles) if s.profiles else [p.name for p in cfg.profiles],
        }
        for s in cfg.surfaces
    ]
    if args.json:
        print(json.dumps(rows, indent=1))
    else:
        for r in rows:
            print(f"{r['key']:<24} {r['path']:<40} [{r['group']}]")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="thundera",
        description="Eye of Thundera — give any agent eyes on a running app.",
        epilog="exit 0 = clean · 1 = findings · 2 = usage error",
    )
    p.add_argument("--version", action="version", version=f"eye-of-thundera {__version__}")
    sub = p.add_subparsers(dest="cmd")

    def common(sp):
        sp.add_argument("-c", "--config", help="path to thundera.toml (default: search upward)")
        sp.add_argument("--base", help="override the app origin")

    look_p = sub.add_parser("look", help="sweep the app and report findings")
    common(look_p)
    look_p.add_argument("base_pos", nargs="?", metavar="BASE",
                        help="app origin; enables zero-config mode when no thundera.toml exists")
    look_p.add_argument("--surfaces", help="comma-separated surface keys")
    look_p.add_argument("--profiles", help="comma-separated profile names")
    look_p.add_argument("--viewports", help="comma-separated viewport labels")
    look_p.add_argument("--quick", action="store_true", help="first profile only")
    look_p.add_argument("--engine", choices=("auto", "browser", "http"), default="auto")
    look_p.add_argument("--browser", help="path to a Chromium binary")
    look_p.add_argument("--vision", nargs="?", const="sample", choices=("sample", "all"),
                        help="add local vision-model critique (slow, advisory)")
    look_p.add_argument("--out", help="run directory (default: .thundera/runs/<timestamp>)")
    look_p.add_argument("--report", help="also write a Markdown report here")
    look_p.add_argument("--json", action="store_true", help="print the findings JSON to stdout")
    look_p.add_argument("--baseline", help="compare against this findings file")
    look_p.add_argument("--update-baseline", nargs="?", const=".thundera/baseline.json",
                        help="record this run as the baseline (default .thundera/baseline.json)")
    look_p.add_argument("--fail-on-new", action="store_true",
                        help="exit 1 on any new finding vs baseline, warnings included")
    look_p.add_argument("--a11y", dest="a11y", action="store_true", default=None,
                        help="run the semantic accessibility checks "
                             "(also: [a11y] enabled = true in config)")
    look_p.add_argument("--no-a11y", dest="a11y", action="store_false",
                        help="skip them even if the config asks for them")
    look_p.add_argument("--retries", type=int, default=0, metavar="N",
                        help="re-run failed page-views N times; errors that don't "
                             "reproduce are demoted to warnings and marked flaky")
    look_p.add_argument("--warn-as-error", action="store_true")
    look_p.add_argument("--no-montage", action="store_true")
    look_p.add_argument("--no-animation", action="store_true",
                        help="skip the eye (also: THUNDERA_NO_ANIM=1)")
    look_p.add_argument("--animation", action="store_true",
                        help="draw the eye even when stderr is not a terminal — "
                             "how an agent shows it on first use or a new mission")
    look_p.add_argument("-q", "--quiet", action="store_true", help="silence progress on stderr")
    look_p.set_defaults(fn=cmd_look)

    init_p = sub.add_parser("init", help="write a starter thundera.toml")
    init_p.add_argument("path", nargs="?", help="where to write (default ./thundera.toml)")
    init_p.add_argument("--name", help="app name")
    init_p.add_argument("--base", default="http://127.0.0.1:8000")
    init_p.add_argument("--force", action="store_true")
    init_p.set_defaults(fn=cmd_init)

    check_p = sub.add_parser("check", help="validate the config without running a sweep")
    common(check_p)
    check_p.set_defaults(fn=cmd_check)

    surf_p = sub.add_parser("surfaces", help="list the surfaces the Eye knows about")
    common(surf_p)
    surf_p.add_argument("--json", action="store_true")
    surf_p.set_defaults(fn=cmd_surfaces)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    # `thundera http://host` and bare `thundera` both mean "look".
    if not argv or (argv[0] not in {"look", "init", "check", "surfaces"} and not argv[0].startswith("-")):
        argv.insert(0, "look")
    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 2
    if getattr(args, "base_pos", None):
        args.base = args.base_pos
    try:
        return args.fn(args, parser)
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
