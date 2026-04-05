from __future__ import annotations

import argparse
import json
from pathlib import Path

from pypdf import PdfReader


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build mock OCR JSON files from text-based PDFs.")
    parser.add_argument("--input-dir", required=True, help="Directory containing input PDFs.")
    parser.add_argument("--output-dir", required=True, help="Directory to write OCR JSON payloads.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_paths = sorted(path for path in input_dir.glob("*.pdf") if path.is_file())
    report: list[dict[str, object]] = []
    for pdf_path in pdf_paths:
        payload = build_mock_ocr_payload(pdf_path)
        output_path = output_dir / f"{pdf_path.stem}.ocr.json"
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        report.append(
            {
                "source_pdf": str(pdf_path.resolve()),
                "output_json": str(output_path.resolve()),
                "pages": payload["total_pages"],
                "blocks": sum(len(page.get("blocks", [])) for page in payload["page_results"]),
            }
        )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def build_mock_ocr_payload(pdf_path: Path) -> dict:
    reader = PdfReader(str(pdf_path))
    page_results: list[dict] = []
    full_text_parts: list[str] = []

    for page_number, page in enumerate(reader.pages, start=1):
        extracted_text = (page.extract_text() or "").replace("\r\n", "\n").strip()
        paragraphs = split_to_paragraphs(extracted_text)
        blocks = [
            {
                "block_id": f"{pdf_path.stem}-p{page_number}-b{index}",
                "text": paragraph,
                "confidence": 1.0,
                "bbox": None,
                "points": [],
                "angle": None,
                "sub_image_id": None,
                "block_type": infer_block_type(paragraph),
            }
            for index, paragraph in enumerate(paragraphs, start=1)
        ]
        page_full_text = "\n\n".join(paragraphs)
        full_text_parts.append(page_full_text)
        page_results.append(
            {
                "document_id": pdf_path.stem,
                "page_number": page_number,
                "provider": "mock-pypdf",
                "full_text": page_full_text,
                "blocks": blocks,
                "request_id": None,
                "image_type": "mock",
                "width": None,
                "height": None,
                "raw_response": {
                    "source": "pypdf",
                    "source_file": pdf_path.name,
                },
            }
        )

    return {
        "document_id": pdf_path.stem,
        "provider": "mock-pypdf",
        "total_pages": len(page_results),
        "full_text": "\n\n".join(part for part in full_text_parts if part),
        "page_results": page_results,
    }


def split_to_paragraphs(text: str) -> list[str]:
    if not text.strip():
        return []

    normalized = text.replace("\u3000", " ").replace("\t", " ")
    raw_lines = [line.strip() for line in normalized.splitlines()]

    paragraphs: list[str] = []
    current: list[str] = []
    for line in raw_lines:
        if not line:
            flush_paragraph(current, paragraphs)
            current = []
            continue

        if current and looks_like_heading(line):
            flush_paragraph(current, paragraphs)
            current = [line]
            flush_paragraph(current, paragraphs)
            current = []
            continue

        if current and should_start_new_paragraph(current[-1], line):
            flush_paragraph(current, paragraphs)
            current = [line]
            continue

        current.append(line)

    flush_paragraph(current, paragraphs)
    return paragraphs


def flush_paragraph(lines: list[str], paragraphs: list[str]) -> None:
    if not lines:
        return
    paragraph = " ".join(part for part in lines if part).strip()
    if paragraph:
        paragraphs.append(paragraph)


def looks_like_heading(line: str) -> bool:
    heading_prefixes = (
        "第一章",
        "第二章",
        "第三章",
        "第四章",
        "第五章",
        "第六章",
        "第七章",
        "第八章",
        "第九章",
        "第十章",
        "一、",
        "二、",
        "三、",
        "四、",
        "五、",
        "六、",
        "七、",
        "八、",
        "九、",
        "十、",
    )
    return line.startswith(heading_prefixes)


def should_start_new_paragraph(previous_line: str, current_line: str) -> bool:
    if looks_like_heading(current_line):
        return True
    if previous_line.endswith(("。", "；", "：")):
        return True
    if len(previous_line) > 40 and len(current_line) < 12:
        return True
    return False


def infer_block_type(paragraph: str) -> str:
    table_markers = ("|", "表", "序号", "项目", "单位", "数量", "金额")
    marker_hits = sum(1 for marker in table_markers if marker in paragraph)
    if marker_hits >= 2:
        return "table"
    return "paragraph"


if __name__ == "__main__":
    raise SystemExit(main())
