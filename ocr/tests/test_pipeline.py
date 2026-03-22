from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ocr.client import OCRConfig
from ocr.pipeline import recognize_document
from ocr.schemas import OCRResult


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temp_root = Path("ocr/tests/.tmp")
        cls._temp_root.mkdir(parents=True, exist_ok=True)

    def setUp(self) -> None:
        self.config = OCRConfig(access_key_id="test-ak", access_key_secret="test-sk")

    def test_non_pdf_uses_single_call(self) -> None:
        sample_dir = self._temp_root / "pipeline-image"
        sample_dir.mkdir(parents=True, exist_ok=True)
        sample_path = sample_dir / "sample.png"
        sample_path.write_bytes(b"fake-image")

        fake_result = OCRResult(
            document_id="sample",
            page_number=1,
            provider="aliyun-recognize-all-text",
            full_text="hello",
            blocks=[],
        )

        with patch("ocr.pipeline.AliyunOCRClient.recognize_file", return_value=fake_result) as mocked:
            batch = recognize_document(sample_path, config=self.config)

        self.assertEqual(batch.total_pages, 1)
        self.assertEqual(batch.full_text, "hello")
        mocked.assert_called_once()

    def test_large_pdf_splits_and_aggregates(self) -> None:
        sample_dir = self._temp_root / "pipeline-pdf"
        sample_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = sample_dir / "large.pdf"
        pdf_path.write_bytes(b"0" * (11 * 1024 * 1024))

        fake_parts = [
            type("Part", (), {"page_number": 1, "path": sample_dir / "p1.pdf", "size_bytes": 100})(),
            type("Part", (), {"page_number": 2, "path": sample_dir / "p2.pdf", "size_bytes": 100})(),
        ]
        fake_page_1 = OCRResult(
            document_id="large.page_0001",
            page_number=1,
            provider="aliyun-recognize-all-text",
            full_text="page one",
            blocks=[],
        )
        fake_page_2 = OCRResult(
            document_id="large.page_0002",
            page_number=2,
            provider="aliyun-recognize-all-text",
            full_text="page two",
            blocks=[],
        )

        with patch("ocr.pipeline.render_pdf_to_page_images", return_value=fake_parts):
            with patch(
                "ocr.pipeline.AliyunOCRClient.recognize_file",
                side_effect=[fake_page_1, fake_page_2],
            ) as mocked_recognize:
                batch = recognize_document(pdf_path, config=self.config)

        self.assertEqual(batch.total_pages, 2)
        self.assertEqual(batch.full_text, "page one\n\npage two")
        self.assertEqual(len(batch.page_results), 2)
        self.assertEqual(mocked_recognize.call_count, 2)
