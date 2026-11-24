"""Integrity checks for the static multilingual books and their reference lines."""
import base64
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent


class BookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'index.html').read_text()
        cls.book = json.loads(re.search(r'<script id="book-data" type="application/json">(.*?)</script>', cls.html, re.S).group(1))
        cls.raw = (ROOT / 'data/results.json').read_bytes()
        cls.rows = {(r['idx'], r['lang']): r for r in json.loads(cls.raw)}

    def test_complete_corpus_and_common_page_ranges(self):
        self.assertEqual(self.book['sourceSha256'], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(len(self.book['languages']), 10)
        self.assertEqual(len(self.book['passages']), 200)
        self.assertEqual(self.book['contentsPages'], 22)
        self.assertIn(self.book['aboutPages'], (2, 4, 6))
        next_page = 3 + self.book['aboutPages'] + self.book['contentsPages']
        for passage in self.book['passages']:
            self.assertEqual(passage['startPage'], next_page)
            self.assertIn(passage['allocatedPages'], (2, 4, 6))
            self.assertEqual(len(passage['versions']), 10)
            for lang, version in passage['versions'].items():
                source = self.rows[passage['idx'], lang]
                self.assertEqual(version['text'], source['text'])
                self.assertEqual(version['occupiedPages'], source['occupied_pages'])
                self.assertEqual(version['original'], source['original'] == 1)
                self.assertLessEqual(version['occupiedPages'], passage['allocatedPages'])
            next_page = passage['endPage'] + 1
        self.assertEqual(next_page, self.book['totalPages'] + 1)
        self.assertEqual(self.book['totalPages'], 634)

    def test_localized_original_titles_and_about(self):
        editions = self.book['languages']
        self.assertEqual(len({locale['aboutText'] for locale in editions}), 10)
        self.assertTrue((ROOT / self.book['methodologyUrl'].split('/')[-1]).is_file())
        for locale in editions:
            self.assertEqual(len(locale['aboutText'].split('\n\n')), 6)
            self.assertEqual(locale['aboutText'].count('GitHub'), 1)
            self.assertEqual(len(locale['titles']), 200)
            self.assertEqual(locale['dir'], 'rtl' if locale['lang'] == 'ar' else 'ltr')
            originals = [r for (idx, lang), r in self.rows.items() if lang == locale['lang'] and r['original'] == 1]
            self.assertEqual(len(originals), 20)
            for row in originals:
                self.assertEqual(locale['titles'][str(row['idx'])], row['title'])

    def test_reference_lines_preserve_text_and_score(self):
        checked = 0
        compact = lambda text: re.sub(r'\s+', '', text)
        for passage in self.book['passages']:
            for version in passage['versions'].values():
                reference = version.get('referenceLayout')
                if not reference:
                    continue
                checked += 1
                text = ''.join(line for page in reference['pages'] for paragraph in page['paragraphs'] for line in paragraph['lines'])
                self.assertEqual(compact(text), compact(version['text']))
                for page in reference['pages']:
                    self.assertEqual(page['lines'], sum(len(p['lines']) for p in page['paragraphs']))
                    self.assertLessEqual(page['lines'], 21)
                lines = sum(page['lines'] for page in reference['pages'])
                self.assertAlmostEqual(lines / 21, version['occupiedPages'])
                self.assertEqual(reference['occupied_pages'], version['occupiedPages'])
                self.assertLessEqual(len(reference['pages']), passage['allocatedPages'])
        self.assertGreater(checked, 0)

    def test_embedded_fonts_match_packaged_files(self):
        inventory = json.loads((ROOT / 'assets/fonts/font-inventory.json').read_text())
        embedded = re.findall(r'font-family:\s*"([^"]+)";\s*src:\s*url\([^,]+,([A-Za-z0-9+/=]+)', self.html)
        hashes = {family: hashlib.sha256(base64.b64decode(data)).hexdigest() for family, data in embedded}
        for font in inventory['fonts']:
            packaged = ROOT / 'assets/fonts' / font['file']
            self.assertEqual(hashlib.sha256(packaged.read_bytes()).hexdigest(), font['sha256'])
            self.assertEqual(hashes[font['family']], font['sha256'])


if __name__ == '__main__':
    unittest.main()
