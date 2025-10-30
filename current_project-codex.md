# GraphToG vs Microsoft GraphRAG – Codex Comparison

## Sources Reviewed
- `backend/app/services/document_processor.py`, `chunking.py`, `embedding_service.py`, `entity_resolution.py`, `graph_service.py`, `community_detection.py`, `community_summarization.py`, `retrieval_service.py`, `query_service.py`, `llm_service.py`, `cache_service.py`, `prompt.py`
- GraphRAG public docs: Welcome, Getting Started, Index → Inputs & Outputs, Query → Overview, Config → Overview, Prompt Tuning → Overview

## Executive Highlights
- GraphToG mirrors GraphRAG’s indexing loop (chunking, entity/relationship/claim extraction, Leiden communities, summaries) but currently limits ingestion to Markdown uploads and stores outputs in PostgreSQL + Neo4j rather than parquet tables.
- The query layer delivers multi-level retrieval and reasoning chains comparable to GraphRAG’s local/global search and adds claims analytics, yet DRIFT search, basic vector-only mode, and question generation from the GraphRAG toolset are absent.
- GraphToG packages production-grade services (FastAPI API surface, authentication, Redis cache, pgvector embeddings, Dockerized stack, Next.js frontend) instead of GraphRAG’s CLI-first workflow.
- Documentation promises LangGraph agent orchestration, LangSmith tracing, and formal Tree of Graphs reasoning; none of these components appear in the current backend code, and prompt auto-tuning/config parity with GraphRAG remain open gaps.

## Capability Comparison
| Capability | GraphRAG Reference | GraphToG Implementation | Status | Notes |
| --- | --- | --- | --- | --- |
| Document ingestion & chunking | Index → Inputs (txt/csv/json, DataFrame ingestion, chunk config) | Markdown-only upload via `/api/documents` with chunking, hashing, and progress callbacks in `backend/app/services/document_processor.py` + `chunking.py` | Partial | Needs additional formats/connectors to match GraphRAG flexibility. |
| Incremental indexing & storage | Index → Outputs (parquet tables for documents/entities/relationships/communities/covariates) | PostgreSQL models + Neo4j graph with versioned documents and incremental reprocessing in `document_processor.py` and `graph_service.py` | Extended | Adds change detection, cleanup, and reprocessing beyond baseline; diverges from parquet storage. |
| Entity/relationship extraction | Index → Methods (LLM tuple extraction) | Gemini-powered extraction, dedup, and confidence merging in `llm_service.py` + `entity_resolution.py`, persisted through `graph_service.py` | Implemented | Adheres to tuple schema while adding coreference logic. |
| Claim/covariate detection | Index → Outputs (covariates table) | Batch claim extraction and linking to entities/text units in `document_processor.py` and `graph_service.py` | Implemented | Mirrors GraphRAG covariate concept with REST exposure. |
| Community detection & summaries | Index → Architecture (Leiden communities + reports) | Neo4j GDS Leiden via `community_detection.py` and Gemini summaries via `community_summarization.py` | Implemented | Supports incremental subgraph recomputation and rich metadata. |
| Query modes | Query → Overview (Local, Global, DRIFT, Basic, Question Generation) | Hierarchical local/community/global retrieval in `retrieval_service.py`, synthesis and reasoning steps in `query_service.py` | Partial | DRIFT search, basic vector-only mode, and question generation still missing. |
| Prompt tuning | Prompt Tuning docs (auto/manual workflows) | Static prompt templates in `backend/app/services/prompt.py`; no feedback-driven tuning loop | Gap | Requires tooling to approach GraphRAG’s tuning guidance. |
| Configuration & operations | Getting Started / CLI (`graphrag init/index/query`, `settings.yaml`) | FastAPI app (`backend/app/main.py`), Docker Compose, env-driven `config.py`; no CLI parity | Divergent | API-first stack; consider wrappers for CLI workflows. |
| Performance features | GraphRAG batch CLI execution | Redis caching (`cache_service.py`), pgvector embeddings (`embedding_service.py`), async progress reporting | Extended | Provides runtime optimizations not in core GraphRAG release. |
| ToG / LangGraph agent | Project roadmap extensions; not in base GraphRAG | No LangGraph code in backend; reasoning chains tracked in `query_service.py` | Planned | LangGraph orchestration and LangSmith tracing remain to be built. |

## Detailed Notes
### Indexing Pipeline
- GraphRAG ingests txt/csv/json or DataFrame sources, applies configurable chunk sizing/overlap, and writes parquet outputs for `documents`, `text_units`, `entities`, `relationships`, `communities`, `community_reports`, and `covariates` (GraphRAG docs – Index → Inputs & Outputs).
- GraphToG processes Markdown uploads through `/api/documents`, validates format, chunks text, generates embeddings, extracts entities/relationships/claims, and manages Neo4j schema initialization and cleanup (`document_processor.py`, `graph_service.py`, `embedding_service.py`). Incremental update logic reprocesses only affected entities and communities, surpassing GraphRAG’s all-or-nothing indexing flow.

### Query Subsystem
- GraphRAG’s query engine exposes Local, Global, DRIFT, Basic, and Question Generation modes (GraphRAG docs – Query → Overview).
- GraphToG classifies queries, retrieves local/community/global contexts, aggregates reasoning steps, and synthesizes answers via Gemini (`query_service.py`, `retrieval_service.py`, `llm_service.py`). There is no DRIFT-style community-augmented local search, vector-only fallback API, or follow-up question generator yet.

### Prompting and Model Management
- GraphRAG provides auto/manual prompt tuning pipelines with configuration handled in `settings.yaml`.
- GraphToG centralizes prompt templates in `prompt.py` and depends on manual prompt editing; the backend lacks automated evaluation, versioning, or configuration tooling comparable to GraphRAG’s tuning guidance (`config.py` controls env settings only).

### Operational Tooling
- GraphRAG is packaged as a CLI using `graphrag init/index/query` (Getting Started documentation) with `uv/poe` tasks and parquet artifacts.
- GraphToG offers a production backend: FastAPI with CORS, authentication (`backend/app/api/endpoints/auth.py`), admin and community endpoints, Dockerized dependencies (PostgreSQL, Neo4j, Redis), and a Next.js frontend. Bridging to CLI-style workflows would ease migration for teams familiar with GraphRAG tooling.

### GraphToG Enhancements
- Incremental document reprocessing, entity resolution with confidence merging, Redis caching, pgvector embeddings, and progress callbacks deliver operational maturity beyond the open-source GraphRAG baseline.
- Query responses capture reasoning steps and expose claims/graph analytics over REST (`backend/app/api/endpoints/queries.py`), extending GraphRAG’s functionality into an API-driven product.

### Gaps to Close
- Implement DRIFT search, basic vector-only retrieval, and question generation to align with GraphRAG’s query engine.
- Add prompt tuning workflows, richer configuration (settings parity, CLI wrappers), and modular ingestion (txt/csv/json, BYO DataFrame, external connectors).
- Build the roadmap items—LangGraph agent orchestration, LangSmith tracing, and concrete Tree of Graphs planners—to fulfill the documented vision.
