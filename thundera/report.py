"""Findings → the agent JSON contract, and a human Markdown report.

The JSON is the product. Agents parse it, so its shape is versioned and
additive-only: new keys may appear, existing keys never change meaning and
never disappear without a `schema_version` bump.
"""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA_VERSION = 1
TOOL = "eye-of-thundera"


def finding_id(rec: dict, finding: dict) -> str:
    """Stable identity for a finding across runs.

    Deliberately excludes `detail`, which carries pixel values that jitter by a
    subpixel between runs — an anchor (usually the CSS path) is what makes two
    findings "the same problem" for baseline comparison.
    """
    return "|".join((
        rec.get("surface", "?"),
        rec.get("profile", "?"),
        rec.get("viewport", "?"),
        finding.get("kind", "?"),
        finding.get("anchor") or finding.get("detail", ""),
    ))


def summarize(records: list[dict]) -> dict:
    views = {"clean": 0, "with_warnings": 0, "with_errors": 0, "skipped": 0}
    errors = warnings = 0
    # Measurements the collector abstained from. Counted even when the matching
    # finding kind is severity "off", so that "0 warnings" can never be mistaken
    # for "everything was checked".
    unverified = 0
    for r in records:
        unverified += sum((r.get("unverified") or {}).values())
        if r.get("skipped"):
            views["skipped"] += 1
            continue
        sevs = [f["severity"] for f in r.get("findings", [])]
        errors += sevs.count("error")
        warnings += sevs.count("warn")
        if "error" in sevs:
            views["with_errors"] += 1
        elif sevs:
            views["with_warnings"] += 1
        else:
            views["clean"] += 1
    return {
        "page_views": len(records), **views,
        "errors": errors, "warnings": warnings, "unverified": unverified,
    }


def build(records: list[dict], meta: dict, vision: dict | None = None,
          baseline: dict | None = None) -> dict:
    body = {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "meta": meta,
        "summary": summarize(records),
        "records": records,
    }
    if vision:
        body["vision"] = vision
    if baseline is not None:
        body["baseline"] = baseline
    return body


def write_json(body: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=1))
    return path


def exit_code(body: dict, warn_as_error: bool = False) -> int:
    """0 clean, 1 findings that count as failure. Used to gate CI."""
    s = body["summary"]
    if s["errors"]:
        return 1
    if warn_as_error and s["warnings"]:
        return 1
    return 0


# ── human report ─────────────────────────────────────────────────────────────
def write_markdown(body: dict, path: Path) -> Path:
    meta, s = body["meta"], body["summary"]
    records = body["records"]
    ok = s["with_errors"] == 0
    title = "ALL CLEAR ✅" if ok else f"{s['with_errors']} SURFACES WITH ERRORS ❌"
    lines = [
        f"# Eye of Thundera — {title}",
        "",
        f"- **App**: {meta.get('app')}  ·  **Base**: {meta.get('base')}",
        f"- **When**: {meta.get('when')}  ·  **Engine**: {meta.get('engine')}",
        f"- **Profiles**: {', '.join(meta.get('profiles', []))}"
        f"  ·  **Viewports**: {', '.join(meta.get('viewports', []))}",
        f"- **Result**: {s['clean']} clean, {s['with_warnings']} with warnings, "
        f"{s['with_errors']} with errors, {s['skipped']} skipped "
        f"(of {s['page_views']} page-views)",
        "",
    ]
    if s.get("unverified"):
        lines += [
            f"> ⚪ **{s['unverified']} measurements could not be judged** — a gradient "
            "or image background, or a paint stack the hit test could not resolve. "
            "Not failures; things the Eye declined to guess at.",
            "",
        ]

    bl = body.get("baseline")
    if bl:
        lines += [
            f"## Against baseline `{bl.get('path')}`",
            "",
            f"- **{len(bl.get('new', []))} new**, **{len(bl.get('fixed', []))} fixed**, "
            f"{bl.get('unchanged', 0)} unchanged",
            "",
        ]
        for f in bl.get("new", [])[:20]:
            lines.append(f"- 🆕 `{f['surface']}` {f['kind']}: {f['detail'][:150]}")
        for f in bl.get("fixed", [])[:20]:
            lines.append(f"- ✅ `{f['surface']}` {f['kind']}: {f['detail'][:150]}")
        lines.append("")

    lines += ["| Surface | Profile | Viewport | Status | Findings |", "|---|---|---|---|---|"]
    for r in records:
        if r.get("skipped"):
            lines.append(
                f"| {r['surface']} | {r['profile']} | {r['viewport']} | ⏭️ SKIP | {r['skipped']} |"
            )
            continue
        finds = r.get("findings", [])
        errs = [f for f in finds if f["severity"] == "error"]
        status = "❌ FAIL" if errs else ("⚠️ WARN" if finds else "✅ PASS")
        detail = "; ".join(f"{f['kind']}: {f['detail']}" for f in finds[:3]) or "—"
        if len(finds) > 3:
            detail += f" (+{len(finds) - 3} more)"
        detail = detail.replace("|", "\\|")
        lines.append(
            f"| {r['surface']} | {r['profile']} | {r['viewport']} | {status} | {detail[:220]} |"
        )

    vision = body.get("vision")
    if vision:
        lines += ["", "## Vision critique (local model, advisory)", "",
                  "| Surface | Polish | Layout ok | One improvement |", "|---|---|---|---|"]
        for key, v in vision.items():
            if "error" in v:
                lines.append(f"| {key} | — | — | _{v['error'][:100]}_ |")
            else:
                lines.append(
                    f"| {key} | {v.get('polish_score_0_to_10', '—')}/10 "
                    f"| {'✅' if v.get('layout_ok') else '❌'} "
                    f"| {str(v.get('one_improvement', ''))[:140]} |"
                )

    lines += ["", f"_Generated by {TOOL}_", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    return path


def write_text_summary(body: dict) -> str:
    """The short console verdict printed at the end of a run."""
    s = body["summary"]
    head = (
        f"{s['clean']} clean · {s['with_warnings']} warn · {s['with_errors']} error "
        f"· {s['skipped']} skipped  ({s['errors']} errors, {s['warnings']} warnings)"
    )
    if s.get("unverified"):
        head += f"\n{s['unverified']} measurements could not be judged (see `unverified`)"
    bl = body.get("baseline")
    if bl:
        head += f"\nvs baseline: {len(bl.get('new', []))} new, {len(bl.get('fixed', []))} fixed"
    return head
