from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

from .preprocess import render_pdf_to_page_images
from .schemas import SealBatchResult, SealPageResult
from .seal_market import (
    SEAL_MARKET_PROVIDER,
    AliyunMarketSealClient,
    SealMarketConfig,
)


def detect_official_seals(
    file_path: str | Path,
    *,
    config: SealMarketConfig | None = None,
) -> SealBatchResult:
    path = Path(file_path)
    client = AliyunMarketSealClient(config=config)

    if path.suffix.lower() != ".pdf":
        payload = client.recognize_file(path)
        page = SealPageResult(
            document_id=path.stem,
            page_number=1,
            provider=payload["provider"],
            source_name=payload["source_name"],
            raw_response=payload["raw_response"],
        )
        return SealBatchResult(
            document_id=path.stem,
            provider=payload["provider"],
            total_pages=1,
            page_results=[page],
        )

    tmpdir = Path(mkdtemp(dir=path.parent))
    try:
        parts = render_pdf_to_page_images(path, tmpdir)
        page_results: list[SealPageResult] = []
        for part in parts:
            payload = client.recognize_file_safe(part.path)
            page_results.append(
                SealPageResult(
                    document_id=path.stem,
                    page_number=part.page_number,
                    provider=payload["provider"],
                    source_name=payload["source_name"],
                    raw_response=payload["raw_response"],
                )
            )
    finally:
        rmtree(tmpdir, ignore_errors=True)

    return SealBatchResult(
        document_id=path.stem,
        provider=page_results[0].provider if page_results else SEAL_MARKET_PROVIDER,
        total_pages=len(page_results),
        page_results=page_results,
    )
