from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import recognize_document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a live self-test against Aliyun OCR.")
    parser.add_argument("--file", required=True, help="Path to an image or PDF file.")
    parser.add_argument("--type", default="Advanced", help="Aliyun OCR Type, default: Advanced")
    parser.add_argument("--page", type=int, default=1, help="PDF page number to recognize, default: 1")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the normalized OCR result as JSON instead of a short summary.",
    )
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args()

    path = Path(args.file)
    result = recognize_document(path, image_type=args.type, page_number=args.page)

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"provider={result.provider}")
        print(f"document_id={result.document_id}")
        print(f"total_pages={result.total_pages}")
        block_count = sum(len(page.blocks) for page in result.page_results)
        print(f"blocks={block_count}")
        print("preview:")
        print(result.full_text[:1000])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
