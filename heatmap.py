"""Build the domain heatmap JSON and figure from the scored corpus."""

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LANGUAGES = {
    "en": "English", "ar": "Arabic", "zh-Hans": "Chinese (simplified)",
    "de": "German", "hi": "Hindi", "it": "Italian", "ja": "Japanese",
    "ru": "Russian", "es": "Spanish", "sw": "Swahili",
}
DISCIPLINES = (
    "fiction/stories", "news", "food/cooking", "health", "travel/places",
    "sports", "work/money", "nature/environment", "science/technology", "arts/culture",
)
DOMAIN_LABELS = (
    "Fiction /\nstories", "News", "Food /\ncooking", "Health", "Travel /\nplaces",
    "Sports", "Work /\nmoney", "Nature /\nenvironment", "Science /\ntechnology", "Arts /\nculture",
)


def compute_heatmap(rows):
    passages = defaultdict(list)
    for row in rows:
        passages[row["idx"]].append(row)
    cells = defaultdict(list)
    for idx, versions in passages.items():
        if len(versions) != 10 or {r["lang"] for r in versions} != set(LANGUAGES):
            raise ValueError(f"Passage {idx} must have ten unique language versions.")
        domains = {r["discipline"] for r in versions}
        if len(domains) != 1 or not domains <= set(DISCIPLINES):
            raise ValueError(f"Passage {idx} has inconsistent or unknown domains.")
        if sum(r["original"] == 1 for r in versions) != 1:
            raise ValueError(f"Passage {idx} must have one original.")
        scores = [r["occupied_pages"] for r in versions]
        if not all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in scores):
            raise ValueError(f"Passage {idx} needs finite positive occupied_pages scores.")
        average = math.fsum(scores) / 10
        for row in versions:
            ratio = row["occupied_pages"] / average
            if (not math.isclose(row["occupied_pages_avg"], average, rel_tol=1e-12)
                    or not math.isclose(row["occupied_pages_ratio"], ratio, rel_tol=1e-12)):
                raise ValueError(f"Passage {idx} has stale averages or ratios.")
            cells[row["lang"], row["discipline"]].append(row["occupied_pages_ratio"])

    result = []
    for lang in LANGUAGES:
        for discipline in DISCIPLINES:
            values = cells[lang, discipline]
            if len(values) != 20:
                raise ValueError(f"{lang}/{discipline}: expected 20 passages, got {len(values)}.")
            result.append({
                "lang": lang, "discipline": discipline,
                "occupied_pages_ratio": math.fsum(values) / len(values), "n": len(values),
            })
    return {
        "schema_version": 1,
        "metric": "occupied_pages_ratio", "aggregation": "arithmetic_mean",
        "reference": 1.0, "passage_count": len(passages),
        "languages": [{"code": code, "label": label} for code, label in LANGUAGES.items()],
        "disciplines": list(DISCIPLINES), "cells": result,
    }


def render_heatmap(data, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
    import numpy as np

    lookup = {(c["lang"], c["discipline"]): c["occupied_pages_ratio"] for c in data["cells"]}
    values = np.array([[lookup[lang, domain] for domain in DISCIPLINES] for lang in LANGUAGES])
    # One symmetric, linear scale for the entire matrix, centred at 1.0.
    span = max(0.05, math.ceil(float(np.max(np.abs(values - 1))) * 20) / 20)
    norm = TwoSlopeNorm(vmin=1-span, vcenter=1, vmax=1+span)
    cmap = LinearSegmentedColormap.from_list(
        "LangPrint", ["#87ab8b", "#fbf5e7", "#c77f78"], N=257
    )
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 12}):
        fig, ax = plt.subplots(figsize=(12.8, 8.8))
        fig.subplots_adjust(left=.19, right=.98, top=.87, bottom=.22)
        image = ax.imshow(values, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
        ax.set_xticks(range(10), DOMAIN_LABELS, fontsize=11)
        ax.set_yticks(range(10), list(LANGUAGES.values()), fontsize=12)
        ax.tick_params(axis="both", length=0, pad=10)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_xticks(np.arange(-.5, 10, 1), minor=True)
        ax.set_yticks(np.arange(-.5, 10, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=2)
        ax.tick_params(which="minor", bottom=False, left=False)
        for (i, j), value in np.ndenumerate(values):
            rgb = cmap(norm(value))[:3]
            luminance = .2126*rgb[0] + .7152*rgb[1] + .0722*rgb[2]
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=12,
                    color="white" if luminance < .5 else "#17202b")
        fig.suptitle("Printed page space across languages", x=.19, y=.965,
                     ha="left", fontsize=21, fontweight="bold")
        fig.text(.19, .915, "Mean passage ratio by domain · 20 matched passages per cell",
                 ha="left", fontsize=12, color="#4d5562")
        cax = fig.add_axes([.30, .105, .56, .022])
        ticks = np.arange(1-span, 1+span+.001, .1)
        bar = fig.colorbar(image, cax=cax, orientation="horizontal", ticks=ticks)
        bar.ax.set_xticklabels([f"{tick:.1f}×" for tick in ticks], fontsize=10)
        bar.outline.set_visible(False)
        bar.set_label("1.0× = the passage’s mean across its ten language versions", fontsize=11, labelpad=8)
        fig.text(.19, .018, "Measured using this corpus, Google NMT and the fixed Noto typography.",
                 ha="left", va="bottom", fontsize=10, color="#4d5562")
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=180, facecolor="white")
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/results.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/heatmap.json")
    parser.add_argument("--figure", type=Path, default=ROOT / "data/heatmap.png")
    args = parser.parse_args()
    raw = args.input.read_bytes()
    data = compute_heatmap(json.loads(raw))
    data["source_file"] = args.input.name
    data["source_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    render_heatmap(data, args.figure)
    print(f"Saved {len(data['cells'])} cells to {args.output} and {args.figure}.")


if __name__ == "__main__":
    main()
