"""Semantic accessibility checks, run inside the page.

Deliberately a *second* collector rather than an addition to `checks.COLLECT_JS`.
Three reasons, in order of how much they matter:

1. `COLLECT_JS` is tuned and its thresholds do not move (see CLAUDE.md #5).
   Growing it invites exactly the edits that rule exists to prevent.
2. This pass asks the DOM different questions — about *meaning*, not geometry.
   A label is missing or it isn't; there is no threshold to tune.
3. It can be switched off wholesale (`[a11y] enabled = false`) without
   disturbing the geometry checks, which is what a project drowning in
   pre-existing a11y debt will want on day one.

Everything here defaults to `warn`. These are real defects — a control a screen
reader cannot name is broken, not untidy — but shipping them as errors would
turn a green CI red for every existing consumer on the day they upgrade. A
project that has cleaned up promotes them: `severity.no_accessible_name = "error"`.

What is deliberately NOT checked: colour contrast (COLLECT_JS already does it,
better, by compositing the real paint stack), and anything needing the
accessibility tree rather than the DOM. Guessing at what a screen reader would
announce is the same class of lie as guessing at a pixel.
"""
from __future__ import annotations

# Returns {imgNoAlt, noAccessibleName, inputNoLabel, headingSkips, duplicateIds,
#          noLang, noLandmark, positiveTabindex}
A11Y_JS = r"""
() => {
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
  // Hidden from the accessibility tree on purpose — decorative, and correctly
  // nameless. Not a finding.
  const ariaHidden = (el) => !!el.closest('[aria-hidden="true"]');

  // The name a screen reader would announce, as far as the DOM can tell:
  // aria-label, aria-labelledby, title, own text, or a nested image's alt.
  const nameOf = (el) => {
    const byLabel = el.getAttribute('aria-label');
    if (byLabel && byLabel.trim()) return byLabel.trim();
    const ref = el.getAttribute('aria-labelledby');
    if (ref) {
      const t = ref.split(/\s+/).map(id => document.getElementById(id))
                   .filter(Boolean).map(n => n.textContent.trim()).join(' ');
      if (t) return t;
    }
    const title = el.getAttribute('title');
    if (title && title.trim()) return title.trim();
    const text = (el.textContent || '').trim();
    if (text) return text;
    const img = el.querySelector('img[alt], svg title, [role="img"][aria-label]');
    if (img) {
      const a = img.getAttribute('alt') || img.getAttribute('aria-label')
                || img.textContent || '';
      if (a.trim()) return a.trim();
    }
    return '';
  };

  // 1. images with no alt attribute at all. alt="" is CORRECT for decorative
  //    images and is not reported — the author said "ignore me" on purpose.
  const imgNoAlt = [];
  for (const img of document.images) {
    if (imgNoAlt.length >= 15) break;
    if (!vis(img) || ariaHidden(img)) continue;
    if (img.hasAttribute('alt') || img.getAttribute('role') === 'presentation') continue;
    imgNoAlt.push({ sel: path(img), src: (img.currentSrc || img.src || '').slice(-60) });
  }

  // 2. interactive things a screen reader cannot name
  const noAccessibleName = [];
  for (const el of document.querySelectorAll(
      'a[href], button, [role="button"], [role="link"], [role="tab"]')) {
    if (noAccessibleName.length >= 15) break;
    if (!vis(el) || ariaHidden(el)) continue;
    if (nameOf(el)) continue;
    noAccessibleName.push({ sel: path(el), tag: el.tagName.toLowerCase() });
  }

  // 3. form controls with no label. Checks the real association rules:
  //    wrapping <label>, for=/id=, aria-*, title. Not placeholder — a
  //    placeholder disappears on focus and is not a label.
  const inputNoLabel = [];
  for (const el of document.querySelectorAll('input, select, textarea')) {
    if (inputNoLabel.length >= 15) break;
    if (!vis(el) || ariaHidden(el)) continue;
    const type = (el.getAttribute('type') || '').toLowerCase();
    if (['hidden', 'submit', 'button', 'reset', 'image'].includes(type)) continue;
    if (nameOf(el)) continue;
    if (el.closest('label')) continue;
    if (el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`)) continue;
    inputNoLabel.push({ sel: path(el), type: type || el.tagName.toLowerCase(),
                        placeholder: (el.getAttribute('placeholder') || '').slice(0, 24) });
  }

  // 4. heading order. A jump from h2 to h4 breaks outline navigation, which is
  //    how a screen-reader user skims a page.
  const headingSkips = [];
  let prev = 0;
  for (const h of document.querySelectorAll('h1,h2,h3,h4,h5,h6')) {
    if (headingSkips.length >= 10) break;
    if (!vis(h) || ariaHidden(h)) continue;
    const lvl = +h.tagName[1];
    if (prev && lvl > prev + 1) {
      headingSkips.push({ sel: path(h), from: prev, to: lvl,
                          text: (h.textContent || '').trim().slice(0, 32) });
    }
    prev = lvl;
  }

  // 5. duplicate ids — breaks label[for], aria-labelledby and anchors
  const duplicateIds = [];
  const seenId = new Set(), dupSeen = new Set();
  for (const el of document.querySelectorAll('[id]')) {
    if (duplicateIds.length >= 10) break;
    const id = el.id;
    if (!id) continue;
    if (seenId.has(id) && !dupSeen.has(id)) {
      dupSeen.add(id);
      duplicateIds.push({ id, sel: path(el) });
    }
    seenId.add(id);
  }

  // 6. document language — without it a screen reader guesses the voice
  const lang = document.documentElement.getAttribute('lang');
  const noLang = !lang || !lang.trim();

  // 7. a main landmark, so "skip to content" has somewhere to go
  const noLandmark = !document.querySelector('main, [role="main"]');

  // 8. positive tabindex — forces an order that fights the visual one
  const positiveTabindex = [];
  for (const el of document.querySelectorAll('[tabindex]')) {
    if (positiveTabindex.length >= 10) break;
    if (!vis(el)) continue;
    const t = parseInt(el.getAttribute('tabindex'), 10);
    if (t > 0) positiveTabindex.push({ sel: path(el), tabindex: t });
  }

  return { imgNoAlt, noAccessibleName, inputNoLabel, headingSkips,
           duplicateIds, noLang, noLandmark, positiveTabindex };
}
"""

