"""Run with python -m unittest -v test_score after installing requirements."""

import unittest

from score import score


class ScoreTests(unittest.TestCase):
    def test_empty_text_and_validation(self):
        self.assertEqual(score({"lang": "en", "text": " \n\t"}), 0.0)
        with self.assertRaises(TypeError):
            score([])
        with self.assertRaises(TypeError):
            score({"lang": "ja", "text": None})
        with self.assertRaises(ValueError):
            score({"lang": "unknown", "text": "hello"})

    def test_line_height_spacing_and_multiple_pages(self):
        one_line = score({"lang": "en", "text": "Hello."})
        self.assertEqual(one_line, 1 / 21)
        # A full page is 1.00; only rendered lines count across page boundaries.
        for lines in (21, 22, 42):
            with self.subTest(lines=lines):
                pages = score({"lang": "en", "text": "\n".join(["Hello."] * lines)})
                self.assertEqual(pages, lines / 21)
        self.assertEqual(one_line, score({"lang": "en", "text": "Hello, world."}))

    def test_metadata_does_not_count_and_results_repeat(self):
        entry = {"lang": "en", "text": "A short passage. " * 150}
        first = score(entry)
        self.assertGreater(first, 1)
        # This is one source paragraph, so line count must come from wrapping.
        self.assertAlmostEqual(first * 21, round(first * 21), places=10)
        changed = dict(entry, idx=94, title="Very long title " * 100, original=0,
                       source="https://example.invalid/not-fetched", discipline="news")
        self.assertEqual(first, score(changed))

    def test_all_ten_languages(self):
        samples = {
            "en": "The garden is quiet in the morning.",
            "ar": "في الصباح يقرأ الأطفال قصة قصيرة في الحديقة.",
            "zh-Hans": "清晨，孩子们在花园里读一本有趣的书。",
            "de": "Morgens lesen die Kinder eine Geschichte im Garten.",
            "hi": "सुबह बच्चे बगीचे में एक छोटी कहानी पढ़ते हैं।",
            "it": "Al mattino i bambini leggono una storia in giardino.",
            "ja": "朝、子供たちは庭で短い物語を読みます。",
            "ru": "Утром дети читают короткий рассказ в саду.",
            "es": "Por la mañana, los niños leen un cuento en el jardín.",
            "sw": "Asubuhi watoto wanasoma hadithi fupi bustanini.",
        }
        for lang, text in samples.items():
            with self.subTest(lang=lang):
                self.assertEqual(score({"lang": lang, "text": text}), 1 / 21)
                self.assertEqual(score({"lang": lang, "text": "\n".join([text] * 21)}), 1.0)

    def test_cjk_long_text_wraps_and_paginates(self):
        for lang, sentence in [
            ("ja", "朝、子供たちは庭で短い物語を読みます。"),
            ("zh-Hans", "清晨，孩子们在花园里读一本有趣的书。"),
        ]:
            with self.subTest(lang=lang):
                pages = score({"lang": lang, "text": sentence * 100})
                self.assertGreater(pages, 2)
                self.assertLess(pages, 10)
                self.assertAlmostEqual(pages * 21, round(pages * 21), places=10)

    def test_rejects_horizontal_clipping_and_unavailable_glyphs(self):
        with self.assertRaisesRegex(Exception, "overflows"):
            score({"lang": "en", "text": "W" * 200})
        with self.assertRaisesRegex(ValueError, "outside the pinned fonts"):
            score({"lang": "en", "text": "Hello 🦄"})

    def test_redaction_bars_have_a_pinned_font(self):
        self.assertGreater(score({"lang": "ru", "text": "город ██████"}), 0)


if __name__ == "__main__":
    unittest.main()
