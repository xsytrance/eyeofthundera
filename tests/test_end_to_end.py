"""A real sweep against a real server, using the http engine (no browser needed)."""
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from thundera import Config, look
from thundera.cli import main


@pytest.fixture
def site(tmp_path):
    (tmp_path / "index.html").write_text("<h1>hello</h1>")
    (tmp_path / "about.html").write_text("<h1>about</h1>")
    handler = partial(QuietHandler, directory=str(tmp_path))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def cfg_for(site, tmp_path, **over):
    raw = {"app": {"name": "site", "base": site, "paths": ["/", "/about.html"]}}
    raw.update(over)
    return Config.from_dict(raw)


def test_http_sweep_finds_a_clean_site(site, tmp_path):
    r = look(cfg_for(site, tmp_path), out_dir=tmp_path / "run", engine="http", log=lambda *a: None)
    assert r.exit_code == 0
    assert r.summary["clean"] == 2
    assert r.summary["errors"] == 0
    assert all(rec["status"] == 200 for rec in r.body["records"])


def test_http_sweep_catches_a_missing_page(site, tmp_path):
    cfg = cfg_for(site, tmp_path, app={"base": site, "paths": ["/", "/gone.html"]})
    r = look(cfg, out_dir=tmp_path / "run", engine="http", log=lambda *a: None)
    assert r.exit_code == 1
    assert r.summary["with_errors"] == 1
    bad = [rec for rec in r.body["records"] if rec["surface"] == "gone-html"][0]
    assert bad["status"] == 404


def test_findings_json_is_written_and_parseable(site, tmp_path):
    r = look(cfg_for(site, tmp_path), out_dir=tmp_path / "run", engine="http", log=lambda *a: None)
    body = json.loads((tmp_path / "run" / "findings.json").read_text())
    assert body["schema_version"] == 1
    assert body["meta"]["engine"] == "http"
    assert len(body["records"]) == 2
    # self-describing: the file on disk names its own artifacts
    assert body["artifacts"]["json"].endswith("findings.json")
    assert body["artifacts"]["run_dir"] == str(tmp_path / "run")


def test_unresolvable_surface_skips_with_a_reason_rather_than_failing(site, tmp_path):
    cfg = cfg_for(site, tmp_path, app={"base": site, "paths": ["/", "/p/{project_id}"]})
    r = look(cfg, out_dir=tmp_path / "run", engine="http", log=lambda *a: None)
    skipped = [rec for rec in r.body["records"] if rec.get("skipped")]
    assert len(skipped) == 1 and "project_id" in skipped[0]["skipped"]
    assert r.exit_code == 0        # a skip is not a failure


def test_dead_discovery_endpoint_degrades_to_skips(site, tmp_path):
    cfg = cfg_for(
        site, tmp_path,
        app={"base": site, "paths": ["/", "/p/{project_id}"]},
        discovery={"url": "http://127.0.0.1:1/nope", "params": {"project_id": "ids.0"}, "timeout": 0.5},
    )
    r = look(cfg, out_dir=tmp_path / "run", engine="http", log=lambda *a: None)
    assert r.body["meta"]["discovery"]["ok"] is False
    assert any(rec.get("skipped") for rec in r.body["records"])
    assert r.exit_code == 0


def test_discovery_supplies_params(site, tmp_path):
    # The site itself serves the discovery document.
    (tmp_path / "map.json").write_text(json.dumps({"entities": {"project_ids": ["about"]}}))
    cfg = cfg_for(
        site, tmp_path,
        app={"base": site, "paths": ["/{project_id}.html"]},
        discovery={"url": f"{site}/map.json", "params": {"project_id": "entities.project_ids.0"}},
    )
    r = look(cfg, out_dir=tmp_path / "run", engine="http", log=lambda *a: None)
    assert r.body["meta"]["params"] == {"project_id": "about"}
    assert r.body["records"][0]["status"] == 200


def test_baseline_round_trip_flags_a_regression(site, tmp_path, capsys):
    good = look(cfg_for(site, tmp_path), out_dir=tmp_path / "r1", engine="http", log=lambda *a: None)
    from thundera import baseline as bl

    bl.save(good.body, tmp_path / "baseline.json")

    broken = cfg_for(site, tmp_path, app={"base": site, "paths": ["/", "/about.html", "/gone.html"]})
    r2 = look(broken, out_dir=tmp_path / "r2", engine="http",
              baseline_path=tmp_path / "baseline.json", log=lambda *a: None)
    d = r2.body["baseline"]
    assert len(d["new"]) == 1 and d["new"][0]["kind"] == "net_4xx"
    assert d["fixed"] == []
    assert d["new_errors"] == 1