# All warn by default — see the module docstring for why none of these ship as
# errors. Projects promote what they have cleaned up.
A11Y_SEVERITY: dict[str, str] = {
    "img_no_alt": "warn",
    "no_accessible_name": "warn",
    "input_no_label": "warn",
    "heading_skip": "warn",
    "duplicate_id": "warn",
    "no_lang": "warn",
    "no_landmark": "warn",
    "positive_tabindex": "warn",
}

A11Y_KINDS = tuple(A11Y_SEVERITY)


def findings(raw: dict, add) -> None:
    """Turn raw a11y measurements into findings via `add(kind, detail, anchor)`.

    `add` is `checks.analyze`'s emitter, so severity resolution, `severity=off`
    and the mobile-only rule all stay in exactly one place.
    """
    for i in raw.get("imgNoAlt", []):
        add("img_no_alt", f"{i['sel']} — no alt attribute (…{i['src']})", i["sel"])
    for n in raw.get("noAccessibleName", []):
        add("no_accessible_name",
            f"{n['sel']} — <{n['tag']}> a screen reader cannot name", n["sel"])
    for f in raw.get("inputNoLabel", []):
        extra = f" (placeholder “{f['placeholder']}” is not a label)" if f["placeholder"] else ""
        add("input_no_label", f"{f['sel']} — {f['type']} has no label{extra}", f["sel"])
    for h in raw.get("headingSkips", []):
        add("heading_skip",
            f"{h['sel']} — h{h['from']} jumps to h{h['to']} “{h['text']}”", h["sel"])
    for d in raw.get("duplicateIds", []):
        add("duplicate_id", f"id=\"{d['id']}\" used more than once ({d['sel']})",
            f"id={d['id']}")
    if raw.get("noLang"):
        add("no_lang", "<html> has no lang attribute", "html[lang]")
    if raw.get("noLandmark"):
        add("no_landmark", "no <main> or role=\"main\" landmark", "main")
    for t in raw.get("positiveTabindex", []):
        add("positive_tabindex",
            f"{t['sel']} — tabindex={t['tabindex']} overrides natural focus order",
            t["sel"])
