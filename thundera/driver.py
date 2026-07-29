"""The engines — visit every (surface × profile × viewport), measure, shoot.

Two of them, and the choice is automatic:

  browser  Playwright/Chromium. Real layout, real console, real screenshots.
           Everything the Eye is for.
  http     urllib only. Status codes and nothing else. Not a substitute — it
           exists so that `thundera look` still tells you something true on a
           box with no browser, instead of refusing to run.

`records` from either engine share a shape, so report/baseline never branch.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from .checks import COLLECT_JS, analyze
from .config import Config, Surface, resolve_path


def have_playwright() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
    except Exception:
        return False
    return True


def _record(cfg: Config, surf: Surface, profile: str, viewport: str, params: dict) -> dict:
    path, why = resolve_path(surf, params)
    rec = {
        "surface": surf.key,
        "group": surf.group,
        "profile": profile,
        "viewport": viewport,
        "path": path,
        "findings": [],
    }
    if path is None:
        rec["skipped"] = why
    else:
        rec["url"] = cfg.url_for(surf, path)
    return rec


# ── browser engine ───────────────────────────────────────────────────────────
def sweep_browser(
    cfg: Config,
    params: dict,
    out_dir: Path,
    *,
    log=print,
    browser_path: str | None = None,
    timeout_ms: int = 25000,
) -> list[dict]:
    """Run the full matrix in Chromium. One record per page-view."""
    from playwright.sync_api import sync_playwright

    shots_dir = out_dir / "screenshots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []

    launch: dict = {"args": ["--no-sandbox", "--autoplay-policy=no-user-gesture-required"]}
    if browser_path:
        launch["executable_path"] = browser_path

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch)
        try:
            for profile in cfg.profiles:
                surfaces = [s for s in cfg.surfaces if s.wants_profile(profile.name)]
                if not surfaces:
                    continue
                seeds = {**cfg.seeds, **profile.seeds}
                for vp in cfg.viewports:
                    ctx = browser.new_context(
                        viewport={"width": vp.width, "height": vp.height},
                        device_scale_factor=vp.scale,
                        is_mobile=vp.mobile,
                    )
                    if seeds:
                        # try/catch: some origins (file://, sandboxed) deny storage,
                        # and a seed failure must not abort the sweep.
                        ctx.add_init_script(
                            "try{"
                            + "".join(
                                f"localStorage.setItem({json.dumps(k)},{json.dumps(v)});"
                                for k, v in seeds.items()
                            )
                            + "}catch(e){}"
                        )
                    page = ctx.new_page()
                    ev: dict[str, list] = {"console": [], "failures": [], "pageerrors": []}
                    page.on(
                        "console",
                        lambda m: ev["console"].append(f"{m.type}: {m.text}")
                        if m.type in ("error", "warning")
                        else None,
                    )
                    page.on(
                        "response",
                        lambda r: ev["failures"].append(f"{r.status} {r.url}")
                        if r.status >= 400
                        else None,
                    )
                    page.on("pageerror", lambda e: ev["pageerrors"].append(str(e)))

                    for surf in surfaces:
                        rec = _record(cfg, surf, profile.name, vp.label, params)
                        if rec.get("skipped"):
                            records.append(rec)
                            continue
                        for k in ev:
                            ev[k].clear()
                        try:
                            page.goto(rec["url"], wait_until="networkidle", timeout=timeout_ms)
                        except Exception as e:
                            # networkidle never settling is common on apps with
                            # polling/SSE; measure anyway and note it.
                            rec["nav_note"] = f"{type(e).__name__} (continuing after settle)"
                        page.wait_for_timeout(surf.settle_ms)
                        click_failures: list[tuple[str, str]] = []
                        for raw_sel in surf.pre_clicks:
                            optional = raw_sel.startswith("?")
                            sel = raw_sel[1:] if optional else raw_sel
                            try:
                                page.click(sel, timeout=2500)
                                page.wait_for_timeout(800)
                            except Exception as e:
                                why = _click_reason(e)
                                if optional:
                                    # Absent by design on this viewport (a
                                    # hamburger that only exists on mobile).
                                    rec.setdefault("click_notes", []).append(
                                        f"{sel}: skipped (optional) — {why}"
                                    )
                                    continue
                                # Keep going — the screenshot still shows what
                                # the page actually looked like — but record it
                                # as a finding so nothing counts as verified.
                                click_failures.append((sel, why))
                                rec.setdefault("click_notes", []).append(f"{sel}: {why}")
                        try:
                            raw = page.evaluate(COLLECT_JS, surf.inventory or {})
                        except Exception as e:
                            raw = {}
                            rec["measure_error"] = str(e)[:200]
                        rec["findings"] = analyze(
                            raw,
                            ev["console"],
                            ev["failures"],
                            ev["pageerrors"],
                            mobile=vp.mobile,
                            severity=cfg.severity,
                            net_ignore=cfg.net_ignore,
                            click_failures=click_failures,
                        )
                        rec["inventory"] = raw.get("inventory", {})
                        shot = shots_dir / f"{surf.key}__{profile.name}__{vp.label}.png"
                        try:
                            page.screenshot(path=str(shot), full_page=True)
                            rec["screenshot"] = str(shot.relative_to(out_dir))
                        except Exception as e:
                            rec["screenshot_error"] = str(e)[:120]
                        log(f"  [{profile.name}/{vp.label}] {surf.key}: {_verdict(rec)}")
                        records.append(rec)
                    ctx.close()
        finally:
            browser.close()
    return records


def _click_reason(e: Exception) -> str:
    """A one-line why, from Playwright's multi-line call log."""
    name = type(e).__name__
    if "strict mode violation" in str(e):
        return f"{name}: selector matched more than one element"
    if name == "TimeoutError":
        return "never appeared or never became clickable"
    return f"{name}: {str(e).splitlines()[0][:100]}"


