from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

from .client import AliyunOCRClient, DEFAULT_PROVIDER, MAX_BINARY_SIZE_BYTES, OCRConfig
from .preprocess import render_pdf_to_page_images
from .schemas import OCRBatchResult, OCRResult


def recognize_document(
    file_path: str | Path,
    *,
    image_type: str = "Advanced",
    page_number: int = 1,
    config: OCRConfig | None = None,
) -> OCRBatchResult:
    path = Path(file_path)

    if path.suffix.lower() != ".pdf":
        client = AliyunOCRClient(config=config)
        single = client.recognize_file(path, image_type=image_type, page_number=page_number)
        return OCRBatchResult(
            document_id=single.document_id,
            provider=single.provider,
            total_pages=1,
            full_text=single.full_text,
            page_results=[single],
        )

    if path.stat().st_size <= MAX_BINARY_SIZE_BYTES:
        client = AliyunOCRClient(config=config)
        single = client.recognize_file(path, image_type=image_type, page_number=page_number)
        return OCRBatchResult(
            document_id=single.document_id,
            provider=single.provider,
            total_pages=1,
            full_text=single.full_text,
            page_results=[single],
        )

    client = AliyunOCRClient(config=config)
    tmpdir = Path(mkdtemp(dir=path.parent))
    try:
        parts = render_pdf_to_page_images(path, tmpdir)
        page_results: list[OCRResult] = []
        for part in parts:
            page_results.append(
                client.recognize_file(part.path, image_type=image_type, page_number=part.page_number)
            )
    finally:
        rmtree(tmpdir, ignore_errors=True)

    full_text = "\n\n".join(result.full_text for result in page_results if result.full_text)
    document_id = path.stem
    provider = page_results[0].provider if page_results else DEFAULT_PROVIDER
    return OCRBatchResult(
        document_id=document_id,
        provider=provider,
        total_pages=len(page_results),
        full_text=full_text,
        page_results=page_results,
    )
