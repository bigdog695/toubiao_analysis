from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .llm import LLMClient, MockHeuristicLLMClient
from .ocr_adapter import default_run_ocr, load_mock_ocr_payload
from .real_llm import OpenAICompatibleLLMClient


RuntimeMode = str
MOCK_RUNTIME_MODE = "mock"
REAL_RUNTIME_MODE = "real"
SUPPORTED_RUNTIME_MODES = {MOCK_RUNTIME_MODE, REAL_RUNTIME_MODE}


def validate_runtime_mode(runtime_mode: RuntimeMode) -> None:
    if runtime_mode not in SUPPORTED_RUNTIME_MODES:
        raise ValueError(f"Unsupported runtime_mode: {runtime_mode}")


def build_ocr_runner(
    *,
    runtime_mode: RuntimeMode,
    mock_ocr_dir: str | Path | None = None,
    mock_ocr_file_map: dict[str, str] | None = None,
) -> Callable[[str | Path], Any]:
    validate_runtime_mode(runtime_mode)
    if runtime_mode == MOCK_RUNTIME_MODE:
        return lambda file_path: load_mock_ocr_payload(
            file_path,
            mock_ocr_dir=mock_ocr_dir,
            mock_ocr_file_map=mock_ocr_file_map,
        )
    return default_run_ocr


def build_llm_client(
    *,
    runtime_mode: RuntimeMode,
    real_llm_client: LLMClient | None = None,
) -> LLMClient:
    validate_runtime_mode(runtime_mode)
    if runtime_mode == MOCK_RUNTIME_MODE:
        return MockHeuristicLLMClient()
    if real_llm_client is not None:
        return real_llm_client
    return OpenAICompatibleLLMClient()
