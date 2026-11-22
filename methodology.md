# LangPrint Bench — methodology

**Question:** how much printed page space does the same message occupy across languages?

## 1. Corpus

`data/results.json` contains **200 original passages**: **20 per source language and two per source-language/domain pair**. Each original is translated directly into the other nine languages. The complete dataset contains **200 originals and 1,800 translations: 2,000 texts**, with 200 versions in each target language.

**Languages, in index order:** English (`en`), Arabic (`ar`), Simplified Chinese (`zh-Hans`), German (`de`), Hindi (`hi`), Italian (`it`), Japanese (`ja`), Russian (`ru`), Spanish (`es`) and Swahili (`sw`).

**Domains, in index order:** fiction/stories, news, food/cooking, health, travel/places, sports, work/money, nature/environment, science/technology, and arts/culture.

### Sourcing

Select roughly **10–20 complete, substantive sentences of contiguous prose** from each of two different documents per language/domain. Headings, captions, salutations, fragments and list labels do not satisfy the sentence minimum. Do not stitch together nonadjacent ordinary prose. Different, nonoverlapping chapters of a larger work may supply different domains; distinct anthology stories count as separate works. Independently authored and titled wiki articles count as separate documents within a shared cookbook; the cookbook still counts as one source family.

Works must have been **first published in 2000–2020 inclusive**. Check original publication or speech dates, printed journal issues, edition credits and native creation histories. Reprints, repository uploads and `dateModified` do not establish first publication. Any uncertain first-publication interval must fall wholly within the window. **Later web edits are allowed**; historical copies corroborate provenance and wording rather than imposing a separate last-edit cutoff.

Search publisher and author sites, institutional archives, native-language community histories and open journals. Read the actual source before selecting its excerpt. Prefer primary texts with reuse terms that allow the planned translations; reject explicitly translated articles, uncertain originals, inaccessible or unreliable text, and list-heavy candidates. Website language alone is insufficient.

To reduce concentration, use **at least four source families per language**, with **no family providing more than eight passages (40%)** and **no identified individual writer or speaker providing more than four (20%)**. A family means a publisher, institution or editorial collection. Group mirrors with their underlying source, and journal articles on CyberLeninka together conservatively. Wikinews, Wikibooks and Wikivoyage are separate editorial collections; this does not cap the entire Wikimedia ecosystem at 40%.

The resulting source inventory is:

