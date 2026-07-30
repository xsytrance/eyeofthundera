"""Config — the layer that makes the Eye app-agnostic.

The Inspector this is extracted from hardcoded one app's surfaces, its theme
ids, its localStorage keys and its `/api/diag/ui-map` discovery endpoint. All
four now come from a `thundera.toml`, so the engine never knows what it is
looking at.

Everything is optional. With no config at all, `Config.minimal(base)` gives you
one surface ("/") at two viewports — enough for `thundera look http://host` to
work against any URL on earth.
"""
from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

CONFIG_NAMES = ("thundera.toml", ".thundera.toml")

# Setup verbs. A step is a single-key table: { click = "#go" }. Kept small on
# purpose — this is a way to reach a state, not a scripting language. Anything
# that wants a real script wants `eval`.
STEP_KINDS = ("click", "fill", "upload", "wait_for", "eval", "goto")

_ENVVAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

# Viewports used when a config declares none. Mobile first, then desktop —
# most layout sins show up at 390px.
DEFAULT_VIEWPORTS = [
    {"label": "m390", "width": 390, "height": 844, "scale": 2, "mobile": True},
    {"label": "d1280", "width": 1280, "height": 800, "scale": 1, "mobile": False},
]

_PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class ConfigError(ValueError):
    """A thundera.toml that cannot be honoured. Message is user-facing."""


@dataclass(frozen=True)
class Viewport:
    label: str
    width: int
    height: int
    scale: float = 1
    mobile: bool = False


@dataclass(frozen=True)
class Step:
    """One precondition action, run in the page before measuring.

    `kind` is one of STEP_KINDS; `value` is a string for click/wait_for/eval/goto
    and a dict for fill/upload. `optional` mirrors the `?` prefix on pre_clicks —
    a step that is allowed not to apply on this viewport.
    """

    kind: str
    value: Any
    optional: bool = False

    def describe(self) -> str:
        v = self.value if isinstance(self.value, str) else dict(self.value)
        return f"{self.kind} {v}"


@dataclass(frozen=True)
class Profile:
    """A named variant of the same app — a theme, a locale, a logged-in state.

    `seeds` are localStorage key/values planted before first paint, which is how
    you put an app into a given state without driving its UI. When localStorage
    isn't enough — a save file to upload, a session cookie, an auth header —
    `setup`, `cookies` and `headers` carry the rest.
    """

    name: str
    seeds: dict[str, str] = field(default_factory=dict)
    # Run once per browser context, before any surface is visited. State that
    # lands in localStorage/IndexedDB or a server session persists across the
    # per-surface navigations that follow.
    setup: tuple[Step, ...] = ()
    cookies: tuple[dict, ...] = ()
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Surface:
    key: str                      # unique; used in screenshot filenames
    path: str                     # "/dashboard", may contain {param} placeholders
    group: str = "core"           # montage grouping
    routing: str | None = None    # "path" | "hash"; None inherits app routing
    settle_ms: int = 1500
    inventory: dict[str, str] = field(default_factory=dict)   # {name: css selector}
    # Selectors to click before measuring. A leading "?" marks a click as
    # optional — for elements that exist on some viewports only, like a
    # hamburger that opens the nav drawer on mobile and isn't rendered at all
    # on desktop. Everything else is required: if it doesn't land, the surface
    # was never reached and that is reported as an error.
    pre_clicks: tuple[str, ...] = ()
    profiles: tuple[str, ...] | None = None   # None = every profile
    # Steps to reach this surface's precondition, run after load+settle and
    # before pre_clicks: setup establishes the state, pre_clicks navigates to
    # the view. A failed required step is an error, for the same reason a
    # failed required pre_click is — the surface was never actually reached.
    setup: tuple[Step, ...] = ()

    def wants_profile(self, name: str) -> bool:
        return self.profiles is None or name in self.profiles


