"""Regression checks for the shared prose paginator and stored page scores."""

import json
from pathlib import Path
import re
import unittest

from playwright.sync_api import sync_playwright

import score as scorer


ROOT = Path(__file__).resolve().parent


class RendererTests(unittest.TestCase):
    def setUp(self):
        # Public score() owns its Playwright context; do not nest sync runtimes.
        if self._testMethodName == "test_stored_score_regressions":
            return
        font = scorer._font_path("Noto Serif")
        runtime = sync_playwright().start()
        self.addCleanup(runtime.stop)
        browser = runtime.chromium.launch()
        self.addCleanup(browser.close)
        context = browser.new_context(
            viewport={"width": 930, "height": 624}, device_scale_factor=1,
            locale="en-US", offline=True,
        )

        def serve_font(route):
            if route.request.url == "https://langprint.invalid/0.ttf":
                route.fulfill(path=font, content_type="font/ttf", headers={
                    "Access-Control-Allow-Origin": "*",
                })
            else:
                route.abort()

        context.route("**/*", serve_font)
        self.page = context.new_page()

    def render(self, text):
        self.page.set_content(scorer._HTML)
        self.page.add_script_tag(content=(ROOT / "renderer.js").read_text())
        return self.page.evaluate(scorer._MEASURE, {
            "lang": "en", "text": text,
            "fonts": [{"family": "Noto Serif", "url": "https://langprint.invalid/0.ttf"}],
        })

    def test_about_fills_pages_and_preserves_text(self):
        html = (ROOT / "index.html").read_text()
        source = re.search(
            r'<script\b[^>]*\bid=([\'"])book-text\1[^>]*>(.*?)</script>',
            html, re.DOTALL,
        )
        self.assertIsNotNone(source, "About must have one continuous source text")
        sections = json.loads(source.group(2))
        about = next(section for section in sections if section["id"] == "about")
        result = self.render(about["text"])
        self.assertEqual(len(result["pages"]), 2)
        self.assertEqual(result["pages"][0]["lines"], 21)
        self.assertTrue(all(0 < page["lines"] <= 21 for page in result["pages"]))
        rendered = " ".join(
            paragraph for page in result["pages"] for paragraph in page["paragraphs"]
        )
        self.assertEqual(rendered.split(), about["text"].split())

    def test_page_boundaries_for_22_and_42_lines(self):
        for count, expected in [(22, [21, 1]), (42, [21, 21])]:
            with self.subTest(lines=count):
                text = "\n".join(["Hello."] * count)
                result = self.render(text)
                self.assertEqual([page["lines"] for page in result["pages"]], expected)
                self.assertEqual(result["occupied_pages"], count / 21)

    def test_stored_score_regressions(self):
        rows = json.loads((ROOT / "data" / "results.json").read_text())
        for idx, lang, lines in [(1, "en", 39), (94, "ja", 28), (15, "ru", 23)]:
            with self.subTest(idx=idx, lang=lang):
                entry = next(row for row in rows if row["idx"] == idx and row["lang"] == lang)
                self.assertEqual(entry["occupied_pages"], lines / 21)
                self.assertEqual(scorer.score(entry), lines / 21)


if __name__ == "__main__":
    unittest.main()
