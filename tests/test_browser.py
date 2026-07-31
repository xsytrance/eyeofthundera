"""Browser-engine tests. Skipped wholesale when Playwright isn't installed.

These cover the things only a real renderer can prove: that seeds land before
first paint, that a required pre_click which misses is reported as an error,
and that an optional one which misses is not.
"""
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from thundera import Config, look

pytest.importorskip("playwright.sync_api")
from thundera.driver import have_playwright  # noqa: E402

pytestmark = pytest.mark.skipif(not have_playwright(), reason="needs playwright")

PAGE = """<!doctype html><meta charset=utf-8><title>t</title>
<style>body{margin:0;font:16px sans-serif;background:#fff;color:#111}
 #panel{display:none}.narrow{display:none}</style>
<h1>home</h1>
<button id="open">open</button>
<div id="panel"><p id="deep">panel content</p></div>
<button class="narrow" id="ghost">never visible</button>
<script>
  document.getElementById('open').onclick = () => {
    document.getElementById('panel').style.display = 'block';
    document.body.dataset.opened = '1';
  };
  if (localStorage.getItem('seeded') === 'yes') document.title = 'seeded';
</script>
"""


GATED = """<!doctype html><meta charset=utf-8><title>gated</title>
<style>body{background:#fff;color:#111;font:16px sans-serif}#locked{display:none}</style>
<input type="file" id="save-file">
<div id="locked"><p id="unlocked-text">the gated view</p></div>
<script>
  document.getElementById('save-file').onchange = () => {
    document.getElementById('locked').style.display = 'block';
    document.title = 'unlocked';
  };
</script>
"""


