# LangPrint Bench — methodology

## 1. Source data

Collect 200 human-authored passages across ten languages and ten domains, with two originals per language/domain pair. Each passage contains roughly 10–20 consecutive sentences from a work first published between 2000 and 2020. Verify that it was originally written in the source language, preserve its wording and record its title and source URL in [data/results.json](data/results.json).

## 2. Translate

Translate each original directly into the other nine languages using Google Cloud Translation Basic v2 (`model=nmt`). Keep the returned text without manual corrections. This produces 2,000 texts: 200 originals and 1,800 translations. Translation quality is not manually reviewed.

## 3. Score

Render each text with [score.py](score.py), using the same layout as the book: a 365 px text width, 12 px Noto fonts appropriate to each script, and 21 lines per page. Count body-text lines only, excluding titles, headers and page numbers.

```text
occupied pages = rendered lines / 21
```

## 4. Heatmap

Normalize each version against the same passage's ten-language average, then average the ratios for each language/domain cell:

```text
passage average = sum of occupied pages across its 10 language versions / 10
passage ratio = occupied pages / passage average
heatmap score = sum of the 20 passage ratios in a language/domain cell / 20
```

[heatmap.py](heatmap.py) generates the heatmap with languages as rows and domains as columns.

A value of 1 is the multilingual average; 1.2 means 20% more space, and 0.8 means 20% less. Results describe this corpus, translation engine and typography.
