import pytest

from thundera.config import (
    Config,
    ConfigError,
    lookup,
    placeholders,
    resolve_params,
    resolve_path,
)


def cfg(**over):
    raw = {"app": {"name": "t", "base": "http://x", "paths": ["/"]}}
    raw.update(over)
    return Config.from_dict(raw)


# ── shape ────────────────────────────────────────────────────────────────────
def test_minimal_has_one_surface_and_default_viewports():
    c = Config.minimal("http://127.0.0.1:9000/")
    assert c.base == "http://127.0.0.1:9000"       # trailing slash stripped
    assert [s.key for s in c.surfaces] == ["home"]
    assert [v.label for v in c.viewports] == ["m390", "d1280"]


def test_paths_shorthand_derives_keys():
    c = cfg(app={"base": "http://x", "paths": ["/", "/about", "/project/{project_id}/inventory"]})
    assert [s.key for s in c.surfaces] == ["home", "about", "project-inventory"]


def test_hash_routing_builds_hash_urls():
    c = cfg(app={"base": "http://x", "routing": "hash", "paths": ["/dash"]})
    assert c.url_for(c.surfaces[0], "/dash") == "http://x/#/dash"


def test_surface_can_override_routing():
    c = Config.from_dict({
        "app": {"base": "http://x", "routing": "hash"},
        "surfaces": [{"key": "spa", "path": "/a"}, {"key": "file", "path": "/b.html", "routing": "path"}],
    })
    assert c.url_for(c.surfaces[0], "/a") == "http://x/#/a"
    assert c.url_for(c.surfaces[1], "/b.html") == "http://x/b.html"


def test_page_view_count_respects_per_surface_profiles():
    c = Config.from_dict({
        "app": {"base": "http://x"},
        "profiles": [{"name": "light"}, {"name": "dark"}],
        "viewports": [{"label": "d", "width": 1280}],
        "surfaces": [{"key": "a", "path": "/a"}, {"key": "b", "path": "/b", "profiles": ["light"]}],
    })
    assert c.page_view_count == 3        # a×2 profiles + b×1


# ── validation ───────────────────────────────────────────────────────────────
def test_no_surfaces_is_an_error():
    with pytest.raises(ConfigError, match="no surfaces"):
        Config.from_dict({"app": {"base": "http://x"}})


def test_duplicate_surface_key_rejected():
    with pytest.raises(ConfigError, match="duplicate surface key"):
        Config.from_dict({"app": {"base": "http://x"},
                          "surfaces": [{"key": "a", "path": "/1"}, {"key": "a", "path": "/2"}]})


def test_bad_routing_rejected():
    with pytest.raises(ConfigError, match="routing"):
        Config.from_dict({"app": {"base": "http://x", "routing": "sideways", "paths": ["/"]}})


def test_unknown_severity_kind_rejected():
    with pytest.raises(ConfigError, match="not a known check"):
        cfg(severity={"nonsense": "off"})


def test_bad_severity_value_rejected():
    with pytest.raises(ConfigError, match="must be"):
        cfg(severity={"spacing": "maybe"})


def test_surface_referencing_undeclared_profile_rejected():
    with pytest.raises(ConfigError, match="not declared"):
        Config.from_dict({"app": {"base": "http://x"},
                          "profiles": [{"name": "light"}],
                          "surfaces": [{"key": "a", "path": "/a", "profiles": ["dark"]}]})


def test_vision_sample_must_name_real_surfaces():
    with pytest.raises(ConfigError, match="unknown surface"):
        cfg(vision={"sample": ["ghost"]})


def test_select_rejects_typos():
    c = cfg()
    with pytest.raises(ConfigError, match="unknown surface"):
        c.select(surfaces=["hoem"])


def test_select_narrows():
    c = Config.from_dict({"app": {"base": "http://x", "paths": ["/a", "/b"]}})
    assert [s.key for s in c.select(surfaces=["a"]).surfaces] == ["a"]


# ── {param} resolution ───────────────────────────────────────────────────────
def test_lookup_walks_dicts_and_list_indices():
    doc = {"entities": {"ids": [7, 8]}}
    assert lookup(doc, "entities.ids.0") == 7
    assert lookup(doc, "entities.ids.5") is None
    assert lookup(doc, "entities.missing.0") is None
    assert lookup(doc, "entities.ids.notanindex") is None


def test_placeholders_extracted():
    assert placeholders("/p/{project_id}/c/{character_id}") == {"project_id", "character_id"}


def test_static_params_beat_discovery():
    c = cfg(params={"project_id": "99"},
            discovery={"url": "http://x/map", "params": {"project_id": "ids.0"}})
    resolved, unresolved = resolve_params(c, {"ids": [1]})
    assert resolved["project_id"] == "99"
    assert not unresolved


def test_nested_param_depends_on_earlier_one():
    c = cfg(discovery={"url": "http://x/map", "params": {
        "project_id": "entities.project_ids.0",
        "character_id": "entities.character_ids.{project_id}.0",
    }})
    doc = {"entities": {"project_ids": [12], "character_ids": {"12": [34]}}}
    resolved, unresolved = resolve_params(c, doc)
    assert resolved == {"project_id": "12", "character_id": "34"}
    assert not unresolved


def test_unresolvable_param_reports_why_and_does_not_raise():
    c = cfg(discovery={"url": "http://x/map", "params": {"project_id": "entities.project_ids.0"}})
    resolved, unresolved = resolve_params(c, {"entities": {"project_ids": []}})
    assert "project_id" not in resolved
    assert "nothing at" in unresolved["project_id"]


def test_circular_param_dependency_terminates():
    c = cfg(discovery={"url": "http://x/map", "params": {"a": "x.{b}", "b": "y.{a}"}})
    resolved, unresolved = resolve_params(c, {})
    assert set(unresolved) == {"a", "b"}
    assert "unresolved param" in unresolved["a"]


def test_resolve_path_fills_and_reports():
    from thundera.config import Surface

    s = Surface(key="p", path="/project/{project_id}")
    assert resolve_path(s, {"project_id": "5"}) == ("/project/5", "")
    path, why = resolve_path(s, {})
    assert path is None and "{project_id}" in why
