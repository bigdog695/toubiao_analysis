# OCR Folder Instructions

## Scope

These instructions apply to work inside the `ocr/` folder and take precedence over the root `AGENT.md` for OCR-related files in this subtree.

## Objective

Build the OCR layer for bid and tender document ingestion.

This folder is responsible for turning scanned or image-based PDF content into normalized, traceable text that can be passed to downstream chunking, retrieval, and scoring components.

## Responsibilities

- Detect pages or regions that require OCR
- Extract page images or image regions from PDFs
- Call the configured OCR provider through a pluggable client
- Normalize OCR output into clean text plus structured metadata
- Preserve page-level and block-level traceability
- Avoid leaking raw documents outside approved boundaries

## Required Output Contract

OCR outputs should preserve enough structure for downstream use.

Minimum fields:

```json
{
  "document_id": "string",
  "page_number": 1,
  "blocks": [
    {
      "block_id": "string",
      "text": "string",
      "bbox": [0, 0, 0, 0],
      "confidence": 0.0
    }
  ],
  "full_text": "string",
  "provider": "string"
}
```

## Input Contract

The current OCR component accepts one input per call.

Supported inputs:

- Local file path
- Remote URL

Supported file types:

- PDF
- PNG
- JPG
- JPEG
- BMP
- GIF
- TIFF
- WebP

Current behavior:

- One document per OCR request
- Small PDFs can be sent directly
- Oversized PDFs are automatically split into page images and OCR'd page by page
- The output is aggregated into one document-level result with per-page payloads
- Multi-document batch OCR is not implemented in this folder yet; callers should loop over documents

Input restrictions from the Aliyun API:

- Binary upload size must be `<= 10MB`
- Image width and height must be `> 15px` and `< 8192px`
- Aspect ratio must be `< 50`

Operational guidance:

- Prefer PDF for source documents when available
- Prefer page-by-page processing for large PDFs
- Reject unsupported file extensions before making API calls
- Preserve page number in every OCR result

## Constraints

- Do not send full raw PDFs to external APIs unless explicitly approved by the system design
- Prefer sending page images or sanitized subsets only
- Keep OCR provider access behind an interface so domestic providers can replace international ones
- Keep deterministic preprocessing where possible
- Log provider name, page number, and request boundaries for auditability

## Implementation Guidance

- Put OCR provider adapters in this folder
- Separate preprocessing, provider calls, and postprocessing into distinct modules
- Keep data contracts structured and typed
- Preserve original page number and coordinate metadata whenever available
- Normalize whitespace and obvious OCR artifacts, but do not silently discard uncertain content

## Near-Term Priorities

1. Define OCR input and output schemas
2. Add PDF page/image extraction utilities
3. Add a pluggable OCR client interface
4. Implement one provider adapter behind that interface
5. Add normalization and traceability metadata
6. Add sample-driven tests for mixed scanned/text PDFs

## Self-Test

Use two levels of testing.

Unit tests:

```bash
python -m unittest discover -s ocr/tests -v
```

Live OCR test with Aliyun:

1. Create `ocr/.env` from `ocr/.env.example`
2. Fill in:
   - `ALIBABA_CLOUD_ACCESS_KEY_ID`
   - `ALIBABA_CLOUD_ACCESS_KEY_SECRET`
3. Run:

```bash
python -m ocr.selftest --file ocr/test_ocr.pdf --json > ocr/test_ocr_result.json
```

Expected result:

- Exit code `0`
- Output file `ocr/test_ocr_result.json` created
- OCR text available in document `full_text`
- Per-page results available in `page_results`

## Suggested Layout

```text
ocr/
  AGENT.md
  schemas.py
  preprocess.py
  client.py
  providers/
    base.py
    provider_x.py
  normalize.py
  tests/
```