def _verdict(rec: dict) -> str:
    finds = rec.get("findings", [])
    if not finds:
        return "OK"
    n_err = sum(1 for f in finds if f["severity"] == "error")
    return f"{n_err} err, {len(finds) - n_err} warn"


# ── http engine (no browser required) ────────────────────────────────────────
def sweep_http(cfg: Config, params: dict, out_dir: Path, *, log=print, timeout: float = 15.0) -> list[dict]:
    """Status codes only. Every surface once — viewport/profile are meaningless
    without a renderer, so the matrix collapses to one row per surface."""
    records: list[dict] = []
    vp = cfg.viewports[0].label if cfg.viewports else "http"
    for surf in cfg.surfaces:
        rec = _record(cfg, surf, "http", vp, params)
        rec["engine_note"] = "status-code only (no browser available)"
        if rec.get("skipped"):
            records.append(rec)
            continue
        # A hash-routed path lives entirely client-side; only the shell can be
        # checked, so say so rather than implying the route was verified.
        url = rec["url"]
        if (surf.routing or cfg.routing) == "hash":
            url = url.split("#", 1)[0]
            rec["engine_note"] += " — hash route not verifiable without a browser"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "eye-of-thundera"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                rec["status"] = resp.status
                if resp.status >= 400:
                    rec["findings"] = [
                        {"kind": "net_4xx", "severity": cfg.severity.get("net_4xx", "error"),
                         "detail": f"{resp.status} {url}", "anchor": "status"}
                    ]
        except urllib.error.HTTPError as e:
            rec["status"] = e.code
            rec["findings"] = [
                {"kind": "net_4xx", "severity": cfg.severity.get("net_4xx", "error"),
                 "detail": f"{e.code} {url}", "anchor": "status"}
            ]
        except Exception as e:
            rec["status"] = None
            rec["findings"] = [
                {"kind": "net_4xx", "severity": cfg.severity.get("net_4xx", "error"),
                 "detail": f"{type(e).__name__} {url}", "anchor": "status"}
            ]
        log(f"  [http] {surf.key}: {rec.get('status')} — {_verdict(rec)}")
        records.append(rec)
    return records
