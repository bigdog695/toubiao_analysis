# Local Semantic Engine

This folder is a standalone implementation for:

- OCR-to-index ingestion
- local semantic storage
- local search for `scoring_model` retrieval hints
- semantic scoring item loading
- prompt construction for LLM-based scoring

It is intentionally isolated from the rest of the repo except for reusing the existing `ocr` package.

## What it includes

- `ingest.py`
  Batch OCR + chunking + local indexing.
- `store.py`
  SQLite-backed local semantic store with metadata filtering and hybrid retrieval.
- `model_loader.py`
  Loads semantic scoring items from `zhaobiao_file_model.json`.
- `prompting.py`
  Builds strict prompts for semantic scoring.
- `scoring.py`
  Semantic scoring runner plus empty result stubs for rule-based and price scoring.
- `demo_adapter.py`
  Converts pipeline score output into the display structure expected by `demo.py`.

## Current design choices

- Metadata and chunks are stored in `SQLite`.
- Embeddings use a local hashing-based provider to avoid adding heavy runtime dependencies in the first pass.
- The storage and scoring interfaces are replaceable later if you want to switch the vector layer to FAISS or another engine.
- Runtime has two modes controlled by one switch:
  - `mock`: uses mock OCR files plus mock heuristic scoring.
  - `real`: uses the real OCR adapter and the built-in HTTP real LLM client.

## Quick usage

List semantic scoring items:

```bash
python -m local_semantic_engine list-semantic-items --model-path zhaobiao_file_model.json
```

Ingest PDFs:

```bash
python -m local_semantic_engine ingest ^
  --project-id demo-project ^
  --store-dir .semantic_store ^
  --model-path zhaobiao_file_model.json ^
  --runtime-mode mock ^
  --mock-ocr-dir .mock_ocr ^
  --doc-types-json doc_types.json ^
  file1.pdf file2.pdf
```

Search:

```bash
python -m local_semantic_engine search ^
  --project-id demo-project ^
  --store-dir .semantic_store ^
  --doc-types construction_plan ^
  --keywords 施工机械设备 设备投入计划 ^
  --queries "施工机械设备配置是否满足施工需要"
```

Semantic scoring:

```bash
python -m local_semantic_engine score ^
  --project-id demo-project ^
  --store-dir .semantic_store ^
  --model-path zhaobiao_file_model.json ^
  --runtime-mode mock
```

End-to-end pipeline:

```bash
python -m local_semantic_engine pipeline ^
  --project-id demo-project ^
  --store-dir .semantic_store ^
  --model-path zhaobiao_file_model.json ^
  --runtime-mode mock ^
  --mock-ocr-dir .mock_ocr ^
  --doc-types-json doc_types.json ^
  file1.pdf file2.pdf
```

## doc_type assignment

Use `--doc-types-json` to pass a JSON object such as:

```json
{
  "商务文件.pdf": "performance_contract",
  "技术文件.pdf": "construction_plan"
}
```

If no assignment is provided, the engine will attempt a keyword-based suggestion and mark the source as `suggested`.

## Mock OCR files

When `--runtime-mode mock` is used, the engine expects OCR payload JSON files with the same shape as `OCRBatchResult.to_dict()`.

Example:

```json
{
  "document_id": "商务文件",
  "provider": "mock-ocr",
  "total_pages": 2,
  "full_text": "整份文件的合并文本",
  "page_results": [
    {
      "document_id": "商务文件",
      "page_number": 1,
      "provider": "mock-ocr",
      "full_text": "第一页文本",
      "blocks": [
        {
          "block_id": "商务文件-p1-b1",
          "text": "项目经理业绩证明材料……",
          "confidence": 1.0,
          "block_type": "paragraph"
        },
        {
          "block_id": "商务文件-p1-t1",
          "text": "| 项目 | 金额 |\\n| --- | --- |\\n| XX工程 | 1200万 |",
          "confidence": 1.0,
          "block_type": "table"
        }
      ],
      "request_id": null,
      "image_type": "mock",
      "width": null,
      "height": null,
      "raw_response": {}
    }
  ]
}
```

File lookup rules:

- `<mock_ocr_dir>/<pdf_stem>.ocr.json`
- `<mock_ocr_dir>/<pdf_name>.ocr.json`
- `<mock_ocr_dir>/<pdf_stem>.json`
- `<mock_ocr_dir>/<pdf_name>.json`

You can also provide `--mock-ocr-map-json` to explicitly map each PDF to its OCR JSON file.

## End-to-end status

You can now run the standalone pipeline end-to-end with one runtime switch:

1. `ingest`
   Reads PDFs, loads matching mock OCR payloads, assigns `doc_type`, chunks text, builds embeddings, and writes into the local store.
2. `search`
   Queries the local store with `doc_type` filters plus keyword/semantic hints.
3. `score`
   Reads `scoring_model`, retrieves evidence for semantic items, and routes scoring through the mock or real LLM implementation selected by `runtime_mode`.
4. `pipeline`
   Runs `ingest + score` under the same `runtime_mode`.

If you want production OCR and production scoring later, switch `--runtime-mode` from `mock` to `real`.

## demo.py integration

`demo.py` currently expects a hand-written payload structure. The adapter in [demo_adapter.py](/C:/Users/kaitao/codes/toubiao_analysis/local_semantic_engine/demo_adapter.py) converts a pipeline report into that shape.

Typical usage:

```python
from local_semantic_engine.demo_adapter import load_pipeline_report, build_demo_payload

report = load_pipeline_report("sample_toubiao_files/mock_score_report.json")
bid_demo_data = build_demo_payload(report)
```

Current ownership split:

- semantic retrieval + LLM scoring: implemented in `local_semantic_engine`
- rule-based scoring items: currently return empty results, `TODO(barry)` in `scoring.py`
- price scoring: currently returns an empty result, `TODO(barry)` in `scoring.py`

## Current behavior by runtime mode

- `mock`
  Uses mock OCR payloads and a heuristic mock scoring client:
  - `hybrid_rule_rag` uses retrieval strength and simple text markers to return pass/fail or tiered award scores.
  - `rag_llm_scoring` maps retrieval strength to rubric levels and returns a midpoint score in the chosen range.
- `real`
  Uses the real OCR path and an HTTP-based OpenAI/Azure OpenAI compatible scoring client.

## Real mode environment variables

For `--runtime-mode real`, configure one provider through environment variables.

OpenAI:

```powershell
$env:LSE_LLM_PROVIDER="openai"
$env:LSE_OPENAI_API_KEY="..."
$env:LSE_LLM_MODEL="gpt-4.1-mini"
# optional
$env:LSE_OPENAI_BASE_URL="https://api.openai.com/v1"
$env:LSE_LLM_TIMEOUT_SECONDS="120"
```

Azure OpenAI:

```powershell
$env:LSE_LLM_PROVIDER="azure_openai"
$env:LSE_AZURE_OPENAI_API_KEY="..."
$env:LSE_AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
$env:LSE_AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
$env:LSE_AZURE_OPENAI_API_VERSION="2024-10-21"
$env:LSE_LLM_MODEL="gpt-4.1-mini"
```

The real client implementation is in [real_llm.py](/C:/Users/kaitao/codes/toubiao_analysis/local_semantic_engine/real_llm.py).
