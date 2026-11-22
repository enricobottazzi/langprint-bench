"""Measure fractional occupied pages: 21 rendered lines equal one page.

Setup: pip install -r requirements.txt && python -m playwright install chromium
Usage: from score import score; occupied_pages = score(entry)

Only ``lang`` and ``text`` affect the score. Fonts are downloaded from a pinned
Google Fonts revision on first use, verified, and cached in .cache/fonts beside
this file. Set LANGPRINT_FONT_CACHE to use another cache directory. Passage text
is rendered locally and is never included in font download requests.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import os
from pathlib import Path
import tempfile
from urllib.parse import quote
from urllib.request import urlopen


PAGE_WIDTH = 465
PAGE_HEIGHT = 624
SIDE_MARGIN = 50
BODY_WIDTH = PAGE_WIDTH - 2 * SIDE_MARGIN
BODY_HEIGHT = PAGE_HEIGHT - 40 - 52 - 47
FONT_SIZE = 12
LINE_HEIGHT = 1.85
LINES_PER_PAGE = 21

_FONT_REVISION = "06bfe0d62a98375cb09c942fa18e68bd32cff057"
# Family: (upstream directory, filename, SHA-256). Fonts are SIL OFL licensed.
# https://github.com/google/fonts/tree/06bfe0d62a98375cb09c942fa18e68bd32cff057/ofl
_FONTS = {
    "Noto Serif": (
        "notoserif", "NotoSerif[wdth,wght].ttf",
        "4d8e6761424656867019081a1a01336f3cb086982682698714054fc33f782713",
    ),
    "Noto Naskh Arabic": (
        "notonaskharabic", "NotoNaskhArabic[wght].ttf",
        "67b5a525a661b607971fbd3f96a81b89d3a768e74534fca84f18ac97e6fab72f",
    ),
    "Noto Serif Devanagari": (
        "notoserifdevanagari", "NotoSerifDevanagari[wdth,wght].ttf",
        "1191e07bfeb062d80e252eb85b0eafdfbda1e350707a2a60628668e8f677dbbb",
    ),
    "Noto Serif SC": (
        "notoserifsc", "NotoSerifSC[wght].ttf",
        "050080d9255a86808f2945bffac582b31ef32bc36411ce29563b4961670c66f9",
    ),
    "Noto Serif JP": (
        "notoserifjp", "NotoSerifJP[wght].ttf",
        "2fd527ba12b6a44ec30d796d633360da0aeba6c5d4af1304ce12bb4dc15a7dfc",
    ),
    "Noto Sans Mono": (
        "notosansmono", "NotoSansMono[wdth,wght].ttf",
        "2cb2adb378a8f574213e23df697050b83c54c27df465a2015552740b2769a081",
    ),
}
_LANGUAGES = dict.fromkeys(("en", "de", "it", "ru", "es", "sw"), "Noto Serif")
_LANGUAGES.update({
    "ar": "Noto Naskh Arabic",
    "hi": "Noto Serif Devanagari",
    "zh-Hans": "Noto Serif SC",
    "ja": "Noto Serif JP",
})

_HTML = """<!doctype html><meta charset="utf-8">
<style>
  * { box-sizing: border-box; }
  body { margin: 0; }
  #page { width: 465px; height: 624px; padding: 40px 50px 52px; }
  #running { height: 47px; }
  .copy {
    font-size: 12px; font-weight: 400; line-height: 1.85;
    font-synthesis: none; font-optical-sizing: none;
    text-align: start; white-space: normal; hyphens: none;
    word-break: normal; overflow-wrap: normal;
  }
  .copy p { margin: 0; padding: 0; text-indent: 1.3em; }
  .copy p:first-child { text-indent: 0; }
  #glyph-check { width: 365px; }
