from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from ocr.seal_market import SealMarketConfig
from ocr.seal_pipeline import detect_official_seals


class SealPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temp_root = Path("ocr/tests/.tmp")
        cls._temp_root.mkdir(parents=True, exist_ok=True)

    def setUp(self) -> None:
        self.config = SealMarketConfig(app_key="key", app_secret="secret")

    def test_non_pdf_uses_single_call(self) -> None:
        sample_path = self._temp_root / "seal_pipeline.png"
        sample_path.write_bytes(b"fake")

        fake_payload = {
            "provider": "aliyun-market-official-seal",
            "source_name": "seal_pipeline",
            "raw_response": {"data": []},
        }
        with patch("ocr.seal_pipeline.AliyunMarketSealClient.recognize_file", return_value=fake_payload) as mocked:
            result = detect_official_seals(sample_path, config=self.config)

        self.assertEqual(result.total_pages, 1)
        self.assertEqual(len(result.page_results), 1)
        mocked.assert_called_once()

    def test_pdf_renders_and_aggregates(self) -> None:
        pdf_path = self._temp_root / "seal_pipeline.pdf"
        pdf_path.write_bytes(b"0" * 1024)
        fake_parts = [
            type("Part", (), {"page_number": 1, "path": self._temp_root / "p1.png", "size_bytes": 100})(),
            type("Part", (), {"page_number": 2, "path": self._temp_root / "p2.png", "size_bytes": 100})(),
        ]
        fake_payloads = [
            {
                "provider": "aliyun-market-official-seal",
                "source_name": "p1",
                "raw_response": {"data": [{"page": 1}]},
            },
            {
                "provider": "aliyun-market-official-seal",
                "source_name": "p2",
                "raw_response": {"data": [{"page": 2}]},
            },
        ]
        with patch("ocr.seal_pipeline.render_pdf_to_page_images", return_value=fake_parts):
            with patch(
                "ocr.seal_pipeline.AliyunMarketSealClient.recognize_file",
                side_effect=fake_payloads,
            ) as mocked:
                result = detect_official_seals(pdf_path, config=self.config)

        self.assertEqual(result.total_pages, 2)
        self.assertEqual(len(result.page_results), 2)
        self.assertEqual(result.page_results[1].page_number, 2)
        self.assertEqual(mocked.call_count, 2)
