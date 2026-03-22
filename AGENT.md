# AGENT.md

## Project Objective

Build an agent-driven scoring system that automatically evaluates bidding documents against tender requirements.

The system should:

- Extract structured scoring criteria from tender documents
- Retrieve relevant evidence from bidding documents
- Generate explainable scores with LLMs
- Run inside a private deployment environment with controlled external API usage

## Core Problem

Manual bid evaluation is:

- Time-consuming
- Inconsistent across reviewers
- Difficult to audit because reasoning and evidence are often not explicit

This project addresses that by converting:

`unstructured tender/bid documents -> structured criteria -> semantic retrieval -> LLM-based scoring with evidence`

## Current Repository Context

The current repository is an early-stage prototype focused on tender scoring extraction.

Present artifacts:

- `extract_for_llm.py`: extracts tender text and tables into Markdown
- `scoring_criteria_cleaned.md`: sample extracted tender scoring content
- `scoring_criteria.json`: sample structured scoring output
- `plan.txt`: initial architecture notes

This means the full multi-agent pipeline is the target architecture, not yet the implemented system.

## System Overview

The target system contains five cooperating agents:

1. Tender Understanding Agent
2. Bid Processing Agent
3. Retrieval Agent
4. Scoring Agent
5. Orchestrator Agent

The orchestrator owns workflow sequencing, failure handling, and reproducibility.

## Agent Responsibilities

### 1. Tender Understanding Agent

Input:

- Tender PDF

Output:

- Structured scoring schema in JSON

Responsibilities:

- Parse Chapter 2 qualification requirements
- Parse Chapter 3 scoring criteria
- Normalize extracted content into a consistent schema
- Capture, at minimum:
  - `item`
  - `weight`
  - `scoring_rule`
  - `required_evidence`
- Tolerate section title variations and formatting inconsistencies

Suggested output shape:

```json
{
  "tender_id": "string",
  "qualification_requirements": [
    {
      "item": "string",
      "required_evidence": ["string"]
    }
  ],
  "scoring_criteria": [
    {
      "criterion_id": "string",
      "item": "string",
      "weight": 0,
      "scoring_rule": "string",
      "required_evidence": ["string"],
      "source_section": "string"
    }
  ]
}
```

### 2. Bid Processing Agent

Input:

- One or more bid PDFs containing text, tables, and images

Responsibilities:

- Run OCR for scanned/image-based content through an approved external API
- Extract tables with `pdfplumber` or equivalent
- Normalize all extracted content into text chunks with metadata
- Generate embeddings for each chunk
- Store embeddings and metadata in a vector index such as FAISS

Chunk metadata should include:

- `document_id`
- `page_number`
- `chunk_id`
- `content_type` (`text`, `table`, `ocr`)
- `source_span` or extraction trace

### 3. Retrieval Agent

Input:

- Structured scoring criteria
- Bid vector index

Responsibilities:

- Convert each scoring criterion into a retrieval query
- Embed criteria with the configured embedding model
- Perform semantic search over bid chunks
- Return top-K relevant chunks per criterion
- Preserve retrieval scores and chunk metadata for auditability

### 4. Scoring Agent

Input:

- One scoring criterion
- Retrieved evidence chunks

Responsibilities:

- Build the scoring prompt
- Call the configured LLM API
- Produce:
  - `score`
  - `reasoning`
  - `supporting_evidence`
- Ensure outputs are explainable and tied to retrieved text, not unsupported model guesses

Expected output shape:

```json
{
  "criterion_id": "string",
  "score": 0,
  "reasoning": "string",
  "supporting_evidence": [
    {
      "chunk_id": "string",
      "quote": "string"
    }
  ]
}
```

### 5. Orchestrator Agent

Responsibilities:

- Manage the full pipeline end to end
- Coordinate tender parsing, bid ingestion, retrieval, and scoring
- Enforce deterministic workflow execution
- Handle retries, timeouts, and partial failures
- Persist intermediate artifacts for debugging and reproducibility
- Keep model providers and external API usage behind clear interfaces

## End-to-End Data Flow

Tender side:

`Tender PDF -> Tender Understanding Agent -> Scoring JSON -> Embedding-ready criteria`

Bid side:

`Bid PDFs -> OCR / table extraction / text extraction -> normalized chunks -> embeddings -> vector store`

Scoring side:

`Scoring JSON + vector store -> Retrieval Agent -> relevant evidence -> Scoring Agent -> scores + explanations`

## Non-Functional Constraints

### Security

- Do not send raw source documents to external services
- Only send sanitized, minimal text chunks to approved APIs
- Use HTTPS for all external communication
- Maintain a clear internal/external boundary
- Log which content leaves the private environment

### Model Strategy

- Default to international models for initial quality
- Support domestic model replacement without workflow changes
- Treat embedding models, OCR providers, and scoring LLMs as pluggable backends

### Template Variability

- Assume core tender structure is broadly stable
- Allow minor differences in section names and formatting
- Prefer normalization and heuristic robustness over brittle exact matching

## Engineering Principles

- Reproducibility: same inputs should produce stable outputs where possible
- Explainability: every score must be traceable to retrieved evidence
- Modularity: OCR, extraction, embedding, retrieval, and scoring should be separable components
- Privacy by design: minimize external payloads and isolate sensitive content
- Auditability: persist intermediate outputs and metadata

## Recommended Module Boundaries

A practical target layout for future implementation:

```text
src/
  agents/
    tender_agent.py
    bid_agent.py
    retrieval_agent.py
    scoring_agent.py
    orchestrator.py
  extraction/
    pdf_text.py
    table_extract.py
    ocr_client.py
    chunking.py
  retrieval/
    embeddings.py
    vector_store.py
  schemas/
    scoring_schema.py
    scoring_result.py
  prompts/
    scoring_prompt.txt
  app/
    web_demo.py
```

## Milestones

### Week 3

- Retrieval pipeline working
- LLM-based scoring working on sample documents

### Week 4

- End-to-end demo with a web interface

## Success Criteria

- End-to-end automated scoring works on real tender and bid documents
- Scores are reproducible enough for operational use
- Outputs are explainable with supporting evidence
- System runs in a private environment with controlled and secure API usage

## Near-Term Build Priorities

1. Stabilize tender scoring schema extraction from current sample files
2. Define chunk schema and metadata model for bid documents
3. Add embedding and FAISS indexing pipeline
4. Implement criterion-to-evidence retrieval
5. Implement scoring prompt and structured scoring output
6. Add orchestrated end-to-end execution
7. Add lightweight web demo

## Notes For Future Contributors

- Treat `scoring_criteria.json` as a seed example, not a final schema contract
- Keep external provider calls abstracted behind interfaces
- Prefer structured outputs over free-form text between agents
- Preserve source-page references whenever extracting, chunking, retrieving, or scoring
