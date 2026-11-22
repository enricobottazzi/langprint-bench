# LangPrint Bench

How much space does the same message occupy on a printed page across languages?

## Occupied-page score

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

```python
from score import score

occupied_pages = score(entry)  # entry is a decoded JSON object
```

Only `lang` and `text` affect the result. The scorer uses the fixed layout in
section 3 of [methodology.md](methodology.md). Exact Noto font files are downloaded
on first use and cached in `.cache/fonts/`; a language can be scored offline once
its fonts are cached. Noto Sans Mono supplies missing symbols such as redaction
bars. Passage text stays local. Run checks with `python -m unittest -v test_score`.

## Translation

`translate.py` uses Google Cloud Translation Basic v2 with `model=nmt`, plain
text and explicit source/target languages. It needs only Python's standard
library. It reads `GOOGLE_TRANSLATE_API_KEY` if set, otherwise the macOS Keychain
item with service `langprint-bench.google-translate` and your login account.

```sh
# Inspect the first-passage pilot without reading credentials or calling Google.
python3 translate.py --idx 1 --dry-run

# Translate that original into the other nine languages.
python3 translate.py --idx 1

# Inspect the remaining corpus cost, then run it when ready.
python3 translate.py --all --dry-run
python3 translate.py --all
```

The runner adds translations directly to `data/results.json`, preserving every
original record. A translation keeps the source passage's `idx`, `discipline`,
`title` and `source`; its `lang` is the target language, `text` is the translation
and `original` is `0`. Originals retain `original: 1`. Records are grouped by
language, then `idx`; `(idx, lang)` identifies a unique version. A complete run
contains **200 originals + 1,800 translations = 2,000 records**. Only originals
are sent to Google, so translations are never chained through another language.
Existing original `occupied_pages` measurements are retained; translated versions
are measured separately. Use `--output PATH` to write the combined corpus elsewhere instead.

Each first successful raw response, exact request settings and UTC timestamp
are saved atomically under `data/translation-cache/`, which is ignored by Git.
Keep this local directory with the experiment. A rerun reuses matching cached responses without API calls or
Keychain access; changing the original text or engine settings creates a new
cache key. Successful responses are retained after interruptions, and completed
records are merged into the dataset when a run exits. Reruns do not duplicate
`(idx, lang)` records. The script stops rather than overwrite the corpus if
another process edits it during translation. Returned text is preserved without HTML unescaping or whitespace
normalization. Temporary HTTP 429/5xx and connection failures get at most three
attempts; ambiguous network failures can result in duplicate billable requests.
Run one translation process at a time. Costs printed by dry runs are for uncached
input characters at $20/million, before monthly credits, taxes or currency
conversion. Run offline checks with `python3 -m unittest -v test_translate`.

Translations are retained as returned by the engine, without semantic quality
review or manual corrections. Technical checks cover nonempty responses,
supported languages, complete coverage and record structure.
