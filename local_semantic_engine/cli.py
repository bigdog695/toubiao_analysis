from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .ingest import ingest_pdfs
from .model_loader import load_semantic_scoring_items
from .models import SearchQuery
from .scoring import SemanticScoringRunner
from .runtime import MOCK_RUNTIME_MODE, REAL_RUNTIME_MODE, build_llm_client
from .store import LocalSemanticStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local semantic ingestion and scoring tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="OCR + ingest PDFs into the local semantic store.")
    ingest_parser.add_argument("--project-id", required=True)
    ingest_parser.add_argument("--store-dir", required=True)
    ingest_parser.add_argument("--model-path", default="zhaobiao_file_model.json")
    ingest_parser.add_argument("--runtime-mode", choices=[MOCK_RUNTIME_MODE, REAL_RUNTIME_MODE], default=MOCK_RUNTIME_MODE)
    ingest_parser.add_argument("--mock-ocr-dir", help="Directory containing mock OCR JSON payloads.")
    ingest_parser.add_argument("--mock-ocr-map-json", help="JSON mapping from PDF file/path to OCR JSON file.")
    ingest_parser.add_argument("--doc-types-json", help="JSON mapping from file name/path to doc_type.")
    ingest_parser.add_argument("pdfs", nargs="+")

    search_parser = subparsers.add_parser("search", help="Search the local semantic store.")
    search_parser.add_argument("--project-id", required=True)
    search_parser.add_argument("--store-dir", required=True)
    search_parser.add_argument("--doc-types", nargs="*", default=[])
    search_parser.add_argument("--keywords", nargs="*", default=[])
    search_parser.add_argument("--queries", nargs="*", default=[])
    search_parser.add_argument("--top-k", type=int, default=5)

    items_parser = subparsers.add_parser("list-semantic-items", help="List semantic scoring items.")
    items_parser.add_argument("--model-path", default="zhaobiao_file_model.json")

    score_parser = subparsers.add_parser("score", help="Run semantic scoring with a unified runtime switch.")
    score_parser.add_argument("--project-id", required=True)
    score_parser.add_argument("--store-dir", required=True)
    score_parser.add_argument("--model-path", default="zhaobiao_file_model.json")
    score_parser.add_argument("--runtime-mode", choices=[MOCK_RUNTIME_MODE, REAL_RUNTIME_MODE], default=MOCK_RUNTIME_MODE)

    pipeline_parser = subparsers.add_parser("pipeline", help="Run ingest and scoring end-to-end with one runtime switch.")
    pipeline_parser.add_argument("--project-id", required=True)
    pipeline_parser.add_argument("--store-dir", required=True)
    pipeline_parser.add_argument("--model-path", default="zhaobiao_file_model.json")
    pipeline_parser.add_argument("--runtime-mode", choices=[MOCK_RUNTIME_MODE, REAL_RUNTIME_MODE], default=MOCK_RUNTIME_MODE)
    pipeline_parser.add_argument("--mock-ocr-dir", help="Directory containing mock OCR JSON payloads.")
    pipeline_parser.add_argument("--mock-ocr-map-json", help="JSON mapping from PDF file/path to OCR JSON file.")
    pipeline_parser.add_argument("--doc-types-json", help="JSON mapping from file name/path to doc_type.")
    pipeline_parser.add_argument("pdfs", nargs="+")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "ingest":
        report = run_ingest_from_args(args)
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
        return 1 if report.errors else 0

    if args.command == "search":
        store = LocalSemanticStore(args.store_dir)
        results = store.search(
            SearchQuery(
                project_id=args.project_id,
                required_doc_types=args.doc_types,
                keywords=args.keywords,
                semantic_queries=args.queries,
                top_k=args.top_k,
            )
        )
        print(json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2))
        return 0

    if args.command == "list-semantic-items":
        items = load_semantic_scoring_items(args.model_path)
        print(json.dumps([item.raw_item for item in items], ensure_ascii=False, indent=2))
        return 0

    if args.command == "score":
        store = LocalSemanticStore(args.store_dir)
        runner = SemanticScoringRunner(
            store=store,
            llm_client=build_llm_client(runtime_mode=args.runtime_mode),
        )
        result = runner.score_items(project_id=args.project_id, model_path=args.model_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("errors") else 0

    if args.command == "pipeline":
        ingest_report = run_ingest_from_args(args)
        if ingest_report.errors:
            print(
                json.dumps(
                    {
                        "ingest_report": asdict(ingest_report),
                        "score_report": None,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1
        store = LocalSemanticStore(args.store_dir)
        runner = SemanticScoringRunner(
            store=store,
            llm_client=build_llm_client(runtime_mode=args.runtime_mode),
        )
        score_report = runner.score_items(project_id=args.project_id, model_path=args.model_path)
        print(
            json.dumps(
                {
                    "ingest_report": asdict(ingest_report),
                    "score_report": score_report,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if score_report.get("errors") else 0

    parser.error(f"Unknown command: {args.command}")
    return 1


def load_json_mapping(path: str | Path) -> dict[str, str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("doc_types_json must contain a JSON object.")
    return {str(key): str(value) for key, value in payload.items()}


def run_ingest_from_args(args: argparse.Namespace):
    assignments = load_json_mapping(args.doc_types_json) if getattr(args, "doc_types_json", None) else {}
    mock_ocr_map = load_json_mapping(args.mock_ocr_map_json) if getattr(args, "mock_ocr_map_json", None) else {}
    return ingest_pdfs(
        pdf_paths=args.pdfs,
        project_id=args.project_id,
        store_dir=args.store_dir,
        model_path=args.model_path,
        doc_type_assignments=assignments,
        mock_ocr_dir=getattr(args, "mock_ocr_dir", None),
        mock_ocr_file_map=mock_ocr_map,
        runtime_mode=args.runtime_mode,
    )
