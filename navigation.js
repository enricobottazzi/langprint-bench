/* Synchronized book navigation. All passages and fonts remain browser-local. */
(() => {
  'use strict';

  function mount({books, totalPages}) {
    if (!books.length) throw new Error('No books were supplied.');
    const wide = matchMedia('(min-width: 851px)');
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const root = document.documentElement;
    const status = document.getElementById('book-position');
    const navigation = document.querySelector('.book-nav');
    const languageNavigation = document.querySelector('.language-nav');
    const languageName = document.querySelector('.language-name');
    const languageButtons = [...document.querySelectorAll('.language-nav [data-step]')];
    const lastSpread = Math.ceil(totalPages / 2) - 1;
    const topInset = 68;
    let activeIndex = 0, current = 0, currentFolio = 1;
    let busy = false, drag = null, progress = 0, turnEpoch = 0;
    let stages = [], animations = [], scrollFrame = 0;
    let mobilePoint = {folio: 1, offset: 0};

    const activeBook = () => books[activeIndex];
    const clampPage = number => Math.max(1, Math.min(totalPages, Number(number) || 1));
    const normalClick = event => event.button === 0 && !event.altKey &&
      !event.ctrlKey && !event.metaKey && !event.shiftKey;
    const pageNumber = (book, number) => new Intl.NumberFormat(book.lang).format(number);

    function publishPosition() {
      root.dataset.activeLang = activeBook().lang;
      root.dataset.currentFolio = String(currentFolio);
      root.lang = activeBook().lang;
      for (const book of books) book.book.dataset.spread = String(current);
      const book = activeBook();
      const ui = book.locale.ui;
      status.textContent = wide.matches
        ? book.spreads[current].getAttribute('aria-label')
        : `${book.locale.nativeName} · ${ui.page} ${pageNumber(book, currentFolio)} / ${pageNumber(book, totalPages)}`;
    }

    function localizeControls() {
      const book = activeBook(), ui = book.locale.ui;
      navigation.querySelector('[data-jump="home"]').setAttribute('aria-label', ui.home);
      navigation.querySelector('[data-jump="contents"]').setAttribute('aria-label', ui.contents);
      navigation.setAttribute('aria-label', `${ui.home} · ${ui.contents}`);
      if (languageNavigation) {
        languageNavigation.hidden = wide.matches;
        languageNavigation.dir = 'ltr';
        languageNavigation.setAttribute('aria-label', ui.language);
      }
      if (languageName) {
        languageName.textContent = book.locale.nativeName;
        languageName.lang = book.lang;
        languageName.dir = book.dir;
        languageName.style.fontFamily = book.block.style.fontFamily;
      }
      for (const button of languageButtons) {
        const step = Number(button.dataset.step);
        button.disabled = step < 0 ? activeIndex === 0 : activeIndex === books.length - 1;
        button.setAttribute('aria-label', step < 0 ? ui.previousLanguage : ui.nextLanguage);
      }
    }

    function fitBooks() {
      const referenceWidth = wide.matches ? 930 : 465;
      const fallback = activeBook().shell.clientWidth || document.documentElement.clientWidth;
      for (const book of books) {
        const available = book.shell.clientWidth || fallback;
        const scale = String(Math.min(1, available / referenceWidth));
        if (book.book.style.getPropertyValue('--book-scale') !== scale) {
          book.book.style.setProperty('--book-scale', scale);
        }
      }
    }

    function render() {
      const paged = wide.matches;
      books.forEach((book, index) => {
        book.block.hidden = !paged && index !== activeIndex;
        book.spreads.forEach((spread, number) => {
          const hidden = paged && number !== current;
          if (spread.hidden !== hidden) spread.hidden = hidden;
        });
        book.previous.hidden = !paged;
        book.next.hidden = !paged;
        book.previous.disabled = busy || current === 0;
        book.next.disabled = busy || current === lastSpread;
        book.previous.setAttribute('aria-label', book.locale.ui.previousPages);
        book.next.setAttribute('aria-label', book.locale.ui.nextPages);
      });
      localizeControls();
      fitBooks();
      publishPosition();
    }

    function setActive(book) {
      const index = books.indexOf(book);
      if (index < 0 || index === activeIndex) return;
      activeIndex = index;
      localizeControls();
      publishPosition();
    }

    function captureMobilePoint() {
      const pages = activeBook().pages;
      let low = 0, high = pages.length - 1;
      while (low < high) {
        const middle = Math.ceil((low + high) / 2);
        if (pages[middle].getBoundingClientRect().top <= topInset + 1) low = middle;
        else high = middle - 1;
      }
      const box = pages[low].getBoundingClientRect();
      return {folio: low + 1, offset: box.height ? (topInset - box.top) / box.height : 0};
    }

    function restoreMobilePoint(point) {
      const folio = clampPage(point.folio);
      const box = activeBook().pages[folio - 1].getBoundingClientRect();
      const desiredTop = topInset - point.offset * box.height;
      window.scrollBy(0, box.top - desiredTop);
      mobilePoint = {folio, offset: point.offset};
      currentFolio = folio;
      current = Math.floor((folio - 1) / 2);
      publishPosition();
    }

    function clearStages() {
      for (const stage of stages) stage.overlay.remove();
      stages = [];
      animations = [];
      progress = 0;
    }

    function stopTurn() {
      turnEpoch++;
      for (const animation of animations) animation.cancel();
      clearStages();
      drag = null;
      busy = false;
    }

    function clonePage(page) {
      const clone = page.cloneNode(true);
      for (const node of [clone, ...clone.querySelectorAll('*')]) {
        for (const name of ['id', 'aria-labelledby', 'aria-describedby', 'headers']) {
          node.removeAttribute(name);
        }
      }
      return clone;
    }

    function prepare(direction, target) {
      if (!wide.matches || reduced.matches) return;
      let visible = books.filter(book => {
        const box = book.book.getBoundingClientRect();
        return box.bottom > 0 && box.top < innerHeight;
      });
      if (!visible.length) visible = [activeBook()];
      for (const book of visible) {
        const oldPages = book.spreads[current].querySelectorAll(':scope > .page');
        const newPages = book.spreads[target].querySelectorAll(':scope > .page');
        const overlay = document.createElement('div');
        overlay.className = 'turn-stage';
        overlay.setAttribute('aria-hidden', 'true');
        overlay.inert = true;
        overlay.append(clonePage(direction > 0 ? oldPages[0] : newPages[0]),
          clonePage(direction > 0 ? newPages[1] : oldPages[1]));
        const leaf = document.createElement('div');
        leaf.className = 'turn-leaf ' + (direction > 0 ? 'forward' : 'backward');
        const front = document.createElement('div');
        front.className = 'turn-face';
        front.append(clonePage(direction > 0 ? oldPages[1] : oldPages[0]));
        const back = document.createElement('div');
        back.className = 'turn-face turn-back';
        back.append(clonePage(direction > 0 ? newPages[0] : newPages[1]));
        leaf.append(front, back);
        overlay.append(leaf);
        book.book.append(overlay);
        stages.push({book, overlay, leaf});
      }
    }

    function frame(value, direction, book) {
      const physicalDirection = direction * (book.dir === 'rtl' ? -1 : 1);
      const lift = Math.sin(Math.PI * value);
      return {
        transform: `rotateY(${-physicalDirection * value * 180}deg)`,
        boxShadow: `${-physicalDirection * 5 * lift}px 1px ${6 * lift}px rgba(0,0,0,${lift * .12})`,
      };
    }

    function setProgress(value, direction) {
      progress = value;
      for (const stage of stages) Object.assign(stage.leaf.style, frame(value, direction, stage.book));
    }

    async function turn(direction, from = 0, commit = true, fromDrag = false) {
      if (!wide.matches || busy || (!fromDrag && drag?.started)) return;
      if (!fromDrag) drag = null;
      const target = current + direction;
      if (target < 0 || target > lastSpread) return;
      const epoch = turnEpoch;
      if (!stages.length) prepare(direction, target);
      busy = true;
      for (const book of books) { book.previous.disabled = true; book.next.disabled = true; }
      try {
        if (!reduced.matches) {
          const end = commit ? 1 : 0;
          animations = stages.map(stage => stage.leaf.animate(
            [0, .25, .5, .75, 1].map(t => frame(from + (end - from) * t, direction, stage.book)),
            {duration: Math.max(100, Math.abs(end - from) * 420),
              easing: 'cubic-bezier(.25,.65,.2,1)', fill: 'forwards'},
          ));
          await Promise.all(animations.map(animation => animation.finished.catch(() => {})));
        }
        if (epoch === turnEpoch && commit) {
          current = target;
          currentFolio = current * 2 + 1;
        }
      } finally {
        if (epoch === turnEpoch) {
          clearStages();
          busy = false;
          render();
        }
      }
    }

    function jumpTo(number, scroll = true) {
      const folio = clampPage(number);
      stopTurn();
      current = Math.floor((folio - 1) / 2);
      currentFolio = wide.matches ? current * 2 + 1 : folio;
      render();
      if (!scroll) return;
      if (wide.matches) activeBook().book.scrollIntoView({block: 'center'});
      else restoreMobilePoint({folio, offset: 0});
    }

    function readHash() {
      const match = /^#page-?(\d+)$/.exec(location.hash);
      if (match) jumpTo(Number(match[1]));
    }

    function navigateTo(folio) {
      const source = wide.matches ? current * 2 + 1 : captureMobilePoint().folio;
      const sourceHash = '#page-' + source;
      if (location.hash !== sourceHash) history.replaceState(null, '', sourceHash);
      const targetHash = '#page-' + clampPage(folio);
      if (location.hash !== targetHash) history.pushState(null, '', targetHash);
      jumpTo(folio);
    }

    navigation.addEventListener('click', event => {
      const link = event.target.closest('a[data-jump]');
      if (!link || !normalClick(event)) return;
      event.preventDefault();
      navigateTo(Number(link.hash.slice('#page-'.length)));
    });
    window.addEventListener('hashchange', readHash);

    for (const book of books) {
      book.previous.addEventListener('click', () => { setActive(book); turn(-1); });
      book.next.addEventListener('click', () => { setActive(book); turn(1); });
      book.block.addEventListener('focusin', () => setActive(book));
      book.block.addEventListener('click', event => {
        const link = event.target.closest('a.index-entry');
        if (!link || !normalClick(event)) return;
        event.preventDefault();
        setActive(book);
        navigateTo(Number(link.dataset.pageStart));
      });
      book.book.addEventListener('pointerdown', event => {
        setActive(book);
        if (!wide.matches || busy || drag || event.button !== 0 || event.target.closest('a, button')) return;
        const box = book.book.getBoundingClientRect(), x = event.clientX - box.left;
        const edge = Math.min(42, box.width * .12);
        if (event.pointerType === 'mouse' && x > edge && x < box.width - edge) return;
        drag = {book, id: event.pointerId, x: event.clientX, y: event.clientY,
          width: box.width, started: false};
        book.book.setPointerCapture(event.pointerId);
      });
      book.book.addEventListener('pointermove', event => {
        if (busy || !drag || drag.book !== book || drag.id !== event.pointerId) return;
        const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
        if (!drag.started) {
          if (Math.abs(dx) < 10) return;
          if (Math.abs(dy) > Math.abs(dx)) { drag = null; return; }
          const direction = (dx < 0 ? 1 : -1) * (book.dir === 'rtl' ? -1 : 1);
          const target = current + direction;
          if (target < 0 || target > lastSpread) { drag = null; return; }
          drag.started = true;
          drag.direction = direction;
          prepare(direction, target);
          for (const item of books) { item.previous.disabled = true; item.next.disabled = true; }
          window.getSelection()?.removeAllRanges();
        }
        event.preventDefault();
        const physicalDirection = drag.direction * (book.dir === 'rtl' ? -1 : 1);
        setProgress(Math.max(0, Math.min(1, -physicalDirection * dx / (drag.width * .55))), drag.direction);
      });
      const endDrag = cancel => {
        if (!drag || drag.book !== book) return;
        const ended = drag;
        drag = null;
        if (ended.started) turn(ended.direction, progress, !cancel && progress > .22, true);
      };
      book.book.addEventListener('pointerup', () => endDrag(false));
      book.book.addEventListener('pointercancel', () => endDrag(true));
      book.book.addEventListener('lostpointercapture', () => endDrag(true));
    }

    document.addEventListener('keydown', event => {
      if (!wide.matches || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey ||
          event.target.closest?.('input, select, textarea, [contenteditable="true"]')) return;
      const physicalDirection = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
      if (!physicalDirection) return;
      event.preventDefault();
      turn(physicalDirection * (activeBook().dir === 'rtl' ? -1 : 1));
    });

    for (const button of languageButtons) button.addEventListener('click', () => {
      if (wide.matches) return;
      const next = activeIndex + Number(button.dataset.step);
      if (next < 0 || next >= books.length) return;
      const point = captureMobilePoint();
      stopTurn();
      activeIndex = next;
      currentFolio = point.folio;
      current = Math.floor((point.folio - 1) / 2);
      render();
      restoreMobilePoint(point);
    });

    window.addEventListener('scroll', () => {
      if (scrollFrame) return;
      scrollFrame = requestAnimationFrame(() => {
        scrollFrame = 0;
        if (!wide.matches) {
          mobilePoint = captureMobilePoint();
          currentFolio = mobilePoint.folio;
          current = Math.floor((currentFolio - 1) / 2);
          publishPosition();
        } else {
          const center = innerHeight / 2;
          let nearest = activeBook(), distance = Infinity;
          for (const book of books) {
            const box = book.book.getBoundingClientRect();
            const nextDistance = Math.abs((box.top + box.bottom) / 2 - center);
            if (nextDistance < distance) { nearest = book; distance = nextDistance; }
          }
          setActive(nearest);
        }
      });
    }, {passive: true});

    const widths = new WeakMap();
    const resizeObserver = new ResizeObserver(entries => {
      let changed = false;
      for (const entry of entries) {
        if (widths.get(entry.target) !== entry.contentRect.width) {
          widths.set(entry.target, entry.contentRect.width);
          changed = true;
        }
      }
      if (!changed) return;
      const point = {...mobilePoint};
      fitBooks();
      if (!wide.matches) restoreMobilePoint(point);
    });
    for (const book of books) resizeObserver.observe(book.shell);

    wide.addEventListener('change', () => {
      const point = {...mobilePoint};
      stopTurn();
      if (wide.matches) currentFolio = current * 2 + 1;
      render();
      if (wide.matches) activeBook().book.scrollIntoView({block: 'center'});
      else restoreMobilePoint({folio: currentFolio || point.folio, offset: 0});
    });

    root.classList.add('book-ready');
    render();
    for (const book of books) book.book.dataset.ready = 'true';
    root.dataset.ready = 'true';
    readHash();
  }

  window.LangPrintNavigation = Object.freeze({mount});
})();
