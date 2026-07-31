"""The animation is cosmetic, but its containment is not — it must never
contaminate the stdout that agents parse."""
import io

from thundera import eye


def test_frames_are_a_rectangular_grid():
    for f in eye.frames():
        widths = {len(line) for line in f.splitlines()}
        # lid rows are one char narrower than the paren rows, by design
        assert widths <= {eye.WIDTH, eye.WIDTH + 1}


def test_the_eye_opens_progressively():
    heights = [len(f.splitlines()) for f in eye.frames()]
    assert heights == sorted(heights)          # never shrinks mid-open
    assert heights[0] < heights[-1]


def test_disabled_writes_nothing():
    buf = io.StringIO()
    eye.open_eye(buf, force=False)
    eye.verdict("ok", "all good", buf, force=False)
    assert buf.getvalue() == ""


def test_forced_on_writes_to_the_given_stream_only(capsys):
    buf = io.StringIO()
    eye.open_eye(buf, delay=0, force=True)
    eye.verdict("error", "1 errors", buf, force=True)
    out = buf.getvalue()
    assert eye.MOTTO in out
    assert "1 errors" in out
    captured = capsys.readouterr()
    assert captured.out == ""                  # nothing leaked to stdout


def test_a_plain_stream_gets_no_escape_codes_at_all():
    """Redirected stderr must stay readable — no colour, no cursor control."""
    buf = io.StringIO()
    eye.open_eye(buf, delay=0, force=True)
    eye.verdict("error", "boom", buf, force=True)
    assert "\033" not in buf.getvalue()


def test_env_var_disables_it(monkeypatch):
    monkeypatch.setenv("THUNDERA_NO_ANIM", "1")
    assert eye.enabled(io.StringIO()) is False


def test_non_tty_is_off_by_default():
    assert eye.enabled(io.StringIO()) is False


def test_status_reflects_the_summary():
    assert eye.status_of({"errors": 0, "warnings": 0}) == "ok"
    assert eye.status_of({"errors": 0, "warnings": 3}) == "warn"
    assert eye.status_of({"errors": 1, "warnings": 3}) == "error"


def test_error_verdict_uses_a_different_iris():
    assert eye.IRIS["error"] != eye.IRIS["ok"]
    assert eye.IRIS["error"] in eye.open_frame(eye.IRIS["error"])


# ── forcing the eye on ───────────────────────────────────────────────────────
# An agent's stderr is a pipe, never a terminal, so auto-detect says no every
# time. --animation is the only way it can draw the eye deliberately — on first
# use, or at the start of a new mission.

def test_a_forced_eye_draws_into_a_pipe_with_no_escape_codes():
    import io

    from thundera import eye

    buf = io.StringIO()                       # not a tty
    eye.open_eye(buf, force=True, delay=0)
    eye.verdict("error", "3 errors", buf, force=True)
    out = buf.getvalue()
    assert "sight beyond sight" in out
    assert "(x)" in out                        # the verdict iris, not the idle one
    assert "\033" not in out                   # safe to capture in a log


def test_cli_animation_flag_forces_it_and_json_still_wins(monkeypatch, capsys):
    """--json outranks --animation: stdout must stay pure JSON."""
    from thundera.cli import build_parser

    p = build_parser()
    a = p.parse_args(["look", "http://x", "--animation"])
    assert a.animation is True and a.no_animation is False
    b = p.parse_args(["look", "http://x", "--animation", "--json"])
    assert b.animation is True and b.json is True     # cmd_look resolves to off
