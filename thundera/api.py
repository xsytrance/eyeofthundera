"""The one entry point.

`look()` is the whole tool as a function. The CLI is a thin argument parser
over it, and an MCP server would be a thin tool-definition over it — neither
gets its own logic, so the two can never drift apart.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import baseline as baseline_mod
from . import driver, montage, report, vision
from .config import Config, placeholders, resolve_params

DEFAULT_OUT = ".thundera/runs"


@dataclass
class LookResult:
    body: dict                       # the JSON contract (report.build)
    out_dir: Path
    exit_code: int = 0
    artifacts: dict = field(default_factory=dict)

    @property
    def summary(self) -> dict:
        return self.body["summary"]

    def json(self, indent: int | None = 1) -> str:
        return json.dumps(self.body, indent=indent)


def fetch_discovery(cfg: Config, log=print) -> tuple[dict, dict]:
    """GET the discovery document. Returns (doc, note) — never raises.

    A discovery outage is not a crash: surfaces that needed its params get
    skipped with a stated reason, and the rest of the sweep proceeds.
    """
    if not cfg.discovery:
        return {}, {"configured": False}
    try:
        req = urllib.request.Request(
            cfg.discovery.url, headers={"User-Agent": "eye-of-thundera"}
        )
        with urllib.request.urlopen(req, timeout=cfg.discovery.timeout) as resp:
            return json.load(resp), {"configured": True, "url": cfg.discovery.url, "ok": True}
    except Exception as e:
        log(f"  ! discovery unreachable ({type(e).__name__}) — parameterised surfaces will skip")
        return {}, {
            "configured": True,
            "url": cfg.discovery.url,
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
        }


def _view_key(rec: dict) -> tuple[str, str, str]:
    return (rec.get("surface", "?"), rec.get("profile", "?"), rec.get("viewport", "?"))


def settle_flakes(records: list[dict], retry_records: list[dict], log=print) -> int:
    """Reconcile a retry pass into the first run's records. Returns flakes found.

    A finding that reproduced stands unchanged. One that did not is marked
    `flaky` and demoted to a warning — never deleted. A vanished error is still
    information: it means the app is unreliable, which is its own kind of bug,
    and dropping it silently would be exactly the sort of lie this tool exists
    to avoid.
    """
    from .report import finding_id

    seen: dict[tuple[str, str, str], set[str]] = {}
    for rec in retry_records:
        seen[_view_key(rec)] = {finding_id(rec, f) for f in rec.get("findings", [])}

    flakes = 0
    for rec in records:
        key = _view_key(rec)
        if key not in seen:
            continue                     # this page-view was not retried
        for f in rec.get("findings", []):
            if f.get("severity") != "error":
                continue
            if finding_id(rec, f) in seen[key]:
                continue                 # reproduced — it is real
            f["flaky"] = True
            f["severity"] = "warn"
            f["detail"] += " [did not reproduce on retry]"
            flakes += 1
    if flakes:
        log(f"  {flakes} error(s) did not reproduce — demoted to warnings (flaky)")
    return flakes


def look(
    cfg: Config,
    *,
    out_dir: str | Path | None = None,
    engine: str = "auto",              # "auto" | "browser" | "http"
    vision_mode: str = "off",          # "off" | "sample" | "all"
    make_montage: bool = True,
    baseline_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
    warn_as_error: bool = False,
    browser_path: str | None = None,
    retries: int = 0,
    log=print,
) -> LookResult:
    """Sweep the app and return findings. The only function anything calls."""
    started = datetime.now()
    run_dir = Path(out_dir) if out_dir else Path(DEFAULT_OUT) / started.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    doc, disc_note = fetch_discovery(cfg, log=log)
    params, unresolved = resolve_params(cfg, doc)
    if unresolved:
        for name, why in unresolved.items():
            log(f"  ! param {{{name}}} unresolved — {why}")

    chosen = engine
    if engine == "auto":
        chosen = "browser" if driver.have_playwright() else "http"
    if chosen == "browser" and not driver.have_playwright():
        raise RuntimeError(
            "engine 'browser' requested but Playwright is not installed.\n"
            "  pip install 'eye-of-thundera[browser]' && playwright install chromium"
        )

    log(f"Eye of Thundera — {cfg.name} @ {cfg.base} [{chosen}]")
    if chosen == "browser":
        records = driver.sweep_browser(
            cfg, params, run_dir, log=log, browser_path=browser_path
        )
    else:
        log("  (no browser — status codes only; install the [browser] extra for real sight)")
        records = driver.sweep_http(cfg, params, run_dir, log=log)

    # ── retries ──────────────────────────────────────────────────────────────
    # Re-run only the page-views that errored. `networkidle` never settles on
    # apps with polling or SSE, and a click can miss transiently; one bad run
    # should not be reported with the same confidence as a reproducible one.
    for attempt in range(retries):
        failed = {
            _view_key(r) for r in records
            if any(f.get("severity") == "error" for f in r.get("findings", []))
        }
        if not failed:
            break
        log(f"  retry {attempt + 1}/{retries}: re-running {len(failed)} failed page-view(s)")
        sweep = driver.sweep_browser if chosen == "browser" else driver.sweep_http
        kwargs = {"browser_path": browser_path} if chosen == "browser" else {}
        retry_records = sweep(
            cfg, params, run_dir, log=lambda *a: None, only=failed,
            shots_subdir=f"retry-{attempt + 1}", **kwargs,
        )
        if not settle_flakes(records, retry_records, log=log):
            break                        # everything reproduced; nothing to gain

    # ── vision (opt-in, sampled) ─────────────────────────────────────────────
    critiques: dict = {}
    if vision_mode != "off":
        wanted = set(cfg.vision_sample) if vision_mode == "sample" and cfg.vision_sample else None
        seen: set[str] = set()
        for rec in records:
            if not rec.get("screenshot"):
                continue
            if wanted is not None and rec["surface"] not in wanted:
                continue
            key = f"{rec['surface']}__{rec['profile']}__{rec['viewport']}"
            if vision_mode == "sample" and rec["surface"] in seen:
                continue        # one view per surface is enough for a style read
            seen.add(rec["surface"])
            log(f"  vision: {key} …")
            critiques[key] = vision.critique(run_dir / rec["screenshot"])

    meta = {
        "when": started.isoformat(timespec="seconds"),
        "app": cfg.name,
        "base": cfg.base,
        "engine": chosen,
        "profiles": [p.name for p in cfg.profiles],
        "viewports": [v.label for v in cfg.viewports],
        "surfaces": [s.key for s in cfg.surfaces],
        "config": str(cfg.source) if cfg.source else None,
        "discovery": disc_note,
        "params": params,
        "unresolved_params": unresolved,
        "duration_s": round((datetime.now() - started).total_seconds(), 1),
    }

    body = report.build(records, meta, vision=critiques or None)

    if baseline_path:
        try:
            body["baseline"] = baseline_mod.compare(
                body, baseline_mod.load(baseline_path), str(baseline_path)
            )
        except (FileNotFoundError, ValueError) as e:
            body["baseline"] = {"path": str(baseline_path), "error": str(e)}
            log(f"  ! baseline: {e}")

    # Artifacts are recorded in the body *before* it is serialised, so the
    # findings JSON is self-describing — an agent reading it can find the
    # screenshots and the montage without being told where they went.
    json_path = run_dir / "findings.json"
    artifacts: dict = {"json": str(json_path), "run_dir": str(run_dir)}
    if make_montage and any(r.get("screenshot") for r in records):
        if montage.available():
            artifacts["montages"] = [str(p) for p in montage.build(records, run_dir)]
        else:
            log("  (Pillow not installed — skipping montages)")
    if markdown_path:
        artifacts["markdown"] = str(markdown_path)
    body["artifacts"] = artifacts

    report.write_json(body, json_path)
    if markdown_path:
        report.write_markdown(body, Path(markdown_path))
    return LookResult(
        body=body,
        out_dir=run_dir,
        exit_code=report.exit_code(body, warn_as_error=warn_as_error),
        artifacts=artifacts,
    )


def preflight(cfg: Config) -> list[str]:
    """Non-fatal warnings about a config, for `thundera check`."""
    notes: list[str] = []
    declared = set(cfg.params) | set(cfg.discovery.params if cfg.discovery else {})
    for s in cfg.surfaces:
        missing = placeholders(s.path) - declared
        if missing:
            notes.append(
                f"surface '{s.key}' uses {{{', '.join(sorted(missing))}}} which nothing supplies "
                f"— it will always skip"
            )
    if not driver.have_playwright():
        notes.append("Playwright is not installed — runs will fall back to the http engine")
    elif not montage.available():
        notes.append("Pillow is not installed — no montages")
    return notes
