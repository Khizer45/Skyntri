"""
Evaluate the skin / non-skin input gate on a labelled folder (SEC-ML-009).

Folder layout (images are NOT committed to the repository):

    <dataset>/skin/<category>/*.jpg        valid skin photos (e.g. face, closeup)
    <dataset>/non_skin/<category>/*.jpg    hard negatives (electronics, documents,
                                           food, animals, rooms, screenshots ...)

Usage:
    python scripts/evaluate_input_gate.py /path/to/dataset [--track facial_concerns]

Reports, with 95% Wilson confidence intervals:
    * non-skin false-accept rate (overall and per negative category)
    * valid-skin rejection rate (overall and per positive category)
    * counts of decisions and reason codes
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.image_gate import assess_image, current_gate_version  # noqa: E402

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def wilson(errors: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return (0.0, 0.0)
    p = errors / total
    denom = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def iter_images(folder: Path):
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            category = path.parent.name if path.parent != folder else "uncategorised"
            yield category, path


def evaluate(dataset: Path, track: str) -> dict:
    report: dict = {"gate_version": current_gate_version(), "track": track}

    for split, positive in (("skin", True), ("non_skin", False)):
        per_category: dict[str, Counter] = defaultdict(Counter)
        reasons: Counter = Counter()

        for category, path in iter_images(dataset / split):
            result = assess_image(path, track=track)
            per_category[category][result.status] += 1
            reasons[result.reason_code] += 1

        total = sum(sum(c.values()) for c in per_category.values())
        accepted = sum(c["accepted"] for c in per_category.values())

        errors = (total - accepted) if positive else accepted
        label = "valid_skin_rejection_rate" if positive else "non_skin_false_accept_rate"
        low, high = wilson(errors, total)

        report[split] = {
            "images": total,
            label: round(errors / total, 4) if total else None,
            "ci95": [round(low, 4), round(high, 4)],
            "reason_codes": dict(reasons),
            "by_category": {
                name: {"images": sum(counts.values()), **dict(counts)}
                for name, counts in sorted(per_category.items())
            },
        }

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--track", default="facial_concerns")
    args = parser.parse_args()

    print(json.dumps(evaluate(args.dataset, args.track), indent=2))


if __name__ == "__main__":
    main()
