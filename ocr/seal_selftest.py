from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .seal_pipeline import detect_official_seals


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run official seal OCR against an image or PDF.")
    parser.add_argument("--file", required=True, help="Path to an image or PDF file.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the aggregated seal OCR result as JSON.",
    )
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args()
    result = detect_official_seals(Path(args.file))

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"provider={result.provider}")
        print(f"document_id={result.document_id}")
        print(f"total_pages={result.total_pages}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
