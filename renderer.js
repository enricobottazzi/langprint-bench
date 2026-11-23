/* Shared prose layout for the static book and score.py. No network requests. */
(() => {
  'use strict';

  const layout = Object.freeze({
    pageWidth: 465,
    pageHeight: 624,
    sideMargin: 50,
    topPadding: 40,
    bottomPadding: 52,
    runningHeight: 47,
    bodyWidth: 365,
    bodyHeight: 485,
    fittingAllowance: 2,
    fontSize: 12,
    lineHeight: 1.85,
    linesPerPage: 21,
  });

  const copyCSS = `
    .lp-copy {
      box-sizing: border-box; margin: 0; padding: 0; border: 0;
      font-size: ${layout.fontSize}px; font-weight: 400; font-style: normal;
      line-height: ${layout.lineHeight};
      font-synthesis: none; font-optical-sizing: none;
      text-align: start; white-space: normal; hyphens: none;
      word-break: normal; overflow-wrap: normal;
      letter-spacing: normal; word-spacing: normal;
    }
    .lp-copy p {
      margin: 0; padding: 0; border: 0; text-indent: 1.3em;
      font-family: inherit; font-size: inherit; font-weight: inherit;
      font-style: inherit; line-height: inherit;
    }
    .lp-copy p:first-child { text-indent: 0; }
  `;

  function installStyles() {
    let style = document.getElementById('langprint-pagination-css');
    if (!style) {
      style = document.createElement('style');
      style.id = 'langprint-pagination-css';
      document.head.append(style);
    }
    if (style.textContent !== copyCSS) style.textContent = copyCSS;
  }

  async function paginate({text, lang = 'en', fontFamily = '"Noto Serif", serif'} = {}) {
    if (typeof text !== 'string') throw new TypeError('text must be a string');
    if (typeof lang !== 'string' || !lang) throw new TypeError('lang must be a language code');
    if (typeof fontFamily !== 'string' || !fontFamily) throw new TypeError('fontFamily must be a CSS font family');
    installStyles();
    await document.fonts.load(`400 ${layout.fontSize}px ${fontFamily}`, text || '\u00a0');
    await document.fonts.ready;

    // A direct body child stays outside the book's zoom/transforms. Its fixed
    // width is the scoring reference, even on a narrow screen.
    const measure = document.createElement('div');
    measure.className = 'lp-copy';
    measure.setAttribute('aria-hidden', 'true');
    measure.dataset.langprintMeasure = '';
    measure.lang = lang;
    measure.dir = lang === 'ar' ? 'rtl' : 'ltr';
    Object.assign(measure.style, {
      position: 'absolute', left: '-100000px', top: '0',
      width: `${layout.bodyWidth}px`, height: 'auto', minHeight: '0',
      maxHeight: 'none', visibility: 'hidden', pointerEvents: 'none',
      fontFamily, zoom: '1',
    });
    document.body.append(measure);

    try {
      const probe = document.createElement('p');
      probe.textContent = '\u00a0';
      measure.append(probe);
      const lineHeight = probe.getBoundingClientRect().height;
      probe.remove();
      if (!Number.isFinite(lineHeight) || lineHeight <= 0) {
        throw new Error('Cannot measure the rendered line height.');
      }

      const limit = layout.bodyHeight - layout.fittingAllowance;
      const pages = [];
      let current = [];
      function finish() {
        if (!current.length) return;
        const height = measure.getBoundingClientRect().height;
        if (height > limit + 0.02 || measure.scrollWidth > measure.clientWidth + 1) {
          throw new Error('Text overflows the fixed page; it cannot be scored without clipping.');
        }
        const lines = Math.round(height / lineHeight);
        pages.push({height, lines, paragraphs: current});
        current = [];
        measure.replaceChildren();
      }

      const cjk = lang === 'ja' || lang === 'zh-Hans';
      const segmenter = cjk ? new Intl.Segmenter(lang, {granularity: 'word'}) : null;
      for (const paragraph of text.replace(/\r\n/g, '\n').split(/\n+/).map(p => p.trim()).filter(Boolean)) {
        let tokens = cjk ? [...segmenter.segment(paragraph)].map(p => p.segment)
                         : (paragraph.match(/\S+\s*/g) || []);
        while (tokens.length) {
          const p = document.createElement('p');
          measure.append(p);
          let lo = 0, hi = tokens.length;
          while (lo < hi) {
            const mid = Math.ceil((lo + hi) / 2);
            p.textContent = tokens.slice(0, mid).join('');
            if (measure.getBoundingClientRect().height <= limit) lo = mid;
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
      const totalLines = pages.reduce((sum, page) => sum + page.lines, 0);
      return {pages, totalLines, occupied_pages: totalLines / layout.linesPerPage, lineHeight};
    } finally {
      measure.remove();
    }
  }

  globalThis.LangPrintRenderer = Object.freeze({layout, copyCSS, paginate});
})();