# ── CLI ──────────────────────────────────────────────────────────────────────
def test_cli_zero_config_look(site, tmp_path, capsys):
    code = main(["look", site, "--engine", "http", "--out", str(tmp_path / "run"), "--json", "-q"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["meta"]["base"] == site
    assert [r["surface"] for r in out["records"]] == ["home"]


def test_cli_bare_url_is_implicitly_look(site, tmp_path, capsys):
    code = main([site, "--engine", "http", "--out", str(tmp_path / "run"), "-q"])
    assert code == 0
    assert "clean" in capsys.readouterr().out


def test_cli_json_mode_keeps_stdout_pure(site, tmp_path, capsys):
    main(["look", site, "--engine", "http", "--out", str(tmp_path / "run"), "--json"])
    cap = capsys.readouterr()
    json.loads(cap.out)                       # parses => no chatter mixed in
    assert "Eye of Thundera" in cap.err       # progress went to stderr


def test_cli_init_then_check(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--name", "demo", "--base", "http://127.0.0.1:9000"]) == 0
    assert (tmp_path / "thundera.toml").exists()
    assert main(["init"]) == 2                # refuses to clobber
    capsys.readouterr()
    assert main(["check"]) == 0
    assert "demo @ http://127.0.0.1:9000" in capsys.readouterr().out


def test_cli_surfaces_json(site, tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["init", "--base", site])
    capsys.readouterr()
    main(["surfaces", "--json"])
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["key"] == "home"


def test_cli_fail_on_new_gates_on_warnings_too(site, tmp_path, capsys):
    from thundera import baseline as bl

    base = look(cfg_for(site, tmp_path), out_dir=tmp_path / "r1", engine="http", log=lambda *a: None)
    bl.save(base.body, tmp_path / "b.json")
    code = main(["look", site, "--engine", "http", "--out", str(tmp_path / "r2"),
                 "--baseline", str(tmp_path / "b.json"), "--fail-on-new", "-q"])
    assert code == 0        # nothing new


def test_cli_unknown_surface_is_a_usage_error(site, tmp_path, capsys):
    code = main(["look", site, "--surfaces", "ghost", "--engine", "http",
                 "--out", str(tmp_path / "run"), "-q"])
    assert code == 2
    assert "unknown surface" in capsys.readouterr().err


# ── retries and flake settling ───────────────────────────────────────────────
class FlakyOnceHandler(SimpleHTTPRequestHandler):
    """404s /flaky.html the first time it is asked for, then serves it.

    A deterministic stand-in for the real thing: `networkidle` never settling
    on a polling app, or a click that misses because an animation was still
    running.
    """

    seen: set = set()

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/flaky.html":
            if "hit" not in self.seen:
                self.seen.add("hit")
                self.send_error(500, "transient")
                return
            body = b"<!doctype html><title>ok</title><p>fine now</p>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()


@pytest.fixture
def flaky_site(tmp_path):
    FlakyOnceHandler.seen = set()
    srv = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(FlakyOnceHandler, directory=str(tmp_path))
    )
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _flaky_cfg(base):
    return Config.from_dict({"app": {"name": "f", "base": base, "paths": ["/flaky.html"]}})


def test_without_retries_a_transient_failure_is_a_hard_error(flaky_site, tmp_path):
    r = look(_flaky_cfg(flaky_site), out_dir=tmp_path / "r", engine="http",
             make_montage=False, log=lambda *a: None)
    assert r.exit_code == 1
    assert r.summary["errors"] == 1


def test_retries_demote_a_finding_that_does_not_reproduce(flaky_site, tmp_path):
    r = look(_flaky_cfg(flaky_site), out_dir=tmp_path / "r", engine="http",
             make_montage=False, retries=1, log=lambda *a: None)
    finds = r.body["records"][0]["findings"]
    assert len(finds) == 1
    assert finds[0]["flaky"] is True
    assert finds[0]["severity"] == "warn"          # demoted, never deleted
    assert "did not reproduce" in finds[0]["detail"]
    assert r.summary["errors"] == 0 and r.summary["warnings"] == 1
    assert r.exit_code == 0


def test_a_reproducible_error_survives_retries(site, tmp_path):
    """The retry must not launder a real failure into a warning."""
    cfg = Config.from_dict({"app": {"name": "t", "base": site, "paths": ["/gone.html"]}})
    r = look(cfg, out_dir=tmp_path / "r", engine="http", make_montage=False,
             retries=2, log=lambda *a: None)
    finds = r.body["records"][0]["findings"]
    assert finds[0]["severity"] == "error"
    assert "flaky" not in finds[0]
    assert r.exit_code == 1