</style>
<div id="page"><div id="running"></div><div id="copy" class="copy"></div></div>
<div id="glyph-check" class="copy"></div>
"""

_MEASURE = r"""async ({lang, text, fonts, bodyHeight, linesPerPage}) => {
  for (const {family, url} of fonts) {
    const face = new FontFace(family, `url("${url}")`, {weight: '400'});
    document.fonts.add(await face.load());
  }
  const family = fonts.map(font => JSON.stringify(font.family)).join(', ');
  const page = document.getElementById('page');
  page.lang = lang;
  page.dir = lang === 'ar' ? 'rtl' : 'ltr';
  const body = document.getElementById('copy');
  body.style.fontFamily = family;
  await document.fonts.load(`400 12px ${JSON.stringify(fonts[0].family)}`, text);
  await document.fonts.ready;

  // Calibrate the actual line box, including Chromium's subpixel rounding.
  const probe = document.createElement('p');
  probe.textContent = '\u00a0';
  body.append(probe);
  const lineHeight = probe.getBoundingClientRect().height;
  probe.remove();
  if (!Number.isFinite(lineHeight) || lineHeight <= 0) {
    throw new Error('Cannot measure the rendered line height.');
  }

  // Keep the reader's fitting tolerance; score by its 21-line capacity.
  const limit = bodyHeight - 2;
  const pages = [];
  let current = [];
  function finish() {
    if (!current.length) return;
    const height = body.getBoundingClientRect().height;
    if (height > limit + 0.02 || body.scrollWidth > body.clientWidth + 1) {
      throw new Error('Text overflows the fixed page; it cannot be scored without clipping.');
    }
    const lines = Math.round(height / lineHeight);
    pages.push({height, lines, paragraphs: current});
    current = [];
    body.replaceChildren();
  }
  const cjk = lang === 'ja' || lang === 'zh-Hans';
  const segmenter = cjk ? new Intl.Segmenter(lang, {granularity: 'word'}) : null;
  for (const paragraph of text.replace(/\r\n/g, '\n').split(/\n+/).map(p => p.trim()).filter(Boolean)) {
    let tokens = cjk ? [...segmenter.segment(paragraph)].map(p => p.segment)
                     : (paragraph.match(/\S+\s*/g) || []);
    while (tokens.length) {
      const p = document.createElement('p');
      body.append(p);
      let lo = 0, hi = tokens.length;
      while (lo < hi) {
        const mid = Math.ceil((lo + hi) / 2);
        p.textContent = tokens.slice(0, mid).join('');
        if (body.getBoundingClientRect().height <= limit) lo = mid;
        else hi = mid - 1;
      }
      if (lo === 0 && current.length) {
        p.remove(); finish(); continue;
      }
      const count = Math.max(1, lo);
      p.textContent = tokens.slice(0, count).join('').trimEnd();
      current.push(p.textContent);
      tokens = tokens.slice(count);
      if (tokens.length) finish();
    }
  }
  finish();

  // Keep a text node available for Chromium's actual-font check, independently
  // of the temporary pages above. Its geometry is never part of the score.
  const check = document.getElementById('glyph-check');
  check.lang = lang; check.dir = page.dir; check.style.fontFamily = family;
  check.textContent = text;
  const totalLines = pages.reduce((sum, p) => sum + p.lines, 0);
  return {pages, occupied_pages: totalLines / linesPerPage};
}"""


def _font_path(family: str) -> Path:
    directory, filename, expected_hash = _FONTS[family]
    cache = Path(os.environ.get(
        "LANGPRINT_FONT_CACHE", str(Path(__file__).resolve().parent / ".cache" / "fonts")
    ))
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / filename
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise RuntimeError(f"Corrupt cached font: {path}. Remove it and retry.")
        return path

    url = (
        f"https://raw.githubusercontent.com/google/fonts/{_FONT_REVISION}"
        f"/ofl/{directory}/{quote(filename, safe='')}"
    )
    temporary = None
    try:
        with urlopen(url, timeout=120) as response, tempfile.NamedTemporaryFile(
            dir=cache, delete=False
        ) as output:
            temporary = Path(output.name)
            digest = hashlib.sha256()
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != expected_hash:
            raise RuntimeError(f"Downloaded font checksum mismatch: {family}")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def score(entry: Mapping[str, object]) -> float:
    """Return rendered line count / 21 for a JSON-decoded passage entry.

    Required keys: ``lang`` (one of the ten methodology codes), ``text`` (str).
    Other fields, including title and original/translated status, are ignored.
    Whitespace-only text returns 0.0. Missing fonts, system-font fallback, and clipped
    text raise errors instead of yielding misleading measurements.
    """
    if not isinstance(entry, Mapping):
        raise TypeError("entry must be a JSON object / mapping")
    lang, text = entry.get("lang"), entry.get("text")
    if not isinstance(lang, str) or lang not in _LANGUAGES:
        raise ValueError(f"lang must be one of: {', '.join(_LANGUAGES)}")
    if not isinstance(text, str):
        raise TypeError("entry['text'] must be a string")
    if not text.strip():
        return 0.0

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "Install the scorer dependencies: pip install -r requirements.txt; "
            "python -m playwright install chromium"
        ) from error

    primary = _LANGUAGES[lang]
    families = [primary] if primary == "Noto Serif" else [primary, "Noto Serif"]
    # Explicit fallback for source characters such as SCP redaction bars (█).
    families.append("Noto Sans Mono")
    # Translations can retain enclosed digits (①②③④). The already pinned
    # Japanese font covers them; keep existing glyph choices ahead of it.
    if primary != "Noto Serif JP":
        families.append("Noto Serif JP")
    font_paths = {
        f"https://langprint.invalid/{index}.ttf": _font_path(family)
        for index, family in enumerate(families)
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(
                viewport={"width": 930, "height": 624},
                device_scale_factor=1, locale="en-US", offline=True,
            )

            def serve_font(route):
                path = font_paths.get(route.request.url)
                if path is None:
                    route.abort()
                else:
                    route.fulfill(path=path, content_type="font/ttf", headers={
                        "Access-Control-Allow-Origin": "*",
                    })

            context.route("**/*", serve_font)
            page = context.new_page()
            page.set_content(_HTML)
            result = page.evaluate(_MEASURE, {
                "lang": lang, "text": text, "bodyHeight": BODY_HEIGHT,
                "linesPerPage": LINES_PER_PAGE,
                "fonts": [
                    {"family": family, "url": url}
                    for family, url in zip(families, font_paths)
                ],
            })
            # Reject accidental system-font fallback, including missing glyphs.
            cdp = context.new_cdp_session(page)
            cdp.send("DOM.enable")
            cdp.send("CSS.enable")
            document = cdp.send("DOM.getDocument")
            node = cdp.send("DOM.querySelector", {
                "nodeId": document["root"]["nodeId"], "selector": "#glyph-check",
            })
            fonts = cdp.send("CSS.getPlatformFontsForNode", {
                "nodeId": node["nodeId"],
            })["fonts"]
            fallbacks = [font["familyName"] for font in fonts if not font["isCustomFont"]]
            if fallbacks:
                raise ValueError(f"Text needs glyphs outside the pinned fonts: {', '.join(fallbacks)}")
            return float(result["occupied_pages"])
        finally:
            browser.close()
