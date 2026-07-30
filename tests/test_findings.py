"""checks.analyze, the report contract, and baseline diffing."""
from thundera import baseline as baseline_mod
from thundera.checks import analyze
from thundera.report import build, exit_code, finding_id, summarize

RAW = {
    "brokenImgs": ["/missing.png"],
    "docOverflow": 12,
    "tapTargets": [{"sel": "button.x", "w": 20, "h": 20, "label": "go"}],
    "spacing": [{"sel": "ul.y", "gaps": [8, 10], "spread": 2}],
}


def test_severities_and_kinds():
    f = analyze(RAW, [], [], [], mobile=True)
    kinds = {x["kind"]: x["severity"] for x in f}
    assert kinds["broken_img"] == "error"
    assert kinds["doc_overflow"] == "error"
    assert kinds["tap_target"] == "warn"


def test_tap_targets_are_mobile_only():
    desktop = analyze(RAW, [], [], [], mobile=False)
    assert not any(x["kind"] == "tap_target" for x in desktop)
    assert any(x["kind"] == "tap_target" for x in analyze(RAW, [], [], [], mobile=True))


def test_severity_off_suppresses_a_check():
    f = analyze(RAW, [], [], [], mobile=True, severity={"spacing": "off"})
    assert not any(x["kind"] == "spacing" for x in f)


def test_severity_can_be_promoted_to_error():
    f = analyze(RAW, [], [], [], mobile=True, severity={"spacing": "error"})
    assert [x["severity"] for x in f if x["kind"] == "spacing"] == ["error"]


def test_console_warnings_are_not_errors():
    f = analyze({}, ["warning: deprecated", "error: boom"], [], [], mobile=False)
    assert [x["detail"] for x in f] == ["error: boom"]


def test_net_ignore_filters_expected_failures():
    f = analyze({}, [], ["404 http://x/favicon.ico", "500 http://x/api/real"], [], mobile=False)
    assert len(f) == 1 and "api/real" in f[0]["detail"]

    f2 = analyze({}, [], ["500 http://x/api/optional"], [], mobile=False,
                 net_ignore=("favicon", "/api/optional"))
    assert f2 == []


def test_every_finding_carries_an_anchor():
    for f in analyze(RAW, ["error: x"], [], [], mobile=True):
        assert f["anchor"]


# ── report contract ──────────────────────────────────────────────────────────
def rec(surface, findings, **kw):
    return {"surface": surface, "profile": "default", "viewport": "d1280",
            "findings": findings, **kw}


ERR = {"kind": "broken_img", "severity": "error", "detail": "/a.png", "anchor": "/a.png"}
WARN = {"kind": "spacing", "severity": "warn", "detail": "ul — gaps [8, 10]", "anchor": "ul"}


def test_summarize_counts_views_and_findings():
    s = summarize([rec("a", [ERR, WARN]), rec("b", [WARN]), rec("c", []),
                   rec("d", [], skipped="no param")])
    assert s == {"page_views": 4, "clean": 1, "with_warnings": 1, "with_errors": 1,
                 "skipped": 1, "errors": 1, "warnings": 2, "unverified": 0}


def test_summarize_totals_what_could_not_be_judged():
    """A clean run that checked nothing must not read as a clean run."""
    s = summarize([
        rec("a", [], unverified={"contrast": 3}),
        rec("b", [], unverified={"contrast": 1}),
        rec("c", []),
    ])
    assert s["unverified"] == 4
    assert s["clean"] == 3 and s["errors"] == 0     # abstentions are not failures


def test_exit_code_gates_on_errors_only_unless_asked():
    warn_only = build([rec("a", [WARN])], {})
    assert exit_code(warn_only) == 0
    assert exit_code(warn_only, warn_as_error=True) == 1
    assert exit_code(build([rec("a", [ERR])], {})) == 1


def test_schema_version_is_declared():
    body = build([rec("a", [])], {"app": "x"})
    assert body["schema_version"] == 1 and body["tool"] == "eye-of-thundera"


def test_finding_id_ignores_jittering_detail():
    a = finding_id(rec("home", []), {"kind": "off_center", "anchor": "div.hero", "detail": "Δ4.1px"})
    b = finding_id(rec("home", []), {"kind": "off_center", "anchor": "div.hero", "detail": "Δ4.3px"})
    assert a == b


def test_finding_id_separates_viewports():
    r1 = {"surface": "home", "profile": "d", "viewport": "m390"}
    r2 = {"surface": "home", "profile": "d", "viewport": "d1280"}
    f = {"kind": "tap_target", "anchor": "button"}
    assert finding_id(r1, f) != finding_id(r2, f)


# ── baseline ─────────────────────────────────────────────────────────────────
def test_compare_reports_new_fixed_and_unchanged():
    before = build([rec("home", [WARN, ERR])], {})
    after = build([rec("home", [WARN, {"kind": "js_error", "severity": "error",
                                       "detail": "TypeError", "anchor": "TypeError"}])], {})
    d = baseline_mod.compare(after, before, "b.json")
    assert [f["kind"] for f in d["new"]] == ["js_error"]
    assert [f["kind"] for f in d["fixed"]] == ["broken_img"]
    assert d["unchanged"] == 1
    assert d["new_errors"] == 1


def test_compare_is_clean_when_nothing_moved():
    body = build([rec("home", [WARN])], {})
    d = baseline_mod.compare(body, body, "b.json")
    assert d["new"] == [] and d["fixed"] == [] and d["unchanged"] == 1


def test_baseline_rejects_a_file_that_is_not_findings(tmp_path):
    p = tmp_path / "nope.json"
    p.write_text('{"hello": 1}')
    try:
        baseline_mod.load(p)
    except ValueError as e:
        assert "not an Eye findings file" in str(e)
    else:
        raise AssertionError("should have rejected")
