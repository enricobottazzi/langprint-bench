# LangPrint Bench — methodology

**Question:** how much space does the same message occupy on a printed page across languages?

Proposed protocol, 22 November 2026. This is a one-day exploratory experiment. No data has been collected yet.

## 1. Scope

Use **100 passages: five in each of 20 domains**, rendered in ten languages. This gives 100 originals, 900 translations and **1,000 text blocks**.

| Language | Dataset / HTML code | Translation API code | Font |
| --- | --- | --- | --- |
| English | `en` | `en` | Noto Sans |
| Arabic | `ar` | `ar` | Noto Sans Arabic |
| Simplified Chinese | `zh-Hans` | `zh-CN` | Noto Sans CJK SC |
| German | `de` | `de` | Noto Sans |
| Hindi | `hi` | `hi` | Noto Sans Devanagari |
| Italian | `it` | `it` | Noto Sans |
| Japanese | `ja` | `ja` | Noto Sans CJK JP |
| Russian | `ru` | `ru` | Noto Sans |
| Spanish | `es` | `es` | Noto Sans |
| Swahili | `sw` | `sw` | Noto Sans |

Swahili adds a Bantu language to the sample. This selection spans several language families and writing systems; it is not a representative sample of the world's languages. See the [UN's Kiswahili overview](https://www.un.org/en/observances/kiswahili-day).

## 2. Corpus and source languages

Do not use English as the source for every passage. That would answer the narrower question of how English originals expand or contract in translation. Translated text can retain features of its source language; [research on translationese](https://aclanthology.org/2020.emnlp-main.6/) shows why original-versus-translated status matters in evaluation.

Instead, use **ten originals per language**, written directly in that language. Each original is a different message; its nine translations provide the matched comparisons.

For a feasible one-day corpus, draft originals with one multilingual generation model and label the corpus as synthetic. Record the model identifier, prompt template, date and edits. Do not translate an English draft and label the result an original in another language. Freeze the corpus before the main translation run.

Use this domain order:

1. Physics
2. Biology
3. Medicine and health
4. Environment and climate
5. Computer science
6. Engineering
7. Mathematics
8. Economics
9. Finance
10. Business and workplace
11. Law
12. Politics and public affairs
13. History
14. Philosophy
15. Psychology
16. News reporting
17. Travel and geography
18. Food and cooking
19. Arts and culture
20. Literary fiction

These are practical content strata, with some overlap between topic and genre.

**Source allocation:** initialize a seeded random generator with seed `42`. For each consecutive pair of domains, freshly shuffle the ten language codes in the table above. Assign the first five to one domain and the other five to the next, one original per assigned language. Save the resulting allocation, rather than relying on the seed alone. Every domain then has five distinct source languages, and every language supplies ten originals overall.

**Passage constraints:** one self-contained prose paragraph, roughly five to seven substantive statements or story events. Use ordinary sentences, with no headings, lists, tables, code, equations or poetry. Give each passage a distinct content brief. Do not impose equal word, character or token counts across languages, and do not select passages based on their rendered area. Record the brief and original text under a stable passage ID.

## 3. Translation

Use **Google Cloud Translation Basic v2, explicitly selecting `model=nmt` and `format=text`**, for all language pairs. Its [language support](https://docs.cloud.google.com/translate/docs/languages) covers the selected languages; the [API reference](https://docs.cloud.google.com/translate/docs/reference/rest/v2/translate) specifies these request fields.

- Set the source and target language explicitly. Retain the original unchanged for its own language row.
- Submit every target request from the original text. Do not chain translations through an English output. The provider's internal routing is outside our control.
- Do not request shortening, length matching or stylistic rewriting. Use no custom glossary.
- Cache the first successful response for each original-text hash, source, target and engine configuration. Retry transport failures, not valid translations whose length looks unusual.
- Retain raw responses, the exact text used for rendering, request settings and timestamps. Document any response decoding or whitespace normalization. Preserve punctuation and script-specific characters.

The hosted NMT model is not an immutable model snapshot. Archived outputs make this dataset reproducible even if later API calls change.

## 4. Typography and measurement

Measure **occupied layout area**: the fixed column width multiplied by the paragraph's rendered height. This includes spaces, line spacing and unused space on the final line. It measures page space allocated to the passage, rather than counting dark ink pixels.

| Setting | Value |
| --- | --- |
| Print reference | A4, 25 mm margins; 160 mm text width |
| Type | Bundled Noto fonts from the table; regular, 12 pt |
| Line height | Fixed 18 pt for every language |
| Alignment | Start-aligned; Arabic right-to-left, all others left-to-right |
| Spacing | Default letter and word spacing; zero paragraph margins, padding and borders |
| Wrapping | Normal language-aware wrapping; hyphenation disabled; no forced word splitting |
| Rendering | One pinned Playwright/Chromium build and operating environment; print media, 100% scale |

Use explicit language and direction attributes. Bundle exact font files, record their hashes and check actual font usage; do not rely on system font substitution. Wait for fonts to finish loading before measurement. Noto provides [script-specific families](https://notofonts.github.io/noto-docs/website/use/), rather than one font that covers everything identically.

Render each paragraph in an unpaginated block with the print settings above. Measure its bounding rectangle, excluding labels and surrounding UI. Convert CSS pixels to physical units using `96 CSS px = 25.4 mm`, as defined by [CSS absolute units](https://www.w3.org/TR/css-values-4/#absolute-lengths):

```text
height_mm = height_css_px × 25.4 / 96
area_cm2 = width_mm × height_mm / 100
```

Save unrounded measurements. Round only for display. This estimates text-block area; it does not measure whole-page counts, pagination or printer output. With fixed width and line height, area changes in whole-line increments, so small differences are coarse.

Equal point size is a reproducible convention, not a guarantee of equal perceived size or readability across scripts. Results describe this typography setup.

## 5. One heatmap

**Rows:** ten languages. **Columns:** twenty domains. Each cell summarizes the five matched passages in that domain.

Normalize within each passage so neither English nor another language supplies the reference:

```text
A[p,l] = area of passage p in language l
G[p]   = geometric mean of A[p,l] across all ten languages
R[p,l] = A[p,l] / G[p]
H[l,d] = geometric mean of R[p,l] across the five passages in domain d
```

Cell colour represents `H[l,d]`, on a diverging scale centred at `1`, with colour distance proportional to `log2(H)`. This treats a doubling and a halving symmetrically. Label the legend in ratios: `1.20×` means 20% more area than the passage-level multilingual geometric reference, aggregated across the domain.

Selecting a cell shows its mean absolute area in cm², sample count and five individual passage ratios, with access to the original and translated text. Keep raw area available because the reference depends on the selected language set. Publish one heatmap, with its settings and a downloadable dataset.

## 6. Quality checks and interpretation

Before the full run, pilot one original from each source language and its translations. Check fonts, Arabic shaping and direction, Hindi marks, CJK wrapping, overflow and clipping. Freeze the typography after this pilot.

Check all records for missing or empty text, failed requests, unexpected language/script, accidental source copying and rendering failures. Treat automatic language checks as flags for review. Inspect at least two translations into each target language, using bilingual review where available and explicitly labelling model-assisted review otherwise. Check preservation of statements, events, numbers and negation. A back-translation alone does not establish fidelity.

Do not silently edit or discard inconvenient results. Log issues and their resolution. If a serious unresolved issue invalidates one version, exclude that passage across all ten languages from the main comparison. Display a domain with fewer than five complete passages as incomplete, rather than substituting a different sample or showing a full-result cell.

Balanced sources reduce English-specific bias; they do not remove translation effects. Each domain contains only five source languages, and original-versus-translated status varies within domain cells. Five passages per domain support an exploratory visualization, not stable language rankings or claims about inherent linguistic efficiency. The source generator, translation engine, corpus and fonts all influence the result.

## 7. Split the work

**Graphical interface:** build a static page with the single heatmap, legend, cell selection, passage inspection, methodology link and figure/data download. Read the experiment export; keep translation and measurement out of the interface. Any fixture data must be clearly marked as a demo.

**Experiment and data collection:** create and freeze the corpus, translate with caching, render in the controlled environment, run checks and export the measurements and cell summaries. Save configuration, corpus provenance, translation responses, font hashes and software versions alongside the results.

Agree on one shared export, `data/results.json`, before either implementation starts:

- `schema_version`, `run_id`, `status` (`demo`, `partial` or `complete`) and run metadata.
- Ordered `languages` and `domains` arrays, plus the typography and engine configuration.
- `passages`: stable ID, domain, source language, original text and source provenance.
- `renderings`: passage ID, language, text, original/translation flag, width and height in mm, area in cm², normalized ratio and quality status.
- `cells`: language, domain, geometric mean ratio, arithmetic mean area in cm², `n`, completeness status and contributing passage IDs. Incomplete cells have null summary values.

The experiment owns these calculations; the interface displays the exported values. Do not present demo or partial output as completed experiment results.

**One-day sequence:** first freeze the protocol, export fields and pilot settings. Then build the interface and run corpus/translation/measurement work in parallel. Finish by checking the integrated heatmap against the underlying records and publishing the figure, data and methodology together.
