# OCR Component

This folder contains the Aliyun OCR integration for the project.

## Setup

1. Copy `ocr/.env.example` to `ocr/.env`
2. Fill in:
   - `ALIBABA_CLOUD_ACCESS_KEY_ID`
   - `ALIBABA_CLOUD_ACCESS_KEY_SECRET`
3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Public API

Use the callable function:

```python
from ocr import recognize_document

result = recognize_document("sample.png", image_type="Advanced")
```

The function returns a normalized dictionary containing:

- `document_id`
- `provider`
- `total_pages`
- `full_text`
- `page_results`

## Expected Input

The current implementation accepts one document per call.

Supported input sources:

- Local file path
- Remote URL

Supported file types:

- `PDF`
- `PNG`
- `JPG`
- `JPEG`
- `BMP`
- `GIF`
- `TIFF`
- `WebP`

Current limitations:

- No multi-document batch endpoint yet
- One document per request
- Oversized PDFs are automatically split into page images and OCR'd page by page
- Small PDFs can still go through as a direct PDF request

Aliyun API limits:

- Uploaded binary file must be `<= 10MB`
- Width and height must be `> 15px` and `< 8192px`
- Aspect ratio must be `< 50`

Example:

```python
from ocr import recognize_document

result = recognize_document("ocr/test_ocr.pdf")
```

## Live Self-Test

Run a real OCR request against Aliyun:

```bash
python -m ocr.selftest --file path/to/file.png --type Advanced --json
```

For PDF input:

```bash
python -m ocr.selftest --file path/to/file.pdf --json > ocr_result.json
```

## Notes

- This implementation uses Aliyun `RecognizeAllText`.
- `Type=Advanced` is the default because it is the best fit for mixed document OCR.
- The API supports PNG, JPG, JPEG, BMP, GIF, TIFF, WebP, and PDF.
- The request size limit is 10MB per file according to the official API documentation.
- Oversized PDFs are rendered to page images automatically before OCR.
