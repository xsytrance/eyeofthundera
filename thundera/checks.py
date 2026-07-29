"""Deterministic geometry + accessibility checks, run inside the page.

One page.evaluate() collects raw measurements; Python turns them into findings
with severities. Thresholds are deliberately conservative — a finding should
mean "a human would call this sloppy", not "pixel trivia".

The collector below is app-agnostic by construction: it asks the DOM about
itself and knows nothing about any particular product. It is carried over
unchanged from the Vera Inspector, where it was tuned against six themes × two
viewports of a real app; resist the urge to loosen a threshold to silence one
noisy surface — set `severity.<kind> = "off"` in that project's config instead.
"""
from __future__ import annotations

# Returns {brokenImgs, docOverflow, clippedText, rowMisalign, offCenter,
#          tapTargets, contrast, spacing, inventory}
COLLECT_JS = r"""
(invSelectors) => {
  const vis = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    const s = getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden' && +s.opacity > 0.05;
  };
  const path = (el) => {
    const bits = [];
    for (let n = el; n && n !== document.body && bits.length < 4; n = n.parentElement) {
      let b = n.tagName.toLowerCase();
      if (n.id) { bits.unshift(b + '#' + n.id); break; }
      const cls = [...n.classList].slice(0, 2).join('.');
      if (cls) b += '.' + cls;
      bits.unshift(b);
    }
    return bits.join(' > ');
  };
  const round = (x) => Math.round(x * 10) / 10;

  // 1. broken imgs
  const brokenImgs = [...document.images]
    .filter(i => i.complete && i.naturalWidth === 0 && vis(i))
    .map(i => i.currentSrc || i.src);

  // 2. document overflow
  const de = document.documentElement;
  const docOverflow = de.scrollWidth > de.clientWidth + 1 ? de.scrollWidth - de.clientWidth : 0;

  // 3. clipped text
  const clippedText = [];
  for (const el of document.querySelectorAll('body *')) {
    if (clippedText.length >= 20) break;
    if (!vis(el) || !el.childNodes.length) continue;
    const hasText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 2);
    if (!hasText) continue;
    const s = getComputedStyle(el);
    if (s.textOverflow === 'ellipsis' || s.overflowX === 'auto' || s.overflowX === 'scroll') continue; // intentional
    if ((s.overflow === 'hidden' || s.overflowX === 'hidden') && el.scrollWidth > el.clientWidth + 2) {
      clippedText.push({ sel: path(el), by: el.scrollWidth - el.clientWidth,
                         text: el.textContent.trim().slice(0, 40) });
    }
  }

  // 4. row alignment: visible interactive/card children sharing a parent + row band
  const rowMisalign = [];
  const parents = new Set();
  for (const el of document.querySelectorAll('button, a[class], [class*="card"], [class*="chip"], li'))
    if (vis(el) && el.parentElement) parents.add(el.parentElement);
  for (const par of parents) {
    if (rowMisalign.length >= 12) break;
    const kids = [...par.children].filter(vis).map(k => ({ k, r: k.getBoundingClientRect() }));
    if (kids.length < 2) continue;
    // bucket into rows: overlap vertically by > half height
    const rows = [];
    for (const it of kids) {
      const row = rows.find(rw => Math.min(rw.bot, it.r.bottom) - Math.max(rw.top, it.r.top) > it.r.height * 0.5);
      if (row) { row.items.push(it); row.top = Math.min(row.top, it.r.top); row.bot = Math.max(row.bot, it.r.bottom); }
      else rows.push({ top: it.r.top, bot: it.r.bottom, items: [it] });
    }
    for (const rw of rows) {
      if (rw.items.length < 2) continue;
      const sameTag = new Set(rw.items.map(i => i.k.tagName)).size === 1;
      if (!sameTag) continue;
      const tops = rw.items.map(i => i.r.top);
      const spread = Math.max(...tops) - Math.min(...tops);
      if (spread > 2 && spread < rw.items[0].r.height) {
        rowMisalign.push({ sel: path(par), kind: rw.items[0].k.tagName.toLowerCase(),
                           n: rw.items.length, spreadPx: round(spread) });
      }
    }
  }

  // 5. centering: only elements that are ALONE in their centering context —
  // an icon flex-centered beside its text sibling is correctly off-center.
  const offCenter = [];
  for (const el of document.querySelectorAll('body *')) {
    if (offCenter.length >= 12) break;
    if (!vis(el)) continue;
    if (el.tagName === 'svg' || el.tagName === 'SVG' || el.tagName === 'IMG') continue;
    const s = getComputedStyle(el);
    const par = el.parentElement;
    if (!par) continue;
    const siblings = [...par.children].filter(c => c !== el && vis(c));
    if (siblings.length) continue;                       // shares the row — not a centering claim
    const hasLooseText = [...par.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (hasLooseText) continue;
    const ps = getComputedStyle(par);
    const flexCentered = ps.display.includes('flex') && ps.justifyContent === 'center'
      && ps.flexDirection.startsWith('row');
    const marginAuto = s.marginLeft === 'auto' && s.marginRight === 'auto';
    if (!flexCentered && !marginAuto) continue;
    const r = el.getBoundingClientRect(), pr = par.getBoundingClientRect();
    if (pr.width - r.width < 24) continue;
    const gl = r.left - pr.left, gr = pr.right - r.right;
    if (Math.abs(gl - gr) > 4) {
      offCenter.push({ sel: path(el), left: round(gl), right: round(gr), delta: round(Math.abs(gl - gr)) });
    }
  }

  // 6. tap targets (meaningful at mobile). 32px floor — conventional 34-38px
  // icon buttons pass; genuinely cramped controls don't.
  const tapTargets = [];
  for (const el of document.querySelectorAll('a, button, [role="button"], input, select, textarea')) {
    if (tapTargets.length >= 15) break;
    if (!vis(el)) continue;
    if (el.tagName === 'INPUT' && ['range', 'checkbox', 'radio'].includes(el.type)) continue; // thumb/track padding extends the real target
    const r = el.getBoundingClientRect();
    if ((r.width < 32 || r.height < 32) && r.width > 2 && r.height > 2) {
      if (el.tagName === 'A' && getComputedStyle(el).display === 'inline') continue; // prose links
      if (r.width >= 100 && r.width >= r.height * 3) continue;                       // wide banner-style links
      tapTargets.push({ sel: path(el), w: round(r.width), h: round(r.height),
                        label: (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 24) });
    }
  }

  // 7. WCAG contrast for visible text (solid backgrounds only — gradients skipped)
  const parseRGB = (str) => {
    const m = str.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);
    return m ? { r: +m[1], g: +m[2], b: +m[3], a: m[4] === undefined ? 1 : +m[4] } : null;
  };
  const lum = (c) => {
    const f = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const contrast = [];
  const seenSel = new Set();
  for (const el of document.querySelectorAll('body *')) {
    if (contrast.length >= 15) break;
    if (!vis(el)) continue;
    const hasText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 2);
    if (!hasText) continue;
    const s = getComputedStyle(el);
    const fg = parseRGB(s.color);
    if (!fg || fg.a < 0.5) continue;
    // Effective background: composite the real element stack under the text
    // (elementsFromPoint sees overlay siblings and translucent sticky bars
    // that an ancestor walk misses). Alpha-blend top-down until opaque;
    // bail on gradients/images (unknown pixels — skip, don't guess).
    const r0 = el.getBoundingClientRect();
    const cx = r0.left + Math.min(40, r0.width / 2);
    const cy = r0.top + r0.height / 2;
    const inViewport = cx >= 1 && cx <= innerWidth - 1 && cy >= 1 && cy <= innerHeight - 1;
    let bg = null, gradient = false;
    const layers = [];
    // The element's OWN background is the first paint layer under its text
    // (a gradient CTA button must be judged by its gradient, not the page
    // behind it — gradients are skipped, not guessed).
    if (s.backgroundImage !== 'none') { gradient = true; }
    else {
      const own = parseRGB(s.backgroundColor);
      if (own && own.a > 0.02) layers.push(own);
    }
    const paintedPseudo = (n) => ['::before', '::after'].some(p => {
      const ps2 = getComputedStyle(n, p);
      return ps2.content !== 'none' &&
             (ps2.backgroundImage !== 'none' || (parseRGB(ps2.backgroundColor) || {a: 0}).a > 0.02);
    });
    if (!gradient && !(layers[0] && layers[0].a > 0.98)) {
      // In-viewport: composite the true hit-test stack (sees overlay siblings
      // and sticky bars). Off-viewport elementsFromPoint is meaningless, so
      // fall back to the ancestor chain — correct for normal document flow.
      const chain = inViewport
        ? document.elementsFromPoint(cx, cy)
        : (() => { const a = []; for (let n = el.parentElement; n; n = n.parentElement) a.push(n); return a; })();
      for (const n of chain) {
        if (n === el || el.contains(n)) continue;   // self / children already handled
        const ns = getComputedStyle(n);
        const op = +ns.opacity;
        if (op < 0.1) continue;   // invisible layers (closed scrims/drawers) still hit-test
        // A painted ::before/::after may cover this box (banner art, tint
        // washes, fade scrims) — pixels unknown, so skip rather than guess.
        if (ns.backgroundImage !== 'none' || paintedPseudo(n)) { gradient = true; break; }
        const c = parseRGB(ns.backgroundColor);
        if (c && c.a * op > 0.02) {
          layers.push({ r: c.r, g: c.g, b: c.b, a: c.a * op });
          if (c.a * op > 0.98) break;
        }
        if (n === document.documentElement) break;
      }
    }
    if (!gradient && layers.length) {
      // blend bottom-up: start from the deepest (most opaque) layer
      let acc = layers[layers.length - 1];
      for (let i = layers.length - 2; i >= 0; i--) {
        const t = layers[i], a = t.a;
        acc = { r: t.r * a + acc.r * (1 - a), g: t.g * a + acc.g * (1 - a),
                b: t.b * a + acc.b * (1 - a), a: 1 };
      }
      bg = acc;
    }
    if (gradient || !bg) continue;
    const L1 = lum(fg), L2 = lum(bg);
    const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const px = parseFloat(s.fontSize);
    const big = px >= 24 || (px >= 18.66 && +s.fontWeight >= 700);
    const need = big ? 3 : 4.5;
    if (ratio < need) {
      const sel = path(el);
      if (seenSel.has(sel)) continue;
      seenSel.add(sel);
      contrast.push({ sel, ratio: round(ratio), need, px: round(px),
                      fg: s.color, bg: `rgb(${Math.round(bg.r)}, ${Math.round(bg.g)}, ${Math.round(bg.b)})`,
                      text: el.textContent.trim().slice(0, 32) });
    }
  }

  // 8. spacing rhythm: vertical stacks of ≥3 same-tag siblings with near-miss gaps
  const spacing = [];
  for (const par of parents) {
    if (spacing.length >= 8) break;
    const kids = [...par.children].filter(vis);
    if (kids.length < 3 || new Set(kids.map(k => k.tagName)).size !== 1) continue;
    const rects = kids.map(k => k.getBoundingClientRect()).sort((a, b) => a.top - b.top);
    const gaps = [];
    for (let i = 1; i < rects.length; i++) {
      const g = rects[i].top - rects[i - 1].bottom;
      if (g >= -1 && g < 200) gaps.push(Math.round(g));
    }
    if (gaps.length < 2) continue;
    const spreadG = Math.max(...gaps) - Math.min(...gaps);
    if (spreadG >= 1 && spreadG <= 3) {
      spacing.push({ sel: path(par), gaps, spread: spreadG });
    }
  }

  // 9. element inventory (named boxes for the size ledger)
  const inventory = {};
  for (const [name, sel] of Object.entries(invSelectors || {})) {
    const el = document.querySelector(sel);
    if (el && vis(el)) {
      const r = el.getBoundingClientRect();
      inventory[name] = { x: round(r.x), y: round(r.y), w: round(r.width), h: round(r.height),
                          font: getComputedStyle(el).fontSize };
    }
  }

  return { brokenImgs, docOverflow, clippedText, rowMisalign, offCenter, tapTargets, contrast, spacing, inventory };
}
"""

