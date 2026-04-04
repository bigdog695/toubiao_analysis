from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Any

from .seal_pipeline import detect_official_seals


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run seal OCR and collect personal-seal name permutations."
    )
    parser.add_argument("--file", required=True, help="Path to an image or PDF file.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print normalized JSON output.",
    )
    return parser


def _walk_content_values(payload: Any) -> list[str]:
    values: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            content = node.get("content")
            if isinstance(content, str):
                cleaned = content.strip().strip('"')
                if cleaned:
                    values.append(cleaned)
            for child in node.values():
                walk(child)
            return

        if isinstance(node, list):
            for child in node:
                walk(child)

    walk(payload)
    return values


def _collect_personal_seal_texts(raw_response: dict[str, Any]) -> set[str]:
    results: set[str] = set()
    for content in _walk_content_values(raw_response):
        normalized = "".join(content.split())
        if "印" in normalized and "公司" not in normalized:
            results.add(normalized)
    return results


def _name_permutations_without_yin(text: str) -> set[str]:
    name = text.replace("印", "")
    if not name:
        return set()
    return {"".join(chars) for chars in itertools.permutations(name)}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args()

    result = detect_official_seals(Path(args.file))

    personal_seal_contents: set[str] = set()
    name_permutation_set: set[str] = set()

    for page in result.page_results:
        page_contents = _collect_personal_seal_texts(page.raw_response)
        personal_seal_contents.update(page_contents)
        for content in page_contents:
            name_permutation_set.update(_name_permutations_without_yin(content))

    payload = {
        "provider": result.provider,
        "document_id": result.document_id,
        "total_pages": result.total_pages,
        "personal_seal_contents": sorted(personal_seal_contents),
        "name_permutation_set": sorted(name_permutation_set),
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"provider={payload['provider']}")
        print(f"document_id={payload['document_id']}")
        print(f"total_pages={payload['total_pages']}")
        print(f"personal_seal_count={len(personal_seal_contents)}")
        print(f"name_permutation_count={len(name_permutation_set)}")
        if personal_seal_contents:
            print("personal_seal_contents:")
            for text in sorted(personal_seal_contents):
                print(text)
        if name_permutation_set:
            print("name_permutation_set:")
            for text in sorted(name_permutation_set):
                print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
