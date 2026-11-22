"""Translate corpus passages with Google NMT, saving the first successful output.

Uses only the Python standard library. Credentials come from
GOOGLE_TRANSLATE_API_KEY or the macOS Keychain item
langprint-bench.google-translate. By default translations are merged into
results.json with their source idx and original: 0, preserving all originals.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
ENDPOINT = "https://translation.googleapis.com/language/translate/v2"
LANGUAGES = ("en", "ar", "zh-Hans", "de", "hi", "it", "ja", "ru", "es", "sw")
KEYCHAIN_SERVICE = "langprint-bench.google-translate"
FIELDS = ("idx", "lang", "discipline", "title", "source", "text", "original")


def request_body(entry: dict, target: str) -> dict:
    def api_language(lang: str) -> str:
        return "zh-CN" if lang == "zh-Hans" else lang

    return {
        "q": [entry["text"]],
        "source": api_language(entry["lang"]),
        "target": api_language(target),
        "model": "nmt",
        "format": "text",
    }


def cache_key(body: dict) -> str:
    config = {"endpoint": ENDPOINT, "request": body}
    return hashlib.sha256(json.dumps(
        config, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def translated_text(response: dict) -> str:
    try:
        translations = response["data"]["translations"]
        if not isinstance(translations, list) or len(translations) != 1:
            raise ValueError
        text = translations[0]["translatedText"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError
        model = translations[0].get("model", "nmt")
        if model != "nmt":
            raise ValueError
        return text
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise RuntimeError("API response must contain one nonempty NMT translation.") from error


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_cache(directory: Path, body: dict) -> dict | None:
    path = directory / (cache_key(body) + ".json")
    if not path.exists():
        return None
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved["endpoint"] != ENDPOINT or saved["request"] != body:
            raise ValueError("Request does not match cache key")
        translated_text(saved["response"])
        return saved
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        raise RuntimeError(f"Invalid translation cache: {path}") from error


def get_api_key() -> str:
    key = os.environ.get("GOOGLE_TRANSLATE_API_KEY", "").strip()
    if not key and sys.platform == "darwin":
        result = subprocess.run(
            ["security", "find-generic-password", "-a", getpass.getuser(),
             "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode == 0:
            key = result.stdout.strip()
    if not key:
        raise RuntimeError(
            "No API key found. Set GOOGLE_TRANSLATE_API_KEY or save the key "
            f"in macOS Keychain with service {KEYCHAIN_SERVICE}."
        )
    return key


def call_api(body: dict, api_key: str) -> dict:
    request = Request(
        ENDPOINT, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8",
                 "X-Goog-Api-Key": api_key}, method="POST",
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
            translated_text(result)
            return result
        except HTTPError as error:
            status = error.code
            detail = ""
            try:
                message = json.loads(error.read().decode("utf-8"))["error"]["message"]
                if isinstance(message, str):
                    detail = " " + message.replace(api_key, "[redacted]")[:500]
            except (ValueError, KeyError, TypeError, UnicodeError):
                pass
            error.close()
            if status not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(
                    f"Translation API returned HTTP {status}.{detail} Check the API key, "
                    "API enablement, billing and quotas in Google Cloud Console."
                ) from None
        except (URLError, TimeoutError, ConnectionError):
            if attempt == 2:
                raise RuntimeError("Translation request failed after three attempts.") from None
        except (ValueError, UnicodeError):
            raise RuntimeError("Translation API returned invalid JSON; response not cached.") from None
        print(f"Temporary API failure; retrying ({attempt + 2}/3).", file=sys.stderr)
        time.sleep(2 ** attempt)
    raise RuntimeError("Translation request did not complete.")


def load_corpus(path: Path) -> tuple[list[dict], list[dict], bytes]:
    source_bytes = path.read_bytes()
    records = json.loads(source_bytes)
    if not isinstance(records, list):
        raise ValueError("Input must be a JSON array.")
    originals, seen, versions = [], set(), set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each corpus entry must be a JSON object.")
        if (not all(field in record for field in FIELDS)
                or type(record["idx"]) is not int
                or type(record["original"]) is not int
                or record["original"] not in (0, 1)
                or record["lang"] not in LANGUAGES
                or not isinstance(record["text"], str)
                or not record["text"].strip()):
            raise ValueError("Entries need integer IDs, original 0/1, supported languages and nonempty text.")
        pair = record["idx"], record["lang"]
        if pair in versions:
            raise ValueError(f"Duplicate idx/language pair: {pair}.")
        versions.add(pair)
        if record["original"] == 0:
            continue
        if record["idx"] in seen:
            raise ValueError("Original passage IDs must be unique.")
        seen.add(record["idx"])
        originals.append(record)
    if not originals:
        raise ValueError("Input contains no originals.")
    if any(record["idx"] not in seen for record in records):
        raise ValueError("Every translation needs an original with the same idx.")
    return records, originals, source_bytes


def export_translations(originals: list[dict], cached: dict) -> list[dict]:
    rows = []
    for target in LANGUAGES:
        for entry in originals:
            if target == entry["lang"]:
                continue
            saved = cached.get(cache_key(request_body(entry, target)))
            if saved is not None:
                row = {field: entry[field] for field in FIELDS}
                row.update(lang=target, text=translated_text(saved["response"]), original=0)
                rows.append(row)
    return rows


def run(input_path: Path, output_path: Path | None, cache_dir: Path,
        idx: int | None = None, dry_run: bool = False) -> int:
    output_path = input_path if output_path is None else output_path
    records, originals, source_bytes = load_corpus(input_path)
    selected = originals if idx is None else [e for e in originals if e["idx"] == idx]
    if not selected:
        raise ValueError(f"No original with idx={idx}.")

    cached, pending = {}, []
    for entry in originals:
        for target in LANGUAGES:
            if target == entry["lang"]:
                continue
            body = request_body(entry, target)
            saved = read_cache(cache_dir, body)
            if saved is not None:
                cached[cache_key(body)] = saved
            elif idx is None or entry["idx"] == idx:
                pending.append((entry, target, body))

    chars = sum(len(entry["text"]) for entry, _, _ in pending)
    print(f"Selected {len(selected)} original(s); {len(pending)} uncached translations; "
          f"{chars:,} input characters.")
    print(f"Gross API cost: ${chars * 20 / 1_000_000:.4f}, before monthly credits and tax.")
    if dry_run:
        return 0

    # Authenticate only when there is work: a cached rerun needs no credentials.
    api_key = get_api_key() if pending else None
    try:
        for number, (entry, target, body) in enumerate(pending, 1):
            print(f"[{number}/{len(pending)}] idx={entry['idx']} {entry['lang']} -> {target}",
                  flush=True)
            response = call_api(body, api_key)
            saved = {
                "endpoint": ENDPOINT, "request": body,
                "received_at": datetime.now(timezone.utc).isoformat(),
                "response": response,
            }
            key = cache_key(body)
            atomic_json(cache_dir / (key + ".json"), saved)
            cached[key] = saved
    finally:
        # Merge successes even if a later request fails. A changed input must not
        # be overwritten; successful API responses remain available in the cache.
        if input_path.read_bytes() != source_bytes:
            raise RuntimeError("Input changed during translation; cached responses were kept. "
                               "Rerun to merge them into the updated corpus.")
        versions = {(row["idx"], row["lang"]): row for row in records}
        for row in export_translations(originals, cached):
            versions[row["idx"], row["lang"]] = row
        rows = sorted(versions.values(), key=lambda row: (LANGUAGES.index(row["lang"]), row["idx"]))
        atomic_json(output_path, rows)
        translations = sum(row["original"] == 0 for row in rows)
        print(f"Saved {len(originals)} original(s) + {translations} translation(s) to {output_path}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--idx", type=int, help="Translate one original passage ID.")
    selector.add_argument("--all", action="store_true", help="Translate every original (billable).")
    parser.add_argument("--input", type=Path, default=ROOT / "data/results.json")
    parser.add_argument("--output", type=Path,
                        help="Write the combined corpus here instead of updating --input in place.")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "data/translation-cache")
    parser.add_argument("--dry-run", action="store_true", help="Show pending work without API calls.")
    args = parser.parse_args()
    try:
        return run(args.input, args.output, args.cache_dir, args.idx, args.dry_run)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Stopped; successful translations are cached. Rerun to resume.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