@dataclass(frozen=True)
class Discovery:
    """Where to GET a JSON document that supplies {param} values at runtime.

    Keeps entity ids out of the config: the app tells the Eye what exists.
    """

    url: str
    params: dict[str, str] = field(default_factory=dict)   # {param: path expression}
    timeout: float = 15.0


@dataclass(frozen=True)
class Config:
    name: str = "app"
    base: str = "http://127.0.0.1:8000"
    routing: str = "path"                 # "path" | "hash"
    discovery: Discovery | None = None
    params: dict[str, str] = field(default_factory=dict)    # static {param} values
    seeds: dict[str, str] = field(default_factory=dict)     # applied under every profile
    viewports: tuple[Viewport, ...] = ()
    profiles: tuple[Profile, ...] = ()
    surfaces: tuple[Surface, ...] = ()
    severity: dict[str, str] = field(default_factory=dict)  # kind -> error|warn|off
    net_ignore: tuple[str, ...] = ("favicon",)   # URL substrings whose 4xx/5xx is expected
    vision_sample: tuple[str, ...] = ()
    source: Path | None = None

    # ── construction ─────────────────────────────────────────────────────────
    @classmethod
    def minimal(cls, base: str, name: str = "app") -> "Config":
        """Zero-config: the front page, both viewports, one unnamed profile."""
        return cls(
            name=name,
            base=base.rstrip("/"),
            viewports=tuple(Viewport(**v) for v in DEFAULT_VIEWPORTS),
            profiles=(Profile("default"),),
            surfaces=(Surface(key="home", path="/"),),
        )

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        p = Path(path)
        if not p.is_file():
            raise ConfigError(f"no config at {p}")
        try:
            raw = tomllib.loads(p.read_text())
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"{p}: invalid TOML — {e}") from e
        return cls.from_dict(raw, source=p)

    @classmethod
    def discover(cls, start: str | Path = ".") -> "Config | None":
        """Walk up from `start` looking for a thundera.toml. None if there is none."""
        here = Path(start).resolve()
        for d in (here, *here.parents):
            for nm in CONFIG_NAMES:
                if (d / nm).is_file():
                    return cls.load(d / nm)
        return None

    @classmethod
    def from_dict(cls, raw: dict[str, Any], source: Path | None = None) -> "Config":
        app = raw.get("app", {})
        routing = app.get("routing", "path")
        if routing not in ("path", "hash"):
            raise ConfigError(f"app.routing must be 'path' or 'hash', got {routing!r}")

        viewports = tuple(
            Viewport(
                label=v.get("label") or f"w{v['width']}",
                width=int(v["width"]),
                height=int(v.get("height", 800)),
                scale=float(v.get("scale", 1)),
                mobile=bool(v.get("mobile", False)),
            )
            for v in raw.get("viewports", [])
        ) or tuple(Viewport(**v) for v in DEFAULT_VIEWPORTS)

        base_dir = source.parent if source is not None else None
        profiles = tuple(
            Profile(
                name=p["name"],
                seeds={
                    k: expand_env(str(v), f"profile {p['name']!r} seed {k!r}")
                    for k, v in (p.get("seeds") or {}).items()
                },
                setup=_read_steps(p.get("setup"), f"profile {p.get('name', '?')!r}", base_dir),
                cookies=_read_cookies(p.get("cookies"), f"profile {p.get('name', '?')!r}"),
                headers={
                    str(k): expand_env(str(v), f"profile {p.get('name', '?')!r} header {k!r}")
                    for k, v in (p.get("headers") or {}).items()
                },
            )
            for p in raw.get("profiles", [])
        ) or (Profile("default"),)

        surfaces = _read_surfaces(raw, routing, base_dir)
        if not surfaces:
            raise ConfigError(
                "config declares no surfaces — add [[surfaces]] entries, or "
                "'paths = [\"/\", \"/about\"]' under [app]"
            )
        seen: set[str] = set()
        for s in surfaces:
            if s.key in seen:
                raise ConfigError(f"duplicate surface key {s.key!r}")
            seen.add(s.key)

        disc = None
        if "discovery" in raw:
            d = raw["discovery"]
            if "url" not in d:
                raise ConfigError("[discovery] needs a url")
            disc = Discovery(
                url=d["url"],
                params={k: str(v) for k, v in (d.get("params") or {}).items()},
                timeout=float(d.get("timeout", 15.0)),
            )

        severity = {k: str(v) for k, v in (raw.get("severity") or {}).items()}
        from .checks import DEFAULT_NET_IGNORE, KINDS

        for kind in severity:
            if kind not in KINDS:
                raise ConfigError(
                    f"severity.{kind} is not a known check (known: {', '.join(KINDS)})"
                )
        for kind, sev in severity.items():
            if sev not in ("error", "warn", "off"):
                raise ConfigError(
                    f"severity.{kind} must be 'error', 'warn' or 'off', got {sev!r}"
                )

        known_profiles = {p.name for p in profiles}
        for s in surfaces:
            for want in s.profiles or ():
                if want not in known_profiles:
                    raise ConfigError(
                        f"surface {s.key!r} wants profile {want!r}, "
                        f"which is not declared (have: {sorted(known_profiles)})"
                    )

        vs = tuple(raw.get("vision", {}).get("sample", []))
        for k in vs:
            if k not in seen:
                raise ConfigError(f"vision.sample names unknown surface {k!r}")

        return cls(
            name=app.get("name", "app"),
            base=str(app.get("base", "http://127.0.0.1:8000")).rstrip("/"),
            routing=routing,
            discovery=disc,
            params={
                k: expand_env(str(v), f"param {k!r}")
                for k, v in (raw.get("params") or {}).items()
            },
            seeds={
                k: expand_env(str(v), f"seed {k!r}")
                for k, v in (raw.get("seeds") or {}).items()
            },
            viewports=viewports,
            profiles=profiles,
            surfaces=surfaces,
            severity=severity,
            net_ignore=tuple(raw.get("network", {}).get("ignore", DEFAULT_NET_IGNORE)),
            vision_sample=vs,
            source=source,
        )

    # ── selection (CLI filters) ──────────────────────────────────────────────
    def select(
        self,
        surfaces: list[str] | None = None,
        profiles: list[str] | None = None,
        viewports: list[str] | None = None,
    ) -> "Config":
        """Return a narrowed copy. Unknown names raise, so typos fail loudly."""
        cfg = self
        if surfaces:
            known = {s.key for s in self.surfaces}
            _reject_unknown(surfaces, known, "surface")
            cfg = replace(cfg, surfaces=tuple(s for s in cfg.surfaces if s.key in set(surfaces)))
        if profiles:
            known = {p.name for p in self.profiles}
            _reject_unknown(profiles, known, "profile")
            cfg = replace(cfg, profiles=tuple(p for p in cfg.profiles if p.name in set(profiles)))
        if viewports:
            known = {v.label for v in self.viewports}
            _reject_unknown(viewports, known, "viewport")
            cfg = replace(cfg, viewports=tuple(v for v in cfg.viewports if v.label in set(viewports)))
        return cfg

    def with_base(self, base: str | None) -> "Config":
        return self if not base else replace(self, base=base.rstrip("/"))

    def url_for(self, surface: Surface, resolved_path: str) -> str:
        routing = surface.routing or self.routing
        return f"{self.base}/#{resolved_path}" if routing == "hash" else f"{self.base}{resolved_path}"

    @property
    def page_view_count(self) -> int:
        return sum(
            1
            for s in self.surfaces
            for p in self.profiles
            if s.wants_profile(p.name)
            for _ in self.viewports
        )


