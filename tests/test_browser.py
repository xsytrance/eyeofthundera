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


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


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