# Default severity per finding kind. "error" fails a run, "warn" is reported
# only, "off" is not emitted at all. Projects override via [severity] in
# thundera.toml — the way to quiet a check you have decided you don't care
# about, rather than editing thresholds.
DEFAULT_SEVERITY: dict[str, str] = {
    "broken_img": "error",
    "console_error": "error",
    "net_4xx": "error",
    "js_error": "error",
    "doc_overflow": "error",
    # A pre_click that did not land means the surface was never reached — what
    # got measured is some other page wearing this surface's name. That is
    # worse than a broken image, so it is an error by default: a silent pass
    # here would be the tool lying about what it looked at.
    "pre_click_failed": "error",
    # Contrast reports composited fg/bg pairs for the polish worklist; it stays
    # warn by default until the hit-test model has proven itself against every
    # off-canvas/transform case (gate on it with --warn-as-error).
    "contrast": "warn",
    "clipped_text": "warn",
    "row_misalign": "warn",
    "off_center": "warn",
    "tap_target": "warn",
    "spacing": "warn",
}

KINDS = tuple(DEFAULT_SEVERITY)

# Network noise that is expected and must not fail runs. Projects add their own
# via [network] ignore = [...].
DEFAULT_NET_IGNORE = ("favicon",)

# Checks that only mean something on a small screen.
MOBILE_ONLY = frozenset({"tap_target"})


