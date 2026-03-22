from __future__ import annotations

import base64
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ocr.client import OCRConfigurationError, OCRInputError
from ocr.seal_market import (
    AliyunMarketSealClient,
    SealMarketConfig,
    recognize_official_seal_file,
)


class SealMarketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temp_root = Path("ocr/tests/.tmp")
        cls._temp_root.mkdir(parents=True, exist_ok=True)

    def setUp(self) -> None:
        self.config = SealMarketConfig(
            app_key="demo-app-key",
            app_secret="demo-app-secret",
        )

    def _make_sample_image(self, suffix: str = ".png") -> Path:
        path = self._temp_root / f"seal-sample{suffix}"
        path.write_bytes(b"fake-image-data")
        return path

    def test_from_env_requires_market_credentials(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch("ocr.seal_market.load_default_env", return_value=None):
                with self.assertRaises(OCRConfigurationError):
                    SealMarketConfig.from_env()

    def test_rejects_unsupported_extension(self) -> None:
        path = self._make_sample_image(".pdf")
        client = AliyunMarketSealClient(config=self.config)
        with self.assertRaises(OCRInputError):
            client.recognize_file(path)

    def test_build_headers_contains_signature_fields(self) -> None:
        client = AliyunMarketSealClient(config=self.config)
        headers = client._build_headers(b'{"image":"demo"}')
        self.assertEqual(headers["X-Ca-Key"], "demo-app-key")
        self.assertEqual(headers["X-Ca-Signature-Method"], "HmacSHA256")
        self.assertIn("x-ca-key", headers["X-Ca-Signature-Headers"])
        self.assertTrue(headers["X-Ca-Signature"])

    def test_recognize_file_posts_signed_request(self) -> None:
        path = self._make_sample_image(".png")
        client = AliyunMarketSealClient(config=self.config)

        mock_response = Mock()
        mock_response.json.return_value = {"success": True, "data": {"name": "测试章"}}
        mock_response.raise_for_status.return_value = None

        with patch("ocr.seal_market.requests.post", return_value=mock_response) as mocked_post:
            payload = client.recognize_file(path)

        self.assertEqual(payload["provider"], "aliyun-market-official-seal")
        self.assertEqual(payload["source_name"], "seal-sample")
        mocked_post.assert_called_once()
        body_bytes = mocked_post.call_args.kwargs["data"]
        parsed_body = json.loads(body_bytes.decode("utf-8"))
        self.assertEqual(
            parsed_body["image"],
            base64.b64encode(path.read_bytes()).decode("utf-8"),
        )

    def test_public_function_returns_payload(self) -> None:
        path = self._make_sample_image(".jpg")
        expected = {"provider": "aliyun-market-official-seal", "raw_response": {"ok": True}}
        with patch("ocr.seal_market.AliyunMarketSealClient.recognize_file", return_value=expected):
            result = recognize_official_seal_file(path, config=self.config)
        self.assertEqual(result["provider"], "aliyun-market-official-seal")


if __name__ == "__main__":
    unittest.main()
