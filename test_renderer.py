"""Regression checks for the shared prose paginator and stored page scores."""

import json
import os
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
        runtime = sync_playwright().start()
        self.addCleanup(runtime.stop)
        browser = runtime.chromium.launch()
        self.addCleanup(browser.close)
        context = browser.new_context(
            viewport={"width": 930, "height": 624}, device_scale_factor=1,
            locale="en-US", offline=True,
        )

        self.page = context.new_page()
        if self._testMethodName == "test_localized_about":
            return
        font = scorer._font_path("Noto Serif")

        def serve_font(route):
            if route.request.url == "https://langprint.invalid/0.ttf":
                route.fulfill(path=font, content_type="font/ttf", headers={
                    "Access-Control-Allow-Origin": "*",
                })
            else:
                route.abort()

        context.route("**/*", serve_font)

    def render(self, text):
        self.page.set_content(scorer._HTML)
        self.page.add_script_tag(content=(ROOT / "renderer.js").read_text())
        return self.page.evaluate(scorer._MEASURE, {
            "lang": "en", "text": text,
            "fonts": [{"family": "Noto Serif", "url": "https://langprint.invalid/0.ttf"}],
        })

    def test_localized_about(self):
        self.page.goto((ROOT / "index.html").as_uri() + "#page-3")
        self.page.wait_for_function("document.documentElement.dataset.ready", timeout=240_000)
        self.assertEqual(self.page.locator("html").get_attribute("data-ready"), "true",
                         self.page.locator("#book-position").text_content())
        book = json.loads(self.page.locator("#book-data").text_content())
        report = json.loads(self.page.locator("#fit-report").text_content())
        self.assertFalse(report["overflows"])
        self.assertEqual(len(report["about"]), 10)
        required = max(entry["required"] for entry in report["about"])
        self.assertEqual(book["aboutPages"], 2 * ((required + 1) // 2))
        for locale in book["languages"]:
            with self.subTest(lang=locale["lang"]):
                edition = self.page.locator(f'article[data-lang="{locale["lang"]}"]')
                pages = edition.locator('.page[data-section="text"]')
                self.assertEqual(pages.count(), book["aboutPages"])
                body = pages.locator(".book-copy")
                self.assertEqual(body.first.get_attribute("lang"), locale["lang"])
                self.assertEqual(body.first.get_attribute("dir"), locale["dir"])
                compact = lambda text: re.sub(r"\s+", "", text)
                self.assertEqual(compact("".join(body.locator("p").all_text_contents())),
                                 compact(locale["aboutText"]))
                self.assertEqual(body.get_by_role("link", include_hidden=True).count(), 1)
                self.assertEqual(body.locator("a").get_attribute("href"), book["methodologyUrl"])
                self.assertEqual(edition.locator(".page--index").first.get_attribute("data-folio"),
                                 str(3 + book["aboutPages"]))
        print("About pagination:", report["about"])
        report_path = os.environ.get("LANGPRINT_FIT_REPORT")
        if report_path:
            Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

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