def analyze(
    raw: dict,
    console: list,
    failures: list,
    pageerrors: list,
    *,
    mobile: bool,
    severity: dict[str, str] | None = None,
    net_ignore: tuple[str, ...] = DEFAULT_NET_IGNORE,
    click_failures: list | None = None,
) -> list[dict]:
    """Turn raw in-page measurements + captured events into findings."""
    sev = {**DEFAULT_SEVERITY, **(severity or {})}
    found: list[dict] = []

    def add(kind: str, detail: str, anchor: str = "") -> None:
        s = sev.get(kind, "warn")
        if s == "off":
            return
        if kind in MOBILE_ONLY and not mobile:
            return
        found.append({"kind": kind, "severity": s, "detail": detail, "anchor": anchor or detail})

    for sel, why in click_failures or []:
        add("pre_click_failed", f"{sel} — {why}", sel)
    for src in raw.get("brokenImgs", []):
        add("broken_img", src)
    for msg in console:
        if msg.startswith("error"):
            add("console_error", msg[:200])
    for url in failures:
        if not any(n in url for n in net_ignore):
            add("net_4xx", url[:200])
    for err in pageerrors:
        add("js_error", str(err)[:200])
    if raw.get("docOverflow"):
        add("doc_overflow", f"horizontal overflow by {raw['docOverflow']}px", "doc_overflow")
    for c in raw.get("contrast", []):
        add("contrast",
            f"{c['sel']} — {c['ratio']}:1 (needs {c['need']}:1) "
            f"[{c.get('fg')} on {c.get('bg')}] “{c['text']}”",
            c["sel"])
    for c in raw.get("clippedText", []):
        add("clipped_text", f"{c['sel']} clipped by {c['by']}px “{c['text']}”", c["sel"])
    for r in raw.get("rowMisalign", []):
        add("row_misalign", f"{r['sel']} — {r['n']} {r['kind']}s, tops spread {r['spreadPx']}px", r["sel"])
    for c in raw.get("offCenter", []):
        add("off_center", f"{c['sel']} — gutters {c['left']}px / {c['right']}px (Δ{c['delta']}px)", c["sel"])
    for t in raw.get("tapTargets", []):
        add("tap_target", f"{t['sel']} {t['w']}×{t['h']}px “{t['label']}”", t["sel"])
    for s2 in raw.get("spacing", []):
        add("spacing", f"{s2['sel']} — sibling gaps {s2['gaps']} (spread {s2['spread']}px)", s2["sel"])
    return found