def expand_env(value: str, where: str) -> str:
    """Substitute ${VAR} from the environment.

    Exists so a token never has to be committed to a thundera.toml. An unset
    variable is a hard error: silently sending an empty Authorization header
    would produce a sweep of 401s reported as the app's fault.
    """
    missing: list[str] = []

    def sub(m: re.Match) -> str:
        val = os.environ.get(m.group(1))
        if val is None:
            missing.append(m.group(1))
            return ""
        return val

    out = _ENVVAR.sub(sub, value)
    if missing:
        raise ConfigError(
            f"{where}: environment variable(s) {', '.join('${' + m + '}' for m in missing)} "
            f"are not set"
        )
    return out


def _read_steps(raw: Any, where: str, base_dir: Path | None) -> tuple[Step, ...]:
    """Parse a `setup = [...]` list. Each entry is a single-key table."""
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ConfigError(f"{where}: setup must be a list of steps")
    steps: list[Step] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict) or len(entry) != 1:
            raise ConfigError(
                f"{where}: step {i + 1} must be a table with exactly one key "
                f"(one of {', '.join(STEP_KINDS)})"
            )
        [(kind, value)] = entry.items()
        if kind not in STEP_KINDS:
            raise ConfigError(
                f"{where}: step {i + 1} has unknown action {kind!r} "
                f"(known: {', '.join(STEP_KINDS)})"
            )
        optional = False
        if kind in ("click", "wait_for", "eval", "goto"):
            if not isinstance(value, str):
                raise ConfigError(f"{where}: step {i + 1} '{kind}' takes a string")
            if kind in ("click", "wait_for") and value.startswith("?"):
                optional, value = True, value[1:]
        elif kind == "fill":
            if not isinstance(value, dict) or "selector" not in value or "text" not in value:
                raise ConfigError(
                    f"{where}: step {i + 1} 'fill' needs {{ selector = ..., text = ... }}"
                )
            value = {"selector": str(value["selector"]),
                     "text": expand_env(str(value["text"]), f"{where} step {i + 1}")}
        elif kind == "upload":
            if not isinstance(value, dict) or "selector" not in value or "path" not in value:
                raise ConfigError(
                    f"{where}: step {i + 1} 'upload' needs {{ selector = ..., path = ... }}"
                )
            p = Path(str(value["path"]))
            if not p.is_absolute() and base_dir is not None:
                p = base_dir / p
            # Fail now, loudly, rather than mid-sweep: a fixture that isn't
            # there means every surface behind it would be measured in the
            # wrong state.
            if not p.is_file():
                raise ConfigError(
                    f"{where}: step {i + 1} 'upload' file not found: {p}"
                )
            value = {"selector": str(value["selector"]), "path": str(p)}
        steps.append(Step(kind=kind, value=value, optional=optional))
    return tuple(steps)


