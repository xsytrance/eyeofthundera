"""Baseline diffing — "did my change break anything?"

An absolute finding count is nearly useless on a real app: every mature UI
carries a tail of accepted warnings, so a run that reports 38 findings tells an
agent nothing. What it needs is the delta. Record a baseline once, and every
later run answers the only question that matters — what is *new* since then,
and what did I fix.

Findings are matched by `finding_id`, which is anchored on the CSS path rather
than the detail string, so a box that shifts by half a pixel stays "the same
finding" instead of showing up as one fixed and one new.
"""
from __future__ import annotations

import json
from pathlib import Path

from .report import finding_id


def flatten(body: dict) -> dict[str, dict]:
    """{finding_id: {surface, profile, viewport, kind, severity, detail}}"""
    out: dict[str, dict] = {}
    for rec in body.get("records", []):
        for f in rec.get("findings", []):
            out[finding_id(rec, f)] = {
                "surface": rec.get("surface"),
                "profile": rec.get("profile"),
                "viewport": rec.get("viewport"),
                "kind": f.get("kind"),
                "severity": f.get("severity"),
                "detail": f.get("detail", ""),
            }
    return out


def load(path: str | Path) -> dict:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"no baseline at {p}")
    body = json.loads(p.read_text())
    if "records" not in body:
        raise ValueError(f"{p} is not an Eye findings file (no 'records')")
    return body


def compare(current: dict, baseline_body: dict, baseline_path: str) -> dict:
    """Diff two findings bodies. New = regressions; fixed = wins."""
    now, before = flatten(current), flatten(baseline_body)
    new_ids = [k for k in now if k not in before]
    fixed_ids = [k for k in before if k not in now]
    return {
        "path": str(baseline_path),
        "recorded": baseline_body.get("meta", {}).get("when"),
        "new": [now[k] for k in new_ids],
        "fixed": [before[k] for k in fixed_ids],
        "unchanged": len(now) - len(new_ids),
        "new_errors": sum(1 for k in new_ids if now[k]["severity"] == "error"),
    }


def save(body: dict, path: str | Path) -> Path:
    """Write the current run as the accepted baseline."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(body, indent=1))
    return p