| Language | Sources used (passage counts) |
| --- | --- |
| English | [Cory Doctorow](https://craphound.com/overclocked/) stories (2); [Obama White House archive](https://obamawhitehouse.archives.gov/) (4); [NASA](https://www.nasa.gov/) (2); [NIH News in Health](https://newsinhealth.nih.gov/) (4); [English Wikivoyage](https://en.wikivoyage.org/) (2); [Distill](https://distill.pub/) (2); [PLOS](https://journals.plos.org/) (2); [The Public Domain Review](https://publicdomainreview.org/) (2). |
| Arabic | [SyriaUntold](https://syriauntold.com/) narratives, reporting and features (8); [EIPR](https://eipr.org/) institutional texts and signed staff essays, including author reprints (8); [An-Najah University journal](https://journals.najah.edu/) original sports studies (2); [Al-Academy, University of Baghdad](https://jcofarts.uobaghdad.edu.iq/) original arts criticism (2). |
| Chinese | [Chinese Wikinews](https://zh.wikinews.org/) native reports (6); [SCP-CN](https://scp-wiki-cn.wikidot.com/) originals (2); [Taiwan agriculture/forestry publications](https://kmweb.moa.gov.tw/) (8); original Chinese educational essays from [NTU ScienceOnline's university archive](https://case.ntu.edu.tw/highscope/all-posts-index.html) (4). Explicitly translated entries in that archive were excluded. |
| German | [Arne Babenhauserheide](https://www.draketo.de/) stories (2); [German Wikinews](https://de.wikinews.org/) (8); [Wikibooks cookbook](https://de.wikibooks.org/) (2); [Robert Koch-Institut](https://edoc.rki.de/) studies (2); [Wikivoyage](https://de.wikivoyage.org/) (2); [Geographica Helvetica](https://gh.copernicus.org/) (2); AVINUS/ffk Journal (1); [Musica Docta](https://musicadocta.unibo.it/) (1). |
| Hindi | Room to Read and Pratham Books Hindi stories, checked against [StoryWeaver](https://storyweaver.org.in/) original/translation metadata (2); [India Water Portal](https://hindi.indiawaterportal.org/) signed Hindi writing (8); Unmukt's CC0 blogs (4); original Hindi JARSSC papers (3); native Hindi Wikinews (1); original *Mann Ki Baat* broadcasts through [PMIndia](https://www.pmindia.gov.in/hi/) and [PIB](https://www.pib.gov.in/) (2 different episodes). |
| Italian | Wu Ming novels via [Liber Liber](https://www.liberliber.eu/) (2); [Italian Wikinews](https://it.wikinews.org/) (8); [Wikibooks](https://it.wikibooks.org/) (1); [Scenario/Aniarti](https://scenario.aniarti.it/) original nursing studies (2); [Wikivoyage](https://it.wikivoyage.org/) (2); [Sergio Bellucci](https://www.sergiobellucci.it/) essays (2); University of Bologna's [Musica Docta](https://musicadocta.unibo.it/) (2) and [Umanistica Digitale](https://umanisticadigitale.unibo.it/) (1). The Bologna journals are grouped conservatively as one family. |
| Japanese | [SCP-JP](https://scp-jp.wikidot.com/) originals (2); [Japanese Wikinews](https://ja.wikinews.org/) (2); MAFF chef interview (1); MEXT reports/plans (5), MHLW reports (3), MLIT reports (2), including [National Diet Library WARP](https://warp.ndl.go.jp/) copies; Ecological Society of Japan field study (1); Association for Natural Language Processing papers (2); Japan Society for Digital Archive papers (2). J-STAGE is a host for five papers from three societies. |
| Russian | Native Russian SCP stories (2); [Russian Wikinews](https://ru.wikinews.org/) (4); [NEWSru](https://www.newsru.com/) food reporting/explanations (2); original Russian journal papers via [CyberLeninka](https://cyberleninka.ru/) (8); [Wikivoyage](https://ru.wikivoyage.org/) (2); [Teplitsa of Social Technologies](https://te-st.org/) original interviews (2). |
| Spanish | Two distinct stories from *Violetas para Luisa y otros cuentos* ([UAEMex edition](https://ri.uaemex.mx/handle/20.500.11799/22494)); [Spanish Wikinews](https://es.wikinews.org/) (8); [Fondo Gastronómico](https://fondogastronomico.blogspot.com/) (2); [Mundo por Libre](https://www.mundoporlibre.com/) (2); MEDISAN (1); [Salud Colectiva](https://revistas.unla.edu.ar/saludcolectiva/) (1); [Ingeniería e Investigación](https://revistas.unal.edu.co/index.php/ingeinv/) (2); [Aisthesis](https://revistaaisthesis.uc.cl/) (2). |
| Swahili | [African Storybook](https://www.africanstorybook.org/) originals (3); native Swahili [Global Voices](https://sw.globalvoices.org/) reports (3); [MAELEZO](https://blog.maelezo.go.tz/) local reporting/features (6); original Swahili scholarship through Editon (4), UDSM journals (3) and East African Scholars Journal of Education, Humanities and Literature (1; repository copy at Embu). All 20 are different works with 19 distinct bylines; no Magufuli speeches remain. |

### Verification and extraction

Establish original-language composition using translation-direction credits, author accounts, native creation/drafting histories, firsthand interviews, original research reports or institutional authorship. Examples include StoryWeaver's original-story links; English counterparts explicitly translated from Swahili; Hindi broadcasts labelled “English rendering” in their English versions; and named translation credits in the English counterparts of the selected German RKI articles. For community texts, inspect initial drafts and imports: a maintenance editor or importing account is not necessarily the author. Where explicit direction evidence is unavailable, the decision rests on positive primary authorship and composition context, not language identification alone. Bilingual abstracts alone do not establish translation direction.

Copy consecutive prose. Remove markup, navigation, headings, captions, duplicate pullquotes, footnotes and page furniture; retain substantive quotations and ordinary prose embedded in tables. Check PDF columns, page joins and scans against rendered page images. Join layout word breaks, preserve lexical hyphens, and normalize artificial extraction spacing. Preserve source wording, punctuation and spelling; do not silently rewrite awkward or dated prose. For Arabic scans, compare visible text with available text layers/OCR and resolve differences against the printed page. Automated extraction can omit quotation boxes or insert footers, so successful downloading alone is not verification.

Traditional Chinese prose is converted to Simplified Chinese through MediaWiki `zh-hans` or OpenCC `t2s`. This is script conversion, not language translation; titles retain the source script. Remove mathematical display formatting only when preserving the same visible literal value as plain text.

Fetch `title` from the actual article, work or chapter heading rather than an invented summary or truncated search/SEO title. `source` is an absolute URL identifying the publication, frozen revision or archived edition. Check source correspondence and sentence boundaries manually, then run programmatic checks for UTF-8, required fields, integer `original`, unique IDs, language, dates and all 100 balanced language/domain cells. Compare normalized titles as well as passages.

Duplicate screening uses normalized full texts, within-language character 5-grams (Jaccard ≥ 0.20 or containment ≥ 0.35 for review), and shared runs of at least 80 letters/digits. Review candidates against their sources; no selected excerpts may overlap. The final 22 November 2026 audit found **no duplicate titles, exact/near-duplicate passages or shared 80-character runs**. Selected publication dates span **2000–2020**. Publication provenance is assessed without an AI detector.

### Organization and limits

Each entry has only **`idx`, `lang`, `discipline`, `title`, `source`, `text`, `original`**. The array is grouped by **language**, then `idx`. IDs **1–200** identify the source passages, not array positions. Every language version of a passage shares its original's `idx`; **`(idx, lang)` is unique**. Source entries have integer **`original: 1`** and translations have integer **`original: 0`**. A translation keeps its source's `discipline`, `title` and `source`, changing only `lang`, `text` and `original`. The original record is preserved.

Language and topic counts are exactly balanced; genres, years and countries are not statistically balanced. The source-family limits reduce publisher/author dominance without making this a representative sample of each language. Japanese retains ten ministry-report passages and reuses distinct, nonoverlapping chapters from MEXT and MHLW annual volumes. German cookbook passages share a book; the Spanish stories share an anthology. German uses 12 passages and Italian 11 from three Wikimedia editorial collections each; their combined platform share therefore exceeds the individual-collection cap. Russian retains eight scholarly passages, Hindi eight India Water Portal texts, and Arabic eight each from SyriaUntold and EIPR.

“Stories” includes documentary narratives; food includes production and safety, and travel includes place/transport descriptions. Modern criticism may discuss older works; the date criterion applies to the selected modern composition. Reuse terms vary, including attribution, noncommercial and share-alike obligations; the corpus has no implied common licence. Measurements describe this selected sample under the stated typography, rather than all writing in these languages.

## 2. Translation

Use **Google Cloud Translation Basic v2**, explicitly selecting **`model=nmt`**, **`format=text`**, and the source and target languages. The dataset uses `zh-Hans`; requests use Google's `zh-CN` code. Translate each original's body text directly into the other nine languages, keeping the original unchanged for its own language. Do not shorten, rewrite or manually correct the returned translations, and do not translate source titles or other metadata.

[`translate.py`](translate.py) reads the API key from `GOOGLE_TRANSLATE_API_KEY` or the macOS Keychain service `langprint-bench.google-translate`. It requires an explicit `--idx ID` or `--all` selection; `--dry-run` reports uncached work and gross character cost without reading credentials or making API calls. The default output is the combined `data/results.json`; `--output PATH` can select a different combined output file.

Cache each first successful raw response, exact request and UTC timestamp under `data/translation-cache/`, keyed by a SHA-256 hash of the endpoint, original text, language pair and engine settings. Reuse matching cached responses when resuming. Preserve returned text exactly, without HTML unescaping or whitespace normalization. Temporary HTTP 429/5xx and connection failures receive at most three attempts; ambiguous network failures can cause duplicate billed requests. Invalid or empty responses are not cached.

Merge completed translations into the dataset atomically on exit, including when a later request fails. Retain previous records and replace matching `(idx, lang)` versions without duplicates. If another process edits the input during translation, keep the cached responses and stop before overwriting that edit. Run one translation process at a time.

**No semantic translation review is performed for this exploratory run.** Retain the engine's outputs, including any meaning errors. Technical checks verify response structure, nonempty text and complete language coverage. Translation errors therefore remain a limitation of the comparison.

## 3. Measurement: `score.py` and fractional pages

[`score.py`](score.py) implements the occupied-page measurement. Call it separately for each original or translated passage:

```python
from score import score

occupied_pages = score(entry)
```

`entry` is a decoded JSON object. Only **`lang` and `text`** affect the result; the function ignores titles and other metadata and returns an **unrounded float**. Installation instructions are in the [README](README.md#occupied-page-score).

### Reference layout

Render locally in headless Chromium through Playwright, using the paperback reader's fixed layout:

- Page: **465 × 624 CSS pixels**, with **50 px side margins**, 40 px top padding, 52 px bottom padding and a 47 px running-title reservation. The usable body is **365 × 485 px**.
- Regular **12 px** type, weight 400 and **1.85 line height** (nominally 22.2 px), with font synthesis and optical sizing disabled. Use Noto Serif for English, German, Italian, Russian, Spanish and Swahili; Noto Naskh Arabic for Arabic; Noto Serif Devanagari for Hindi; Noto Serif SC for Chinese; and Noto Serif JP for Japanese.
- One column, start-aligned, with Arabic right-to-left and the other languages left-to-right. Use normal browser wrapping, without automatic hyphenation or forced word breaking.
- No extra paragraph spacing. Indent each paragraph's first line by **1.3 em (15.6 px)**, except the first paragraph on each rendered page, which is unindented.

Exact font files and SHA-256 checksums are pinned in `score.py`. They are downloaded and verified on first use, then cached. Other-script fonts fall back to Noto Serif for uncovered characters, and every language also has Noto Sans Mono for symbols. Unintended system-font fallback causes an error. Wait for fonts to load before measuring, and use the same pinned dependencies and Chromium version for comparable runs.

### Pagination and score

1. Treat one or more newline characters as a paragraph boundary, trim paragraphs and discard empty ones. Ordinary whitespace within a paragraph collapses according to normal browser layout.
2. Fill pages in reading order. Use whitespace-delimited tokens for most languages and `Intl.Segmenter` word segments for Japanese and Chinese. For each paragraph, a binary search finds the largest token prefix whose rendered block fits; any remaining text continues on the next page. Chromium determines the actual line wrapping.
3. Keep the reader's **2 px fitting allowance**: text must fit within **483 px** of the 485 px body. The fixed scoring capacity is **21 rendered lines per page**.
4. Measure the actual height of one rendered line after the fonts load, including browser subpixel rounding. Divide each page's body-block height by that line height and round to the nearest integer to recover its rendered line count. Sum those counts and calculate:

```text
occupied pages = total rendered lines / 21
```

This counts rendered lines at the fixed width, font and line spacing. Each line contributes **1/21 of a page**, regardless of how much horizontal space it fills. Titles, running headers, page numbers, blank paragraphs and unused page-bottom space do not count. A full **21-line page scores exactly 1.00**; **22 lines score 22/21 ≈ 1.0476**, and **42 lines score exactly 2.00**. Browser wrapping determines the line count, rather than the number of source newline characters. The returned float is not rounded to whole pages.

Whitespace-only text returns **0.0**. Invalid inputs, missing or corrupt fonts, unsupported glyphs requiring system fonts, or text that clips horizontally or vertically raise errors rather than producing a score. The function does not write scores into `data/results.json`; retain measurements separately for the normalization in step 4.

Run `python -m unittest -v test_score` after installing dependencies to check multilingual rendering, pagination, repeatability, metadata exclusion, font coverage and overflow handling. Smaller reader screens should scale the reference pages without reflowing the measured text.

## 4. Heatmap and checks

Produce **one heatmap**: languages on the y-axis, domains on the x-axis. Normalize each passage against the average occupied pages of its ten language versions, then average the ratios within each domain:

```text
passage ratio = occupied pages / average pages across its ten versions
heatmap cell = average passage ratio across the domain's usable passages (normally 20)
```

**1.00 = multilingual average; 1.20 = 20% more space; 0.80 = 20% less.** This controls for passage length and gives each passage equal weight. Use one shared colour scale centred at 1, and retain raw page counts. Scores are relative to the selected ten languages.

Check for missing or empty translations, duplicate `(idx, lang)` pairs, missing glyphs and clipped text. Require all ten technically usable versions of each passage; semantic translation review is outside this run's scope. If a technical problem cannot be resolved, exclude that passage across **all languages** before calculating ratios and averages. Mark the affected domain as incomplete and show its remaining passage count. Treat results as an exploratory comparison under these typography settings.

## 5. Work split

- **Interface:** display the heatmap and let users inspect the passages.
- **Experiment:** curate `data/results.json`, translate the originals, render all language versions and export raw page counts, passage ratios and heatmap cell averages.