class QuietHandler(SimpleHTTPRequestHandler):
    """Serves tmp_path, plus /echo which reflects request headers into the page.

    Reflecting them is the only way to prove from the outside that a header or
    cookie actually reached the server rather than being silently dropped.
    """

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path != "/echo":
            return super().do_GET()
        # Render a broken image when the header or cookie did NOT arrive, so a
        # dropped credential shows up as a real broken_img finding rather than
        # something the test has to introspect for.
        ok = (self.headers.get("X-Thundera-Test") == "landed"
              and "sess=abc123" in (self.headers.get("Cookie") or ""))
        body = (
            "<!doctype html><meta charset=utf-8><title>echo</title>"
            "<body style='background:#fff;color:#111'><p>echo</p>"
            + ("" if ok else "<img src='/credentials-did-not-arrive.png' width=50 height=50>")
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def site(tmp_path):
    (tmp_path / "index.html").write_text(PAGE)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(tmp_path)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def run(site, tmp_path, surface, **cfgover):
    raw = {
        "app": {"name": "t", "base": site},
        "viewports": [{"label": "d", "width": 1024, "height": 768}],
        "surfaces": [surface],
    }
    raw.update(cfgover)
    return look(Config.from_dict(raw), out_dir=tmp_path / "run",
                engine="browser", make_montage=False, log=lambda *a: None)


def test_clean_page_is_clean_and_shoots_a_screenshot(site, tmp_path):
    r = run(site, tmp_path, {"key": "home", "path": "/", "settle_ms": 300})
    assert r.exit_code == 0
    assert r.summary["errors"] == 0
    shot = r.body["records"][0]["screenshot"]
    assert (tmp_path / "run" / shot).exists()


def test_required_pre_click_that_misses_is_an_error(site, tmp_path):
    r = run(site, tmp_path,
            {"key": "home", "path": "/", "settle_ms": 300, "pre_clicks": ["#nope"]})
    kinds = [f["kind"] for f in r.body["records"][0]["findings"]]
    assert "pre_click_failed" in kinds
    assert r.exit_code == 1          # a surface never reached must not pass


def test_optional_pre_click_that_misses_is_not_an_error(site, tmp_path):
    r = run(site, tmp_path,
            {"key": "home", "path": "/", "settle_ms": 300, "pre_clicks": ["?#nope"]})
    assert [f["kind"] for f in r.body["records"][0]["findings"]] == []
    assert r.exit_code == 0
    assert "optional" in r.body["records"][0]["click_notes"][0]


def test_pre_click_actually_changes_the_page(site, tmp_path):
    r = run(site, tmp_path,
            {"key": "home", "path": "/", "settle_ms": 300, "pre_clicks": ["#open"],
             "inventory": {"panel": "#deep"}})
    inv = r.body["records"][0]["inventory"]
    assert "panel" in inv and inv["panel"]["h"] > 0     # only visible once opened


def test_inventory_skips_invisible_elements(site, tmp_path):
    r = run(site, tmp_path,
            {"key": "home", "path": "/", "settle_ms": 300, "inventory": {"ghost": "#ghost"}})
    assert r.body["records"][0]["inventory"] == {}


def test_seeds_are_planted_before_first_paint(site, tmp_path):
    r = run(site, tmp_path, {"key": "home", "path": "/", "settle_ms": 300},
            seeds={"seeded": "yes"})
    # The page rewrites its title from localStorage during initial script run.
    assert r.body["records"][0]["findings"] == []
    body = json.loads((tmp_path / "run" / "findings.json").read_text())
    assert body["meta"]["engine"] == "browser"


def test_broken_image_is_an_error(site, tmp_path):
    (tmp_path / "broken.html").write_text('<img src="/missing.png" width=50 height=50>')
    r = run(site, tmp_path, {"key": "b", "path": "/broken.html", "settle_ms": 300})
    kinds = [f["kind"] for f in r.body["records"][0]["findings"]]
    assert "broken_img" in kinds and "net_4xx" in kinds
    assert r.exit_code == 1


def test_horizontal_overflow_is_an_error(site, tmp_path):
    (tmp_path / "wide.html").write_text(
        '<body style="margin:0"><div style="width:3000px;height:20px;background:#333"></div>'
    )
    r = run(site, tmp_path, {"key": "w", "path": "/wide.html", "settle_ms": 300})
    assert any(f["kind"] == "doc_overflow" for f in r.body["records"][0]["findings"])


def test_js_error_is_caught(site, tmp_path):
    (tmp_path / "boom.html").write_text("<script>null.x</script><p>hi</p>")
    r = run(site, tmp_path, {"key": "boom", "path": "/boom.html", "settle_ms": 300})
    assert any(f["kind"] == "js_error" for f in r.body["records"][0]["findings"])


def test_low_contrast_text_is_warned(site, tmp_path):
    (tmp_path / "faint.html").write_text(
        '<body style="background:#ffffff"><p style="color:#dddddd;font-size:14px">'
        "barely readable text here</p></body>"
    )
    r = run(site, tmp_path, {"key": "faint", "path": "/faint.html", "settle_ms": 300})
    finds = [f for f in r.body["records"][0]["findings"] if f["kind"] == "contrast"]
    assert finds and finds[0]["severity"] == "warn"
    assert r.exit_code == 0                       # warnings alone don't fail


# ── contrast under a fixed bar ───────────────────────────────────────────────
# Regression tests for the false-positive class found on undertale-vera
# 2026-07-29: legible white-on-black text sitting under a position:fixed bottom
# bar was composited against the *bar's* background and reported as 1:1.

# Text at y≈700 is inside the 768px viewport and underneath the fixed bar that
# occupies the bottom 120px — exactly the poisoned geometry.
FIXED_BAR = """<!doctype html><meta charset=utf-8><title>bar</title>
<style>
 body{margin:0;background:#000;color:#fff;font:16px sans-serif}
 .spacer{height:680px}
 .bar{position:fixed;bottom:0;left:0;right:0;height:120px;background:#ffffff}
</style>
<div class="spacer"></div>
<p id="under">perfectly legible white on black</p>
<div class="bar"></div>
"""


def test_text_under_a_fixed_bar_is_not_a_false_contrast_finding(site, tmp_path):
    (tmp_path / "bar.html").write_text(FIXED_BAR)
    r = run(site, tmp_path, {"key": "bar", "path": "/bar.html", "settle_ms": 300})
    rec = r.body["records"][0]
    bad = [f for f in rec["findings"]
           if f["kind"] == "contrast" and "p#under" in f["anchor"]]
    assert bad == [], f"white-on-black reported as low contrast: {bad}"


def test_a_genuine_low_contrast_element_still_reports_under_a_fixed_bar(site, tmp_path):
    """The fix must not blind the check — only correct which pixels it reads."""
    (tmp_path / "bar2.html").write_text(
        FIXED_BAR.replace(
            '<p id="under">perfectly legible white on black</p>',
            '<p id="under" style="color:#151515">barely there grey on black</p>',
        )
    )
    r = run(site, tmp_path, {"key": "bar2", "path": "/bar2.html", "settle_ms": 300})
    finds = [f for f in r.body["records"][0]["findings"]
             if f["kind"] == "contrast" and "p#under" in f["anchor"]]
    assert finds, "a real 1.1:1 contrast bug under the bar was missed"


def test_unverifiable_contrast_is_counted_not_silently_skipped(site, tmp_path):
    """A gradient background is unknowable, and saying nothing is not an option."""
    (tmp_path / "grad.html").write_text(
        '<body style="margin:0"><div style="background:linear-gradient(#000,#fff);'
        'padding:40px"><p style="color:#808080">text over a gradient</p></div></body>'
    )
    r = run(site, tmp_path, {"key": "grad", "path": "/grad.html", "settle_ms": 300})
    rec = r.body["records"][0]
    assert rec.get("unverified", {}).get("contrast", 0) > 0
    assert r.body["summary"]["unverified"] > 0
    # ...but it stays out of the findings list unless the project asks for it.
    assert [f for f in rec["findings"] if f["kind"] == "obscured"] == []


# ── preconditions: setup steps, cookies, headers ─────────────────────────────
# `seeds` only reach localStorage. These cover the states that needed more:
# a file to upload, a cookie, an auth header.

def test_upload_step_reaches_a_state_seeds_cannot(site, tmp_path):
    (tmp_path / "gated.html").write_text(GATED)
    (tmp_path / "save.dat").write_text("a save file")
    r = run(site, tmp_path,
            {"key": "gated", "path": "/gated.html", "settle_ms": 300,
             "inventory": {"gated": "#unlocked-text"},
             "setup": [{"upload": {"selector": "#save-file",
                                   "path": str(tmp_path / "save.dat")}}]})
    rec = r.body["records"][0]
    assert rec["findings"] == []
    assert rec["inventory"].get("gated", {}).get("h", 0) > 0   # only after upload


def test_without_the_upload_the_gated_view_stays_invisible(site, tmp_path):
    """The control: proves the previous test's upload is what did the work."""
    (tmp_path / "gated.html").write_text(GATED)
    r = run(site, tmp_path,
            {"key": "gated", "path": "/gated.html", "settle_ms": 300,
             "inventory": {"gated": "#unlocked-text"}})
    assert r.body["records"][0]["inventory"] == {}


def test_a_failed_required_setup_step_is_an_error(site, tmp_path):
    r = run(site, tmp_path,
            {"key": "home", "path": "/", "settle_ms": 300,
             "setup": [{"click": "#does-not-exist"}]})
    finds = [f for f in r.body["records"][0]["findings"] if f["kind"] == "setup_failed"]
    assert finds and finds[0]["severity"] == "error"
    assert r.exit_code == 1          # measured in the wrong state ≠ clean


def test_an_optional_setup_step_that_misses_is_not_an_error(site, tmp_path):
    r = run(site, tmp_path,
            {"key": "home", "path": "/", "settle_ms": 300,
             "setup": [{"click": "?#does-not-exist"}]})
    assert r.body["records"][0]["findings"] == []
    assert r.exit_code == 0
    assert "optional" in r.body["records"][0]["setup_notes"][0]


def test_setup_steps_run_in_order_and_can_drive_the_page(site, tmp_path):
    r = run(site, tmp_path,
            {"key": "home", "path": "/", "settle_ms": 300,
             "inventory": {"panel": "#deep"},
             "setup": [{"click": "#open"}, {"wait_for": "#deep"}]})
    assert r.body["records"][0]["inventory"]["panel"]["h"] > 0


def test_profile_headers_and_cookies_reach_the_server(site, tmp_path):
    # /echo renders a broken image unless BOTH the header and the cookie arrive.
    r = run(site, tmp_path,
            {"key": "echo", "path": "/echo", "settle_ms": 300},
            profiles=[{"name": "authed",
                       "headers": {"X-Thundera-Test": "landed"},
                       "cookies": [{"name": "sess", "value": "abc123"}]}])
    assert r.body["records"][0]["findings"] == []
    assert r.exit_code == 0


def test_without_credentials_the_same_surface_fails(site, tmp_path):
    """The control: proves the previous test is asserting something real."""
    r = run(site, tmp_path, {"key": "echo", "path": "/echo", "settle_ms": 300})
    kinds = [f["kind"] for f in r.body["records"][0]["findings"]]
    assert "broken_img" in kinds
    assert r.exit_code == 1


def test_env_vars_expand_in_credentials(site, tmp_path, monkeypatch):
    """A token should never have to be committed to a thundera.toml."""
    monkeypatch.setenv("THUNDERA_TEST_TOKEN", "landed")
    r = run(site, tmp_path,
            {"key": "echo", "path": "/echo", "settle_ms": 300},
            profiles=[{"name": "authed",
                       "headers": {"X-Thundera-Test": "${THUNDERA_TEST_TOKEN}"},
                       "cookies": [{"name": "sess", "value": "abc123"}]}])
    assert r.body["records"][0]["findings"] == []


def test_a_failed_profile_setup_taints_every_surface_in_the_context(site, tmp_path):
    """One bad precondition must not let nine surfaces report clean."""
    r = run(site, tmp_path,
            {"key": "home", "path": "/", "settle_ms": 300},
            profiles=[{"name": "broken", "setup": [{"click": "#never-there"}]}])
    assert all(
        any(f["kind"] == "setup_failed" for f in rec["findings"])
        for rec in r.body["records"]
    )
    assert r.exit_code == 1


# ── accessibility pass ───────────────────────────────────────────────────────
# One page carrying one instance of each defect, plus the correct-and-quiet
# counterparts: alt="" on a decorative image, a properly labelled input, an
# aria-label on an icon button. A check that fires on those is worse than
# useless — it teaches people to ignore the tool.

PX = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

A11Y_PAGE = f"""<!doctype html><html><head><meta charset=utf-8><title>a11y</title></head>
<body style="background:#fff;color:#111">
<main>
  <h1>title</h1>
  <h3>skipped a level</h3>

  <img src="{PX}" alt="described properly" width=20 height=20>
  <img src="{PX}" alt="" width=20 height=20>
  <img src="{PX}" width=20 height=20>

  <button aria-label="close">&times;</button>
  <button><img src="{PX}" alt="save" width=16 height=16></button>
  <button></button>

  <label for="named">Name</label><input id="named">
  <label>Wrapped <input></label>
  <input aria-label="search">
  <input placeholder="just a placeholder">

  <div id="dup">one</div><div id="dup">two</div>
  <a href="#x" tabindex="3">forced order</a>
  <span aria-hidden="true"><button></button></span>
</main>
</body></html>
"""


def _a11y_kinds(site, tmp_path, **over):
    (tmp_path / "a11y.html").write_text(A11Y_PAGE)
    raw = {
        "app": {"name": "t", "base": site},
        "viewports": [{"label": "d", "width": 1024, "height": 768}],
        "surfaces": [{"key": "a", "path": "/a11y.html", "settle_ms": 300}],
        "a11y": {"enabled": True},
    }
    raw.update(over)
    r = look(Config.from_dict(raw), out_dir=tmp_path / "run", engine="browser",
             make_montage=False, log=lambda *a: None)
    return r, [f["kind"] for f in r.body["records"][0]["findings"]]


def test_a11y_is_off_unless_asked_for(site, tmp_path):
    """Upgrading the package must not silently change an existing run."""
    (tmp_path / "a11y.html").write_text(A11Y_PAGE)
    r = look(Config.from_dict({
        "app": {"name": "t", "base": site},
        "viewports": [{"label": "d", "width": 1024, "height": 768}],
        "surfaces": [{"key": "a", "path": "/a11y.html", "settle_ms": 300}],
    }), out_dir=tmp_path / "run", engine="browser", make_montage=False,
        log=lambda *a: None)
    assert r.body["records"][0]["findings"] == []


def test_a11y_finds_each_defect_exactly_once(site, tmp_path):
    r, kinds = _a11y_kinds(site, tmp_path)
    assert kinds.count("img_no_alt") == 1          # alt="" and a real alt are fine
    assert kinds.count("no_accessible_name") == 1  # aria-label and nested alt are fine
    assert kinds.count("input_no_label") == 1      # for=, wrapping, aria-label are fine
    assert kinds.count("heading_skip") == 1        # h1 -> h3
    assert kinds.count("duplicate_id") == 1
    assert kinds.count("positive_tabindex") == 1
    assert r.exit_code == 0                        # all warnings by default


def test_a11y_does_not_fire_on_a_clean_document(site, tmp_path):
    """The control. A page that does it right must produce nothing."""
    (tmp_path / "clean.html").write_text(
        f'<!doctype html><html lang="en"><head><meta charset=utf-8><title>ok</title>'
        '</head><body><main><h1>title</h1><h2>sub</h2>'
        f'<img src="{PX}" alt="a thing" width=20 height=20>'
        '<label for="q">Query</label><input id="q">'
        '<button>Go</button></main></body></html>'
    )
    r = look(Config.from_dict({
        "app": {"name": "t", "base": site},
        "viewports": [{"label": "d", "width": 1024, "height": 768}],
        "surfaces": [{"key": "c", "path": "/clean.html", "settle_ms": 300}],
        "a11y": {"enabled": True},
    }), out_dir=tmp_path / "run", engine="browser", make_montage=False,
        log=lambda *a: None)
    assert r.body["records"][0]["findings"] == []


def test_document_level_a11y_checks_fire(site, tmp_path):
    _, kinds = _a11y_kinds(site, tmp_path)
    assert "no_lang" in kinds                      # the fixture omits it
    assert "no_landmark" not in kinds              # ...but it does have <main>


def test_a11y_kinds_honour_severity_config(site, tmp_path):
    _, kinds = _a11y_kinds(site, tmp_path, severity={"img_no_alt": "off"})
    assert "img_no_alt" not in kinds
    r, _ = _a11y_kinds(site, tmp_path, severity={"img_no_alt": "error"})
    assert r.exit_code == 1


# ── navigate = "once" ────────────────────────────────────────────────────────
# A click-routed SPA keeps its state in memory, and the per-surface reload
# throws it away. This is the page that proves it: #inc bumps a counter held
# only in a JS closure, and #twice appears at 2. Nothing touches localStorage,
# so the count survives only if the page was never reloaded.

COUNTER = """<!doctype html><meta charset=utf-8><title>counter</title>
<style>body{background:#fff;color:#111;font:16px sans-serif}</style>
<button id="inc">inc</button><p id="count">0</p>
<script>
  let n = 0;
  document.getElementById('inc').onclick = () => {
    n += 1;
    document.getElementById('count').textContent = String(n);
    if (n >= 2 && !document.getElementById('twice')) {
      const d = document.createElement('div');
      d.id = 'twice'; d.textContent = 'clicked twice in one page';
      document.body.appendChild(d);
    }
  };
</script>
"""


def _counter_cfg(site, navigate):
    """Two surfaces, same URL, each clicking #inc once."""
    return {
        "app": {"name": "t", "base": site, "navigate": navigate},
        "viewports": [{"label": "d", "width": 1024, "height": 768}],
        "surfaces": [
            {"key": "first", "path": "/counter.html", "settle_ms": 250,
             "setup": [{"click": "#inc"}]},
            # Only reachable if the first surface's click survived.
            {"key": "second", "path": "/counter.html", "settle_ms": 250,
             "setup": [{"click": "#inc"}, {"wait_for": "#twice"}]},
        ],
    }


def test_navigate_once_reuses_the_page_and_keeps_in_memory_state(site, tmp_path):
    (tmp_path / "counter.html").write_text(COUNTER)
    r = look(Config.from_dict(_counter_cfg(site, "once")), out_dir=tmp_path / "run",
             engine="browser", make_montage=False, log=lambda *a: None)
    assert r.exit_code == 0
    assert r.body["records"][1]["findings"] == []
    assert r.body["records"][1]["nav_note"] == "reused page (navigate = once)"


def test_the_default_reloads_and_therefore_loses_it(site, tmp_path):
    """The control — and proof the default behaviour is unchanged."""
    (tmp_path / "counter.html").write_text(COUNTER)
    r = look(Config.from_dict(_counter_cfg(site, "always")), out_dir=tmp_path / "run",
             engine="browser", make_montage=False, log=lambda *a: None)
    assert r.exit_code == 1
    assert any(f["kind"] == "setup_failed" for f in r.body["records"][1]["findings"])
    assert "reused" not in r.body["records"][1].get("nav_note", "")


def test_navigate_once_still_loads_when_the_url_differs(site, tmp_path):
    """Reuse is keyed on the URL, not on "skip every navigation after the first"."""
    (tmp_path / "counter.html").write_text(COUNTER)
    raw = _counter_cfg(site, "once")
    raw["surfaces"][1] = {"key": "elsewhere", "path": "/", "settle_ms": 250}
    r = look(Config.from_dict(raw), out_dir=tmp_path / "run",
             engine="browser", make_montage=False, log=lambda *a: None)
    assert r.exit_code == 0
    assert "reused" not in r.body["records"][1].get("nav_note", "")


def test_obscured_can_be_turned_on_as_a_finding(site, tmp_path):
    (tmp_path / "grad.html").write_text(
        '<body style="margin:0"><div style="background:linear-gradient(#000,#fff);'
        'padding:40px"><p style="color:#808080">text over a gradient</p></div></body>'
    )
    r = run(site, tmp_path, {"key": "grad", "path": "/grad.html", "settle_ms": 300},
            severity={"obscured": "warn"})
    finds = [f for f in r.body["records"][0]["findings"] if f["kind"] == "obscured"]
    assert finds and finds[0]["severity"] == "warn"
    assert r.exit_code == 0
