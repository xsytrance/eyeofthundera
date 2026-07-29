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
