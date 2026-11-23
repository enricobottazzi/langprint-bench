/* Static, synchronized editions. Text layout is shared with score.py. */
(async () => {
  'use strict';
  const data = JSON.parse(document.getElementById('book-data').textContent);
  const layout = LangPrintRenderer.layout;
  const reader = document.querySelector('.reader');
  const status = document.getElementById('book-position');
  const report = {sourceSha256: data.sourceSha256, books: 10, pagesPerBook: data.totalPages, about: [], contents: [], passages: [], overflows: [], scoreMismatches: [], nativeReflowDifferences: []};
  const reportNode = document.getElementById('fit-report');
  const books = [];
  const mainFonts = {ar: 'Noto Naskh Arabic', hi: 'Noto Serif Devanagari', 'zh-Hans': 'Noto Serif SC', ja: 'Noto Serif JP'};
  const fontFor = lang => [...new Set([mainFonts[lang] || 'Noto Serif', 'Noto Serif', 'Noto Sans Mono', 'Noto Serif JP'])].map(f => JSON.stringify(f)).join(', ');
  const latinFont = fontFor('en');
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const upper = (text, locale) => text.toLocaleUpperCase(locale.lang);
  const numeral = locale => new Intl.NumberFormat(locale.lang, {useGrouping: false});
  const markTitle = (title, original) => title + (original ? ' *' : '');
  const normalized = text => text.replace(/\s+/g, '');

  for (const family of new Set(Object.values(mainFonts).concat('Noto Serif', 'Noto Sans Mono', 'Noto Serif JP'))) {
    await document.fonts.load(`400 12px "${family}"`);
  }
  await document.fonts.ready;

  function makePage(book, folio, {kind = 'text', title = '', discipline = '', original = false, first = false, blank = false, idx} = {}) {
    const page = el('section', `page page--${kind}` + (blank ? ' page--padding' : ''));
    page.id = `${book.lang}-page-${folio}`;
    page.dataset.folio = String(folio);
    if (idx !== undefined) page.dataset.idx = String(idx);
    if (blank) page.dataset.blank = 'true';
    page.dataset.section = kind;
    page.dataset.sectionTitle = title;
    page.setAttribute('aria-label', `${blank ? book.locale.ui.blankPage : title}, ${book.locale.ui.page} ${book.number.format(folio)}`);
    if (folio > 2) {
      const running = el(first ? 'h2' : 'div', 'running');
      const isTitlePage = !discipline || folio % 2 === 1;
      const label = el('span', 'running-title', upper(isTitlePage ? title : discipline, book.locale));
      running.append(label);
      if (original && isTitlePage) {
        const marker = el('span', 'original-marker', '*');
        marker.setAttribute('aria-label', book.locale.ui.originalLabel);
        running.append(marker);
      }
      if (!first) running.setAttribute('aria-hidden', 'true');
      page.append(running);
      const number = el('span', 'folio', book.number.format(folio));
      number.setAttribute('aria-hidden', 'true');
      page.append(number);
    }
    book.pages[folio - 1] = page;
    return page;
  }

  function appendFragment(page, fragment, {lang, font, latin = false}) {
    const copy = el('div', 'book-copy lp-copy');
    copy.lang = latin ? 'la' : lang;
    copy.dir = latin ? 'ltr' : lang === 'ar' ? 'rtl' : 'ltr';
    copy.style.width = layout.bodyWidth + 'px';
    copy.style.fontFamily = font;
    copy.dataset.lines = String(fragment.lines);
    for (const text of fragment.paragraphs) {
      const paragraph = el('p');
      if (typeof text === 'string') paragraph.textContent = text;
      else { paragraph.textContent = text.lines.join('\n'); paragraph.style.whiteSpace = 'pre'; }
      copy.append(paragraph);
    }
    page.insertBefore(copy, page.querySelector('.folio'));
    return copy;
  }

  function makeTitle(book) {
    const page = makePage(book, 1, {kind: 'title'});
    const content = el('div', 'title-content');
    const title = el('h1');
    title.id = `book-title-${book.lang}`;
    title.dir = 'ltr';
    title.lang = 'en';
    title.style.fontFamily = '"Noto Serif", serif';
    title.append('LangPrint', el('br'), 'Bench');
    page.setAttribute('aria-labelledby', title.id);
    content.append(title, el('p', 'subtitle', book.locale.ui.subtitle));
    page.append(content);
  }

  function heatColor(value) {
    const center = [251, 245, 231];
    const end = value < 1 ? [135, 171, 139] : [199, 127, 120];
    const amount = Math.min(1, Math.abs(value - 1) / .4);
    return `rgb(${center.map((c, i) => Math.round(c + (end[i] - c) * amount)).join(',')})`;
  }

  function makeHeatmap(book) {
    const page = makePage(book, 2, {kind: 'heatmap'});
    const figure = el('figure', 'heatmap-content');
    const frame = el('div', 'heatmap-frame');
    const table = el('table', 'heatmap');
    table.setAttribute('aria-label', book.locale.ui.subtitle);
    table.dataset.sourceSha256 = data.sourceSha256;
    const cols = el('colgroup');
    for (let i = 0; i <= data.disciplines.length; i++) cols.append(el('col'));
    table.append(cols);
    const head = el('thead'), headings = el('tr');
    const corner = el('th');
    corner.scope = 'col';
    corner.append(el('span', 'sr-only', book.locale.ui.language));
    headings.append(corner);
    for (const discipline of data.disciplines) {
      const cell = el('th'); cell.scope = 'col';
      cell.append(el('span', 'column-label', book.locale.disciplines[discipline]));
      headings.append(cell);
    }
    head.append(headings); table.append(head);
    const body = el('tbody');
    for (const language of data.languages) {
      const row = el('tr');
      const label = el('th', '', book.locale.languageNames[language.lang]);
      label.scope = 'row'; row.append(label);
      for (const discipline of data.disciplines) {
        const value = data.heatmap.find(c => c.lang === language.lang && c.discipline === discipline).occupied_pages_ratio;
        const cell = el('td');
        cell.dataset.ratio = String(value);
        cell.style.backgroundColor = heatColor(value);
        cell.setAttribute('aria-label', `${book.locale.languageNames[language.lang]}, ${book.locale.disciplines[discipline]}: ${new Intl.NumberFormat(book.lang, {maximumFractionDigits: 2}).format(value)}`);
        row.append(cell);
      }
      body.append(row);
    }
    table.append(body); frame.append(table); figure.append(frame); page.append(figure);
  }

  async function makeContents(book) {
    const measure = el('div', 'index-copy lp-copy');
    measure.lang = book.lang; measure.dir = book.dir;
    Object.assign(measure.style, {position: 'absolute', left: '-100000px', top: '0', visibility: 'hidden', width: layout.bodyWidth + 'px', fontFamily: book.font});
    document.body.append(measure);
    const fragments = [], rows = [];
    function finish() {
      if (!measure.childNodes.length) return;
      const fragment = document.createDocumentFragment();
      fragment.append(...measure.childNodes);
      fragments.push(fragment);
    }
    const fits = () => measure.getBoundingClientRect().height <= layout.bodyHeight - layout.fittingAllowance && measure.scrollWidth <= layout.bodyWidth + 1;
    try {
      for (const discipline of data.disciplines) {
        const heading = el('h3', 'index-discipline', book.locale.disciplines[discipline]);
        heading.dataset.discipline = discipline;
        const passages = data.passages.filter(p => p.discipline === discipline);
        for (const [index, passage] of passages.entries()) {
          const version = passage.versions[book.lang];
          const row = el('a', 'index-entry');
          row.href = `#page-${passage.startPage}`;
          row.dataset.idx = String(passage.idx);
          row.dataset.pageStart = String(passage.startPage);
          row.dataset.pageEnd = String(passage.endPage);
          row.dataset.allocatedPages = String(passage.allocatedPages);
          row.dataset.original = String(version.original);
          row.append(el('span', '', markTitle(book.locale.titles[passage.idx], version.original)), el('span', 'index-range', book.number.format(passage.startPage)));
          const nodes = index === 0 ? [heading, row] : [row];
          measure.append(...nodes);
          if (!fits()) {
            nodes.forEach(node => node.remove()); finish(); measure.append(...nodes);
            if (!fits()) throw new Error(`Contents entry ${book.lang}/${passage.idx} overflows a page.`);
          }
          rows.push(row);
        }
      }
      finish();
    } finally { measure.remove(); }
    report.contents.push({lang: book.lang, required: fragments.length, available: data.contentsPages, entries: rows.length});
    if (fragments.length > data.contentsPages) {
      report.overflows.push({lang: book.lang, section: 'contents', required: fragments.length, available: data.contentsPages});
      reportNode.textContent = JSON.stringify(report);
      throw new Error(`Contents exceeds its allocation: ${book.lang}`);
    }
    for (let i = 0; i < data.contentsPages; i++) {
      const page = makePage(book, i + 5, {kind: 'index', title: book.locale.ui.contents, first: i === 0, blank: !fragments[i]});
      if (fragments[i]) {
        const copy = el('div', 'index-copy lp-copy'); copy.style.width = layout.bodyWidth + 'px';
        copy.append(fragments[i]); page.insertBefore(copy, page.querySelector('.folio'));
      }
    }
  }

  for (const locale of data.languages) {
    const block = el('article', 'book-block');
    block.lang = locale.lang; block.dir = locale.dir; block.dataset.lang = locale.lang;
    const font = fontFor(locale.lang); block.style.fontFamily = font;
    const caption = el('h2', 'book-language', locale.nativeName);
    const shell = el('div', 'book-shell');
    const previous = el('button', 'page-arrow page-previous', locale.dir === 'rtl' ? '›' : '‹');
    const next = el('button', 'page-arrow page-next', locale.dir === 'rtl' ? '‹' : '›');
    previous.type = next.type = 'button';
    previous.setAttribute('aria-label', locale.ui.previousPages); next.setAttribute('aria-label', locale.ui.nextPages);
    const paper = el('div', 'paperback');
    paper.dataset.lang = locale.lang;
    paper.setAttribute('aria-label', locale.nativeName);
    shell.append(previous, paper, next); block.append(caption, shell);
    const book = {lang: locale.lang, dir: locale.dir, locale, block, book: paper, shell, previous, next, pages: [], spreads: [], font, number: numeral(locale)};
    makeTitle(book); makeHeatmap(book);
    const about = await LangPrintRenderer.paginate({text: locale.aboutText, lang: 'en', fontFamily: latinFont});
    report.about.push({lang: locale.lang, required: about.pages.length, available: 2});
    if (about.pages.length > 2) {
      report.overflows.push({lang: locale.lang, section: 'about', required: about.pages.length, available: 2});
      reportNode.textContent = JSON.stringify(report);
      throw new Error(`About exceeds its allocation: ${locale.lang}`);
    }
    for (let i = 0; i < 2; i++) {
      const page = makePage(book, i + 3, {kind: 'text', title: locale.ui.about, first: i === 0, blank: !about.pages[i]});
      if (about.pages[i]) appendFragment(page, about.pages[i], {lang: 'en', font: latinFont, latin: true});
    }
    await makeContents(book);
    for (const passage of data.passages) {
      const version = passage.versions[locale.lang];
      let result = await LangPrintRenderer.paginate({text: version.text, lang: locale.lang, fontFamily: font});
      if (Math.abs(result.occupied_pages - version.occupiedPages) > 1e-10 && version.referenceLayout) {
        report.nativeReflowDifferences.push({lang: locale.lang, idx: passage.idx, native: result.occupied_pages, reference: version.occupiedPages});
        const reference = version.referenceLayout;
        const fullText = reference.pages.flatMap(p => p.paragraphs.flatMap(p => p.lines)).join(' ');
        if (normalized(fullText) !== normalized(version.text)) throw new Error(`Reference text mismatch in ${locale.lang}/${passage.idx}`);
        for (const fragment of reference.pages) {
          const host = el('div');
          const copy = appendFragment(host, fragment, {lang: locale.lang, font});
          Object.assign(copy.style, {position: 'absolute', left: '-100000px', top: '0', visibility: 'hidden'});
          document.body.append(copy);
          try {
            const height = copy.getBoundingClientRect().height;
            const lines = Math.round(height / parseFloat(getComputedStyle(copy).lineHeight));
            if (height > layout.bodyHeight - layout.fittingAllowance || copy.scrollWidth > copy.clientWidth + 1 || lines !== fragment.lines) {
              throw new Error(`Reference layout does not fit ${locale.lang}/${passage.idx}`);
            }
          } finally { copy.remove(); }
        }
        result = {pages: reference.pages, occupied_pages: reference.occupied_pages};
      }
      const sameText = normalized(result.pages.flatMap(p => p.paragraphs.flatMap(p => typeof p === 'string' ? [p] : p.lines)).join(' ')) === normalized(version.text);
      if (!sameText) throw new Error(`Text loss in ${locale.lang}/${passage.idx}`);
      if (Math.abs(result.occupied_pages - version.occupiedPages) > 1e-10) report.scoreMismatches.push({lang: locale.lang, idx: passage.idx, expected: version.occupiedPages, actual: result.occupied_pages});
      if (result.pages.length > passage.allocatedPages) {
        report.overflows.push({lang: locale.lang, idx: passage.idx, section: 'passage', required: result.pages.length, available: passage.allocatedPages});
        reportNode.textContent = JSON.stringify(report);
        throw new Error(`Text exceeds its allocation: ${locale.lang}/${passage.idx}`);
      }
      report.passages.push({lang: locale.lang, idx: passage.idx, pages: result.pages.length, allocated: passage.allocatedPages, score: result.occupied_pages});
      for (let i = 0; i < passage.allocatedPages; i++) {
        const fragment = result.pages[i];
        const page = makePage(book, passage.startPage + i, {kind: 'passage', title: locale.titles[passage.idx], discipline: locale.disciplines[passage.discipline], original: version.original, first: i === 0, blank: !fragment, idx: passage.idx});
        page.dataset.discipline = passage.discipline;
        page.dataset.original = String(version.original);
        if (fragment) appendFragment(page, fragment, {lang: locale.lang, font});
      }
    }
    for (let i = 0; i < book.pages.length; i += 2) {
      const spread = el('div', 'spread');
      spread.setAttribute('role', 'group');
      spread.setAttribute('aria-label', `${locale.ui.pages} ${book.number.format(i + 1)}–${book.number.format(i + 2)}`);
      spread.append(...book.pages.slice(i, i + 2));
      paper.append(spread); book.spreads.push(spread);
    }
    paper.dataset.pageCount = String(book.pages.length);
    paper.dataset.ready = 'true';
    reader.append(block); books.push(book);
    status.textContent = `${locale.ui.loading} ${books.length}/10`;
    // Give the loading indicator a chance to paint between complete editions.
    await new Promise(resolve => setTimeout(resolve, 0));
  }
  reportNode.textContent = JSON.stringify(report);
  document.documentElement.dataset.fit = report.overflows.length || report.scoreMismatches.length ? 'failed' : 'passed';
  LangPrintNavigation.mount({books, locales: data.languages, totalPages: data.totalPages});
  document.querySelector('.loading-books').remove();
})().catch(error => {
  console.error(error);
  const node = document.getElementById('book-position');
  node.textContent = error.message;
  const loading = document.querySelector('.loading-books');
  if (loading) loading.textContent = error.message;
  document.documentElement.dataset.ready = 'error';
});
