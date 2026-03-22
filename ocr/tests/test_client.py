from __future__ import annotations

import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from ocr.client import AliyunOCRClient, OCRConfig, OCRConfigurationError, OCRInputError, recognize_all_text_file


class DummyResponse:
    def to_map(self):
        return {
            "RequestId": "req-123",
            "Data": {
                "Width": 1000,
                "Height": 2000,
                "Content": '"合同编号..."',
                "SubImages": [
                    {
                        "SubImageId": 0,
                        "Type": "通用文字",
                        "BlockInfo": {
                            "BlockDetails": [
                                {
                                    "BlockId": 1,
                                    "BlockContent": "第一行",
                                    "BlockConfidence": 98,
                                    "BlockAngle": 0,
                                    "BlockRect": {
                                        "CenterX": 100,
                                        "CenterY": 50,
                                        "Width": 80,
                                        "Height": 20,
                                    },
                                    "BlockPoints": [
                                        {"X": 60, "Y": 40},
                                        {"X": 140, "Y": 40},
                                        {"X": 140, "Y": 60},
                                        {"X": 60, "Y": 60},
                                    ],
                                }
                            ]
                        },
                    }
                ],
            },
        }


class DummyNestedResponse:
    def to_map(self):
        return {
            "headers": {
                "x-acs-request-id": "req-nested-123",
            },
            "statusCode": 200,
            "body": {
                "RequestId": "req-body-123",
                "Data": {
                    "Width": 1000,
                    "Height": 2000,
                    "Content": "嵌套响应文本",
                    "SubImages": [
                        {
                            "SubImageId": 0,
                            "Type": "通用文字",
                            "BlockInfo": {
                                "BlockDetails": [
                                    {
                                        "BlockId": 7,
                                        "BlockContent": "嵌套块",
                                        "BlockConfidence": 88,
                                        "BlockAngle": 0,
                                        "BlockRect": {
                                            "CenterX": 50,
                                            "CenterY": 50,
                                            "Width": 20,
                                            "Height": 10,
                                        },
                                        "BlockPoints": [],
                                    }
                                ]
                            },
                        }
                    ],
                },
            },
        }


class DummySDKClient:
    def __init__(self):
        self.last_request = None

    def recognize_all_text(self, request):
        self.last_request = request
        return DummyResponse()


class OCRClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temp_root = Path("ocr/tests/.tmp")
        cls._temp_root.mkdir(parents=True, exist_ok=True)

    def setUp(self) -> None:
        self.config = OCRConfig(
            access_key_id="test-ak",
            access_key_secret="test-sk",
        )

    def _make_sample_file(self) -> Path:
        sample_dir = self._temp_root / f"case-{uuid.uuid4().hex}"
        sample_dir.mkdir(parents=True, exist_ok=True)
        sample_path = sample_dir / "sample.png"
        sample_path.write_bytes(b"fake-image")
        return sample_path

    def test_recognize_file_normalizes_response(self) -> None:
        sample_path = self._make_sample_file()

        client = AliyunOCRClient(config=self.config)
        dummy_sdk = DummySDKClient()

        with patch.object(client, "_get_sdk_client", return_value=dummy_sdk):
            with patch.object(client, "_build_request", return_value=object()):
                result = client.recognize_file(sample_path)

        self.assertEqual(result.document_id, "sample")
        self.assertEqual(result.provider, "aliyun-recognize-all-text")
        self.assertEqual(result.full_text, "合同编号...")
        self.assertEqual(len(result.blocks), 1)
        self.assertEqual(result.blocks[0].text, "第一行")
        self.assertEqual(result.blocks[0].bbox, [60, 40, 140, 60])
        self.assertAlmostEqual(result.blocks[0].confidence or 0, 0.98)

    def test_public_function_returns_dict(self) -> None:
        sample_path = self._make_sample_file()

        payload = {
            "document_id": "sample",
            "page_number": 1,
            "provider": "aliyun-recognize-all-text",
            "full_text": "hello",
            "blocks": [],
            "raw_response": {},
        }
        with patch("ocr.client.AliyunOCRClient.recognize_file") as mocked:
            mocked.return_value.to_dict.return_value = payload
            result = recognize_all_text_file(sample_path, config=self.config)

        self.assertEqual(result["provider"], "aliyun-recognize-all-text")
        self.assertEqual(result["full_text"], "hello")

    def test_recognize_file_normalizes_nested_sdk_response(self) -> None:
        sample_path = self._make_sample_file()

        client = AliyunOCRClient(config=self.config)
        dummy_sdk = DummySDKClient()

        with patch.object(client, "_get_sdk_client", return_value=dummy_sdk):
            with patch.object(client, "_build_request", return_value=object()):
                with patch.object(dummy_sdk, "recognize_all_text", return_value=DummyNestedResponse()):
                    result = client.recognize_file(sample_path)

        self.assertEqual(result.request_id, "req-body-123")
        self.assertEqual(result.full_text, "嵌套响应文本")
        self.assertEqual(len(result.blocks), 1)
        self.assertEqual(result.blocks[0].text, "嵌套块")
        self.assertEqual(result.blocks[0].bbox, [40, 45, 60, 55])

    def test_from_env_requires_credentials(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch("ocr.client.load_default_env", return_value=None):
                with self.assertRaises(OCRConfigurationError):
                    OCRConfig.from_env()

    def test_rejects_unsupported_file_extension(self) -> None:
        sample_dir = self._temp_root / f"case-{uuid.uuid4().hex}"
        sample_dir.mkdir(parents=True, exist_ok=True)
        sample_path = sample_dir / "sample.txt"
        sample_path.write_text("not valid for OCR", encoding="utf-8")

        client = AliyunOCRClient(config=self.config)

        with self.assertRaises(OCRInputError):
            client.recognize_file(sample_path)

    def test_rejects_invalid_page_number(self) -> None:
        sample_path = self._make_sample_file()
        client = AliyunOCRClient(config=self.config)

        with self.assertRaises(OCRInputError):
            client.recognize_file(sample_path, page_number=0)


if __name__ == "__main__":
    unittest.main()
