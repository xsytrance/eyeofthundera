"""Optional LLM eyes — a local vision model's critique of a screenshot.

The deterministic checks stay authoritative; this adds the judgment call a
human reviewer would make ("does this read as professional?"). It is slow
(~30s per screenshot on a decent local GPU), hence opt-in and sampled.

Any failure degrades to a note in the report, never an error — a missing
Ollama must not fail somebody's CI.
"""
from __future__ import annotations

import base64
import io
import json
import os
import urllib.request

DEFAULT_MODEL = "qwen3-vl:8b"
DEFAULT_HOST = "http://127.0.0.1:11434"

RUBRIC = """Review this web app screenshot as a meticulous UI QA inspector.
Respond with ONLY a JSON object:
{"page_title": str, "layout_ok": bool, "misalignments": [str],
 "clipped_or_overlapping": [str], "empty_or_broken_regions": [str],
 "polish_score_0_to_10": int, "one_improvement": str}"""


def available(host: str | None = None, timeout: float = 2.0) -> bool:
    host = host or os.getenv("OLLAMA_HOST", DEFAULT_HOST)
    try:
        urllib.request.urlopen(f"{host}/api/tags", timeout=timeout).read(1)
        return True
    except Exception:
        return False


def critique(png_path, *, model: str | None = None, host: str | None = None,
             timeout: int = 240) -> dict:
    """Return the model's structured verdict, or {"error": ...} on any failure."""
    model = model or os.getenv("THUNDERA_VISION_MODEL", DEFAULT_MODEL)
    host = host or os.getenv("OLLAMA_HOST", DEFAULT_HOST)
    try:
        from PIL import Image

        im = Image.open(png_path).convert("RGB")
        im.thumbnail((1024, 1024))  # full-res PNGs 500 on some Ollama builds
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
        img_b64 = base64.b64encode(buf.getvalue()).decode()
        payload = {
            "model": model,
            "stream": False,
            "format": "json",
            "messages": [{"role": "user", "content": RUBRIC, "images": [img_b64]}],
        }
        req = urllib.request.Request(
            f"{host}/api/chat",
            json.dumps(payload).encode(),
            {"Content-Type": "application/json"},
        )
        resp = json.load(urllib.request.urlopen(req, timeout=timeout))
        return json.loads(resp["message"]["content"])
    except Exception as e:  # vision is best-effort by contract
        return {"error": f"{type(e).__name__}: {e}"}