def _read_cookies(raw: Any, where: str) -> tuple[dict, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ConfigError(f"{where}: cookies must be a list of tables")
    out: list[dict] = []
    for i, c in enumerate(raw):
        if not isinstance(c, dict) or "name" not in c or "value" not in c:
            raise ConfigError(f"{where}: cookie {i + 1} needs a name and a value")
        cookie = {k: v for k, v in c.items()}
        cookie["name"] = str(cookie["name"])
        cookie["value"] = expand_env(str(cookie["value"]), f"{where} cookie {i + 1}")
        out.append(cookie)
    return tuple(out)


def _reject_unknown(want: list[str], known: set[str], noun: str) -> None:
    bad = [w for w in want if w not in known]
    if bad:
        raise ConfigError(f"unknown {noun}(s): {', '.join(bad)} (known: {', '.join(sorted(known))})")


def _read_surfaces(
    raw: dict[str, Any], routing: str, base_dir: Path | None = None
) -> tuple[Surface, ...]:
    out: list[Surface] = []
    # Shorthand: app.paths = ["/", "/about"] — keys derived from the path.
    for path in raw.get("app", {}).get("paths", []):
        out.append(Surface(key=_key_for(path), path=path))
    for s in raw.get("surfaces", []):
        if "path" not in s:
            raise ConfigError(f"surface {s.get('key', '?')!r} has no path")
        r = s.get("routing")
        if r is not None and r not in ("path", "hash"):
            raise ConfigError(f"surface {s.get('key')!r}: routing must be 'path' or 'hash'")
        profiles = s.get("profiles")
        out.append(
            Surface(
                key=s.get("key") or _key_for(s["path"]),
                path=s["path"],
                group=s.get("group", "core"),
                routing=r,
                settle_ms=int(s.get("settle_ms", 1500)),
                inventory={k: str(v) for k, v in (s.get("inventory") or {}).items()},
                pre_clicks=tuple(s.get("pre_clicks") or ()),
                profiles=tuple(profiles) if profiles is not None else None,
                setup=_read_steps(
                    s.get("setup"), f"surface {s.get('key') or s['path']!r}", base_dir
                ),
            )
        )
    return tuple(out)


def _key_for(path: str) -> str:
    """'/project/{project_id}/inventory' -> 'project-inventory'; '/' -> 'home'."""
    bits = [b for b in _PLACEHOLDER.sub("", path).strip("/").split("/") if b]
    return "-".join(bits).replace(".", "-") or "home"


# ── {param} resolution ───────────────────────────────────────────────────────
def placeholders(path: str) -> set[str]:
    return set(_PLACEHOLDER.findall(path))


def lookup(doc: Any, expr: str) -> Any:
    """Read a dotted path out of a JSON document. Numeric segments index lists.

    'entities.project_ids.0' → doc["entities"]["project_ids"][0].
    Returns None if any hop is missing — a surface that cannot be located is
    skipped with a note, never an error.
    """
    cur = doc
    for seg in expr.split("."):
        if cur is None:
            return None
        if isinstance(cur, list):
            if not seg.lstrip("-").isdigit():
                return None
            idx = int(seg)
            cur = cur[idx] if -len(cur) <= idx < len(cur) else None
        elif isinstance(cur, dict):
            cur = cur.get(seg)
        else:
            return None
    return cur


def resolve_params(cfg: Config, doc: Any) -> tuple[dict[str, str], dict[str, str]]:
    """Resolve every declared {param} to a concrete value.

    Static `[params]` win over discovery (they are an explicit override). A
    discovery expression may itself reference an already-resolved param —
    `entities.character_ids.{project_id}.0` — so resolution iterates until it
    stops making progress, which also breaks any circular reference.

    Returns (resolved, unresolved_reasons).
    """
    resolved: dict[str, str] = dict(cfg.params)
    wanted = dict((cfg.discovery.params if cfg.discovery else {}))
    reasons: dict[str, str] = {}

    pending = {k: v for k, v in wanted.items() if k not in resolved}
    while pending:
        progressed = False
        for name, expr in list(pending.items()):
            needs = placeholders(expr)
            if not needs <= set(resolved):
                continue                      # depends on a param we do not have yet
            concrete = _PLACEHOLDER.sub(lambda m: resolved[m.group(1)], expr)
            val = lookup(doc, concrete)
            del pending[name]
            progressed = True
            if val is None or isinstance(val, (dict, list)):
                reasons[name] = f"discovery has nothing at '{concrete}'"
            else:
                resolved[name] = str(val)
        if not progressed:
            for name, expr in pending.items():
                missing = sorted(placeholders(expr) - set(resolved))
                reasons[name] = f"needs unresolved param(s): {', '.join(missing)}"
            break
    return resolved, reasons


def resolve_path(surface: Surface, params: dict[str, str]) -> tuple[str | None, str]:
    """Fill a surface's placeholders. (None, why) when it cannot be satisfied."""
    missing = sorted(placeholders(surface.path) - set(params))
    if missing:
        return None, f"no value for {', '.join('{' + m + '}' for m in missing)}"
    return _PLACEHOLDER.sub(lambda m: params[m.group(1)], surface.path), ""
