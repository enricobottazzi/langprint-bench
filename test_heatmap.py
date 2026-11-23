"""Check matched aggregation, equal passage weighting and stale-data rejection."""

import math
import unittest

from heatmap import LANGUAGES, DISCIPLINES, compute_heatmap


class HeatmapTests(unittest.TestCase):
    def setUp(self):
        self.rows = []
        for domain_index, domain in enumerate(DISCIPLINES):
            for sample in range(20):
                idx = domain_index * 20 + sample + 1
                for language_index, lang in enumerate(LANGUAGES):
                    self.rows.append({
                        "idx": idx, "lang": lang, "discipline": domain,
                        "original": int(language_index == sample % 10),
                        "occupied_pages": 1.0, "occupied_pages_avg": 1.0,
                        "occupied_pages_ratio": 1.0,
                    })

    def test_complete_grid_and_reference(self):
        data = compute_heatmap(self.rows)
        self.assertEqual(data["passage_count"], 200)
        self.assertEqual(len(data["cells"]), 100)
        self.assertTrue(all(c["n"] == 20 and c["occupied_pages_ratio"] == 1 for c in data["cells"]))

    def test_passages_are_equally_weighted_despite_length(self):
        for row in self.rows:
            if row["idx"] == 1:
                row["occupied_pages"] = 2.0 if row["lang"] == "en" else 1.0
                row["occupied_pages_avg"] = 1.1
                row["occupied_pages_ratio"] = row["occupied_pages"] / 1.1
            elif row["idx"] == 2:
                row["occupied_pages"] = row["occupied_pages_avg"] = 100.0
        data = compute_heatmap(self.rows)
        cell = next(c for c in data["cells"] if c["lang"] == "en" and c["discipline"] == DISCIPLINES[0])
        self.assertAlmostEqual(cell["occupied_pages_ratio"], 229 / 220)
        self.assertFalse(math.isclose(cell["occupied_pages_ratio"], 120 / 119.1))

    def test_incomplete_passages_rejected(self):
        with self.assertRaisesRegex(ValueError, "ten unique language versions"):
            compute_heatmap(self.rows[1:])

    def test_stale_derived_metrics_rejected(self):
        for field in ("occupied_pages_avg", "occupied_pages_ratio"):
            with self.subTest(field=field):
                self.rows[0][field] = 2
                with self.assertRaisesRegex(ValueError, "stale"):
                    compute_heatmap(self.rows)
                self.rows[0][field] = 1


if __name__ == "__main__":
    unittest.main()
