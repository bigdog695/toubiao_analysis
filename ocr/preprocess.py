from __future__ import annotations

from io import BytesIO
from dataclasses import dataclass
from pathlib import Path

from .client import MAX_BINARY_SIZE_BYTES, OCRInputError


@dataclass(slots=True)
class PDFSplitPart:
    page_number: int
    path: Path
    size_bytes: int


def split_pdf_to_single_pages(pdf_path: str | Path, output_dir: str | Path) -> list[PDFSplitPart]:
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError as exc:
        raise OCRInputError(
            "PyPDF2 is required for PDF splitting. Install dependencies from requirements.txt."
        ) from exc

    source_path = Path(pdf_path)
    if not source_path.exists():
        raise FileNotFoundError(f"PDF file does not exist: {source_path}")
    if source_path.suffix.lower() != ".pdf":
        raise OCRInputError("split_pdf_to_single_pages only accepts PDF input.")

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(source_path))
    parts: list[PDFSplitPart] = []

    for index, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)
        part_path = target_dir / f"{source_path.stem}.page_{index:04d}.pdf"
        with part_path.open("wb") as handle:
            writer.write(handle)

        size_bytes = part_path.stat().st_size
        if size_bytes > MAX_BINARY_SIZE_BYTES:
            raise OCRInputError(
                f"Split page {index} still exceeds the 10MB Aliyun OCR limit: {size_bytes} bytes."
            )

        parts.append(PDFSplitPart(page_number=index, path=part_path, size_bytes=size_bytes))

    return parts


def render_pdf_to_page_images(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    scale_candidates: tuple[float, ...] = (2.0, 1.5, 1.25, 1.0),
) -> list[PDFSplitPart]:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise OCRInputError(
            "pypdfium2 is required for PDF page rendering. Install dependencies from requirements.txt."
        ) from exc

    source_path = Path(pdf_path)
    if not source_path.exists():
        raise FileNotFoundError(f"PDF file does not exist: {source_path}")
    if source_path.suffix.lower() != ".pdf":
        raise OCRInputError("render_pdf_to_page_images only accepts PDF input.")

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    document = pdfium.PdfDocument(str(source_path))
    parts: list[PDFSplitPart] = []

    for index in range(len(document)):
        page = document[index]
        try:
            image_bytes = None
            extension = ".png"
            for scale in scale_candidates:
                pil_image = page.render(scale=scale).to_pil()

                png_buffer = BytesIO()
                pil_image.save(png_buffer, format="PNG")
                png_bytes = png_buffer.getvalue()
                if len(png_bytes) <= MAX_BINARY_SIZE_BYTES:
                    image_bytes = png_bytes
                    extension = ".png"
                    break

                jpeg_buffer = BytesIO()
                rgb_image = pil_image.convert("RGB")
                rgb_image.save(jpeg_buffer, format="JPEG", quality=85, optimize=True)
                jpeg_bytes = jpeg_buffer.getvalue()
                if len(jpeg_bytes) <= MAX_BINARY_SIZE_BYTES:
                    image_bytes = jpeg_bytes
                    extension = ".jpg"
                    break

            if image_bytes is None:
                raise OCRInputError(
                    f"Rendered page {index + 1} still exceeds the 10MB Aliyun OCR limit."
                )

            part_path = target_dir / f"{source_path.stem}.page_{index + 1:04d}{extension}"
            part_path.write_bytes(image_bytes)
            parts.append(
                PDFSplitPart(
                    page_number=index + 1,
                    path=part_path,
                    size_bytes=len(image_bytes),
                )
            )
        finally:
            page.close()

    document.close()
    return parts
