"""Offline checks: no real credentials, network calls or paid translations."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import translate


def response(text):
    return {"data": {"translations": [{"translatedText": text, "model": "nmt"}]}}


class TranslationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "results.json"
        self.output = self.root / "translations.json"
        self.cache = self.root / "cache"
        self.entry = {"idx": 1, "lang": "en", "discipline": "fiction/stories",
                      "title": "Original title", "source": "https://example.com/story",
                      "text": "First statement.\n\nSecond statement.", "original": 1}
        self.source.write_text(json.dumps([self.entry]), encoding="utf-8")

    def run_script(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return translate.run(self.source, self.output, self.cache, **kwargs)

    def run_in_place(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return translate.run(self.source, self.source, self.cache, **kwargs)

    def test_request_and_cache_identity(self):
        body = translate.request_body(self.entry, "zh-Hans")
        self.assertEqual(body, {"q": [self.entry["text"]], "source": "en",
                                "target": "zh-CN", "model": "nmt", "format": "text"})
        self.assertNotEqual(translate.cache_key(body), translate.cache_key({**body, "model": "other"}))
        self.assertNotEqual(translate.cache_key(body), translate.cache_key({**body, "q": ["Changed"]}))

    def test_live_run_then_cached_rerun_preserves_original(self):
        before = self.source.read_bytes()
        with patch.object(translate, "get_api_key", return_value="secret"), \
                patch.object(translate, "call_api", side_effect=lambda b, k: response(b["target"] + " text")) as api:
            self.run_script(idx=1)
            self.assertEqual(api.call_count, 9)
        rows = json.loads(self.output.read_text())
        self.assertEqual(len(rows), 10)
        originals = [r for r in rows if r["original"] == 1]
        translations = [r for r in rows if r["original"] == 0]
        self.assertEqual(originals, [self.entry])
        self.assertEqual({r["lang"] for r in translations}, set(translate.LANGUAGES) - {"en"})
        self.assertTrue(all(r["idx"] == 1 for r in translations))
        self.assertTrue(all(set(r) == set(translate.FIELDS) for r in rows))
        self.assertTrue(all(r["title"] == self.entry["title"] and r["source"] == self.entry["source"] for r in rows))
        self.assertEqual(self.source.read_bytes(), before)
        with patch.object(translate, "get_api_key", side_effect=AssertionError("Must not access credentials")), \
                patch.object(translate, "call_api", side_effect=AssertionError("Must not call API")):
            self.run_script(idx=1)
        self.assertEqual(json.loads(self.output.read_text()), rows)

    def test_partial_failure_saves_and_resumes(self):
        with patch.object(translate, "get_api_key", return_value="secret"), \
                patch.object(translate, "call_api", side_effect=[response("Arabic"), RuntimeError("Stopped")]):
            with self.assertRaisesRegex(RuntimeError, "Stopped"):
                self.run_script(idx=1)
        partial = json.loads(self.output.read_text())
        self.assertEqual(len(partial), 2)
        self.assertEqual([r for r in partial if r["original"] == 1], [self.entry])
        with patch.object(translate, "get_api_key", return_value="secret"), \
                patch.object(translate, "call_api", return_value=response("Resumed")) as api:
            self.run_script(idx=1)
            self.assertEqual(api.call_count, 8)
        self.assertEqual(len(json.loads(self.output.read_text())), 10)

    def test_dry_run_never_authenticates_or_writes(self):
        with patch.object(translate, "get_api_key", side_effect=AssertionError), \
                patch.object(translate, "call_api", side_effect=AssertionError):
            self.run_script(idx=1, dry_run=True)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.cache.exists())

    def test_new_source_does_not_reuse_old_translations(self):
        with patch.object(translate, "get_api_key", return_value="secret"), \
                patch.object(translate, "call_api", return_value=response("First")):
            self.run_script(idx=1)
        self.entry["text"] += " Third statement."
        self.source.write_text(json.dumps([self.entry]), encoding="utf-8")
        with patch.object(translate, "get_api_key", return_value="secret"), \
                patch.object(translate, "call_api", return_value=response("Updated")) as api:
            self.run_script(idx=1)
            self.assertEqual(api.call_count, 9)
        rows = json.loads(self.output.read_text())
        self.assertEqual([r for r in rows if r["original"] == 1], [self.entry])
        self.assertTrue(all(r["text"] == "Updated" for r in rows if r["original"] == 0))

    def test_other_passages_survive_export(self):
        second = {**self.entry, "idx": 2, "text": "A different passage."}
        self.source.write_text(json.dumps([self.entry, second]), encoding="utf-8")
        with patch.object(translate, "get_api_key", return_value="secret"), \
                patch.object(translate, "call_api", return_value=response("Translated")):
            self.run_script(idx=1)
            self.run_script(idx=2)
        rows = json.loads(self.output.read_text())
        self.assertEqual(len(rows), 20)
        self.assertEqual({r["idx"] for r in rows}, {1, 2})

    def test_in_place_replay_is_idempotent_and_does_not_chain_translations(self):
        with patch.object(translate, "get_api_key", return_value="secret"), \
                patch.object(translate, "call_api", return_value=response("Translated")) as api:
            self.run_in_place(idx=1)
            self.assertEqual(api.call_count, 9)
        rows = json.loads(self.source.read_text())
        self.assertEqual(len(rows), 10)
        self.assertEqual([r for r in rows if r["original"] == 1], [self.entry])
        self.assertEqual(len({(r["idx"], r["lang"]) for r in rows}), 10)
        self.assertEqual([r["lang"] for r in rows], list(translate.LANGUAGES))
        with patch.object(translate, "get_api_key", side_effect=AssertionError("No credentials needed")), \
                patch.object(translate, "call_api", side_effect=AssertionError("No additional API calls")):
            self.run_in_place()
        self.assertEqual(json.loads(self.source.read_text()), rows)

    def test_in_place_failure_keeps_originals_and_completed_translations(self):
        with patch.object(translate, "get_api_key", return_value="secret"), \
                patch.object(translate, "call_api", side_effect=[response("Arabic"), RuntimeError("Stopped")]):
            with self.assertRaisesRegex(RuntimeError, "Stopped"):
                self.run_in_place(idx=1)
        rows = json.loads(self.source.read_text())
        self.assertEqual([r for r in rows if r["original"] == 1], [self.entry])
        self.assertEqual(len([r for r in rows if r["original"] == 0]), 1)
        with patch.object(translate, "get_api_key", return_value="secret"), \
                patch.object(translate, "call_api", return_value=response("Resumed")) as api:
            self.run_in_place(idx=1)
            self.assertEqual(api.call_count, 8)
        self.assertEqual(len(json.loads(self.source.read_text())), 10)

    def test_subset_run_preserves_existing_translation_without_cache(self):
        second = {**self.entry, "idx": 2, "lang": "de", "text": "An original German passage."}
        previous = {**second, "lang": "ja", "original": 0, "text": "Previously translated text."}
        self.source.write_text(json.dumps([self.entry, second, previous]), encoding="utf-8")
        with patch.object(translate, "get_api_key", return_value="secret"), \
                patch.object(translate, "call_api", return_value=response("New translation")) as api:
            self.run_in_place(idx=1)
            self.assertEqual(api.call_count, 9)
        rows = json.loads(self.source.read_text())
        self.assertEqual(len(rows), 12)
        self.assertIn(previous, rows)
        self.assertIn(self.entry, rows)
        self.assertIn(second, rows)
        self.assertEqual(len({(r["idx"], r["lang"]) for r in rows}), len(rows))
        order = [translate.LANGUAGES.index(r["lang"]) for r in rows]
        self.assertEqual(order, sorted(order))

    def test_external_input_edit_is_not_overwritten_and_cache_survives(self):
        changed = {**self.entry, "title": "Edited elsewhere while translating"}
        external_bytes = (json.dumps([changed]) + "\n").encode("utf-8")

        def external_edit(body, api_key):
            self.source.write_bytes(external_bytes)
            return response("Completed translation")

        with patch.object(translate, "get_api_key", return_value="secret"), \
                patch.object(translate, "call_api", side_effect=external_edit):
            with self.assertRaises(RuntimeError):
                self.run_in_place(idx=1)
        self.assertEqual(self.source.read_bytes(), external_bytes)
        self.assertTrue(list(self.cache.glob("*.json")))

    def test_cli_defaults_output_to_selected_input(self):
        with patch.object(translate.sys, "argv", ["translate.py", "--idx", "1", "--input", str(self.source),
                                                "--cache-dir", str(self.cache)]), \
                patch.object(translate, "get_api_key", return_value="secret"), \
                patch.object(translate, "call_api", return_value=response("Translated")), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(translate.main(), 0)
        self.assertEqual(len(json.loads(self.source.read_text())), 10)
        self.assertFalse(self.output.exists())

    def test_invalid_responses_rejected(self):
        for result in ({}, {"data": {"translations": []}}, response(" "),
                       {"data": {"translations": [{"translatedText": "ok", "model": "other"}]}}):
            with self.subTest(result=result), self.assertRaises(RuntimeError):
                translate.translated_text(result)
        self.assertEqual(translate.translated_text(response(" A &amp; B\n")), " A &amp; B\n")

    def test_key_in_header_and_forbidden_not_retried(self):
        error = HTTPError(translate.ENDPOINT, 403, "Forbidden", {}, io.BytesIO())
        with patch.object(translate, "urlopen", side_effect=error) as opener, \
                patch.object(translate.time, "sleep") as sleep:
            with self.assertRaisesRegex(RuntimeError, "HTTP 403") as caught:
                translate.call_api(translate.request_body(self.entry, "it"), "secret-value")
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, translate.ENDPOINT)
        self.assertEqual(request.get_header("X-goog-api-key"), "secret-value")
        self.assertNotIn("secret-value", str(caught.exception))
        self.assertEqual(opener.call_count, 1)
        sleep.assert_not_called()

    def test_api_error_detail_redacts_key(self):
        body = json.dumps({"error": {"message": "Invalid API key: secret-value"}}).encode()
        error = HTTPError(translate.ENDPOINT, 400, "Bad Request", {}, io.BytesIO(body))
        with patch.object(translate, "urlopen", side_effect=error) as opener:
            with self.assertRaisesRegex(RuntimeError, r"Invalid API key: \[redacted\]") as caught:
                translate.call_api(translate.request_body(self.entry, "it"), "secret-value")
        self.assertNotIn("secret-value", str(caught.exception))
        self.assertEqual(opener.call_count, 1)


if __name__ == "__main__":
    unittest.main()
