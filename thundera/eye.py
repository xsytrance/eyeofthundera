"""The Eye — an opening animation, and a verdict that encodes the result.

Decoration that earns its place: the iris at the end of a run *is* the verdict,
so the thing you watch is also the thing you read.

Hard rule, because agents depend on it: **this never touches stdout.** It draws
on stderr, and only when stderr is a terminal. In a pipe, in CI, under --json
or --quiet, it does not exist.

Frames are generated on a fixed grid rather than hand-drawn, so every row is
the same width and successive frames overwrite each other cleanly.
"""
from __future__ import annotations

import os
import sys
import time

W = 32          # interior width, between the outer parens
LID = 30        # width of the lid rules

_TOP = "     ." + "-" * LID + "."
_BOT = "     '" + "-" * LID + "'"


def _row(inner: str = "") -> str:
    return "    (" + inner.center(W) + ")"


def _lens(width: int, rows: list[str]) -> list[str]:
    """An aperture `width` wide, with `rows` of interior content."""
    out = ["." + "-" * width + "."]
    out += ["|" + r.center(width) + "|" for r in rows]
    out += ["'" + "-" * width + "'"]
    return [_row(line) for line in out]


def _frame(*body: str) -> str:
    return "\n".join((_TOP, *body, _BOT))


def frames(iris: str = "(o)") -> list[str]:
    """The full open sequence, ending on the eye wide open."""
    return [
        _frame(_row("-" * 24)),
        _frame(*_lens(18, [])),
        _frame(*_lens(20, [""])),
        _frame(*_lens(20, ["", ".--.", ""])),
        _frame(*_lens(20, ["", iris, ""])),
        open_frame(iris),
    ]


def open_frame(iris: str = "(o)") -> str:
    return _frame(*_lens(20, ["", "", iris, "", ""]))


IRIS = {"ok": "(o)", "warn": "(o)", "error": "(x)", "idle": "(o)"}

ANSI = {
    "ok": "\033[32m",
    "warn": "\033[33m",
    "error": "\033[31m",
    "idle": "\033[36m",
    "dim": "\033[2m",
    "off": "\033[0m",
}

MOTTO = "sight beyond sight"
WIDTH = len(_TOP)


def enabled(stream=None, force: bool | None = None) -> bool:
    """Animate only for a human at a terminal."""
    if force is not None:
        return force
    if os.getenv("THUNDERA_NO_ANIM"):
        return False
    stream = stream or sys.stderr
    try:
        return bool(stream.isatty())
    except Exception:
        return False


def _tty(stream) -> bool:
    """Whether cursor control is meaningful — i.e. can we redraw in place."""
    try:
        return bool(stream.isatty())
    except Exception:
        return False


def _colour(stream) -> bool:
    return _tty(stream) and not os.getenv("NO_COLOR")


def _paint(text: str, key: str, stream) -> str:
    if not _colour(stream):
        return text
    return f"{ANSI.get(key, '')}{text}{ANSI['off']}"


def open_eye(stream=None, *, delay: float = 0.07, force: bool | None = None) -> None:
    """Play the eye opening. Silent no-op when not animating."""
    stream = stream or sys.stderr
    if not enabled(stream, force):
        return
    if not _tty(stream):
        # Redirected to a file or a pipe: no cursor to move, so draw the open
        # eye once rather than spraying control codes into somebody's log.
        stream.write(open_frame(IRIS["idle"]) + "\n")
        stream.write(MOTTO.center(WIDTH) + "\n\n")
        stream.flush()
        return
    prev = 0
    for frame in frames(IRIS["idle"]):
        if prev:
            stream.write(f"\033[{prev}A\033[J")      # rewind over the last frame
        stream.write(_paint(frame, "idle", stream) + "\n")
        stream.flush()
        prev = len(frame.splitlines())
        time.sleep(delay)
    stream.write(_paint(MOTTO.center(WIDTH), "dim", stream) + "\n\n")
    stream.flush()


def verdict(status: str, line: str = "", stream=None, *, force: bool | None = None) -> None:
    """The closing eye, iris coloured by outcome: ok / warn / error."""
    stream = stream or sys.stderr
    if not enabled(stream, force):
        return
    body = open_frame(IRIS.get(status, IRIS["idle"]))
    stream.write(_paint(body, status, stream) + "\n")
    if line:
        stream.write(_paint(line.center(WIDTH), status, stream) + "\n")
    stream.write("\n")
    stream.flush()


def status_of(summary: dict) -> str:
    if summary.get("errors"):
        return "error"
    if summary.get("warnings"):
        return "warn"
    return "ok"
