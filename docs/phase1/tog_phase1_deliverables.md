# Tree of Graphs – Phase 1 Deliverables

**Date:** 2025-11-03  
**Owner:** GraphToG Core Team  
**Scope:** Phase 1 – Foundation & Analysis from `tog_implementation_plan.md`

---

## Task 1.1 – Code Architecture Analysis

### Current Query Processing Flow
```
Frontend -> FastAPI router (`backend/app/api/endpoints/queries.py`)
          -> `QueryService.process_query` (pending ToG integration)
             -> Graph access via `GraphService` (`backend/app/services/graph_service.py`)
             -> LLM prompts via `LLMService` (`backend/app/services/llm_service.py`)
             -> Response serialization -> PostgreSQL persistence (`backend/app/models/query.py`)
```

- Authentication is enforced through `get_current_user` in `queries.py` before any processing.
- Neo4j access is centralized in `GraphService`; all Cypher is issued through a lazily created session.
- Prompt construction and Gemini calls are encapsulated in `LLMService`, keeping prompt variants in `prompt.py`.

### Component Dependency Map

| Layer | Key Modules | Depends On | Notes |
| --- | --- | --- | --- |
| API | `app/api/endpoints/queries.py` | `query_service`, `graph_service`, SQLAlchemy session | Entry point for query submission, retrieval, and analytics. |
| Services | `graph_service.py` | `app.db.neo4j`, Neo4j driver | Handles node/edge CRUD, community detection, traversal utilities. |
| Services | `llm_service.py` | Google Gemini SDK, `prompt.py` | Provides all LLM-backed extraction, summarization, and classification calls. |
| Services | `prompt.py` | N/A | Houses prompt templates and builders for extraction, classification, summarization. |
| Persistence | `app/db/postgres.py`, `app/models/*` | SQLAlchemy, PostgreSQL | Stores user, document, and query metadata. |
| Auth | `app/services/auth.py`, `app/services/security.py` | JWT, NextAuth session context | Validates users before API access. |

### Integration Points for ToG

| Integration Area | Current Component | Planned Extension | Notes |
| --- | --- | --- | --- |
| Query orchestration | `QueryService` (stub) | ToG controller to decide GraphRAG vs. ToG | Implement strategy selector + reasoning trace capture. |
| Graph traversal | `GraphService` | ToG traversal hooks (multi-hop, pruning metadata) | Reuse existing node/edge fetch + add traversal-specific Cypher helpers. |
| Prompting | `prompt.py` | ToG-specific relation/entity/sufficiency prompts | Map ToG prompt templates to Gemini-friendly formats. |
| Caching | `cache_service.py` | Store intermediate ToG states | Avoid redundant traversals for repeated sub-queries. |
| Analytics | `queries.py` responses | Return reasoning paths & sufficiency flags | Ensure backward compatibility with existing response schema. |

---

## Task 1.2 – Neo4j Graph Schema Review

### Node Types in Use

| Label | Key Properties | Purpose |
| --- | --- | --- |
| `Document` | `id`, `name`, `file_path`, `status`, timestamps | Top-level container for uploaded files (`graph_service.py`:86-137). |
| `TextUnit` | `id`, `document_id`, `text`, `start_char`, `end_char` | Chunked passages linked via `(:TextUnit)-[:PART_OF]->(:Document)` (lines 139-207). |
| `Entity` | `id`, `name`, `type`, `description`, `confidence` | Canonicalized entities extracted from documents (lines 211-314). |
| `Community` | `id`, `level`, `summary`, `size` | Leiden clusters generated in `community_detection.py` (lines 52-388). |
| `Claim` | `id`, `claim_text`, `claim_type`, `status`, `confidence` | Structured claims extracted by advanced pipelines (lines 598-706). |

### Relationship Types

| Relationship | Direction | Description | Source |
| --- | --- | --- | --- |
| `(:TextUnit)-[:PART_OF]->(:Document)` | Outbound from chunk | Document composition (graph_service lines 166-202). |
| `(:Entity)-[:MENTIONED_IN]->(:TextUnit)` | Entity → chunk | Entity occurrences with offsets and confidence (lines 215-354). |
| `(:Entity)-[:RELATED_TO]->(:Entity)` | Undirected | Semantic/relational edge with `type`, `description`, `confidence` (lines 305-366). |
| `(:Entity)-[:IN_COMMUNITY]->(:Community)` | Entity → community | Community assignment (community_detection lines 214-304). |
| `(:Claim)-[:ABOUT]->(:Entity)` | Claim → entity | Links claim to its subject(s) (graph_service lines 650-704). |
| `(:Claim)-[:SUPPORTED_BY]->(:TextUnit)` | Claim → evidence | Evidence tracking (graph_service lines 705-740). |

### Schema Validation Queries

```cypher
// Connectivity around an entity (up to 3 hops)
MATCH (e:Entity {name: $entity})-[:RELATED_TO*1..3]-(neighbor:Entity)
RETURN e, neighbor LIMIT 50;

// Relationship distribution for pruning heuristics
MATCH ()-[r:RELATED_TO]->()
RETURN r.type AS relation_type, count(*) AS frequency
ORDER BY frequency DESC;

// Community completeness check
MATCH (c:Community)<-[:IN_COMMUNITY]-(e:Entity)
RETURN c.id AS community, count(e) AS entity_count
ORDER BY entity_count DESC;
```

### Observations & Gaps

- Constraints/indexes already cover uniqueness for `Entity`, `Document`, `TextUnit`, `Community`, and `Claim`. No explicit constraint for `RELATED_TO` edge uniqueness; ToG pruning should tolerate duplicate relations or add composite keys if needed.
- `GraphService.get_entity_graph_view` (`graph_service.py`:449-546) returns multi-hop neighborhoods suitable for ToG expansion with minor adjustments to expose edge confidence.
- `GraphService.search_entities` (`graph_service.py`:738-781) provides text + type search and is a candidate for ToG entry-point entity lookups.
- Need lightweight metadata on relationships (e.g., extraction method) to inform pruning strategies; consider adding `source`/`weight`.

---

## Task 1.3 – ToG Algorithm Deep Dive

### High-Level Flow (`main_freebase.py`)

1. Initialize parameters (`width`, `depth`, `temperature_*`, `num_retain_entity`).
2. For each depth level:
   - Call `relation_search_prune` to score relations per entity using LLM prompting.
   - Expand candidate entities via `entity_search`.
   - Score and prune entities using `entity_score` + `entity_prune`.
3. After exploration, run `reasoning` to combine traversed paths and answer; fallback to `generate_without_explored_paths`.

### Prompt Usage (`prompt_list.py`)

- `extract_relation_prompt`: Asks LLM to produce top-k relations with normalized scores.
- `score_entity_candidates_prompt`: Scores entity candidates conditioned on relation and question context.
- `answer_prompt`: Aggregates selected triplets and performs sufficiency reasoning; includes fallback guidance when knowledge is incomplete.

### Scoring & Pruning Mechanics

- **Relations**: Top-scored relations normalized to sum 1; used to weight downstream entity scoring.
- **Entities**: Weighted by combination of relation score and LLM-evaluated relevance; `entity_prune` retains highest aggregate scores given `width` constraint.
- **Sufficiency**: `reasoning` evaluates if current chain covers the question; uses prompts to decide whether to continue or finalize.
- **Fallback**: `half_stop` persists partial chains; `generate_without_explored_paths` triggers direct answer generation when traversal stalls.

### Hyperparameters & Defaults

| Parameter | Default | Role | GraphToG Adaptation |
| --- | --- | --- | --- |
| `width` | 3 | Max children explored per expansion | Align with average `RELATED_TO` degree to avoid combinatorial blow-up. |
| `depth` | 3 | Max traversal depth | Map to community levels (Document → Entity → Community). |
| `temperature_exploration` | 0.4 | Encourage breadth in exploration stage | Translate to Gemini 2.5 Flash equivalents. |
| `temperature_reasoning` | 0 | Deterministic answer synthesis | Maintain low temp for consistent reasoning traces. |
| `num_retain_entity` | 5 | Candidate entities kept per relation | Tune using entity confidence distribution from GraphRAG. |

---

## Task 1.4 – Design Adaptation Strategy

### Schema Mapping (Freebase → GraphRAG)

| ToG Concept | Freebase Source | GraphToG Equivalent | Adaptation Notes |
| --- | --- | --- | --- |
| Topic Entity | Identified by `topic_entity` ID | Entity nodes resolved via `Entity` label | Seeded from `GraphService.search_entities` or query classification. |
| Relation | Stable Freebase predicate | `RELATED_TO.type` (LLM-extracted) | Normalize relation labels (lemmatize, collapse aliases). |
| Evidence Node | Neighbor entity in KG | `Entity` or `Community` nodes | Communities act as meta-entities for summarization. |
| Triplet | `(head, relation, tail)` | `(Entity)-[:RELATED_TO]->(Entity)` + metadata | Include `MENTIONED_IN` TextUnits as provenance. |
| Sufficiency Check | LLM check over triplets | Gemini call with graph context | Use `build_contextual_answer_prompt` foundation. |

### Adapted Traversal Pseudocode

1. Resolve initial entities from query classification (GraphRAG mode fallback).
2. For each entity, fetch candidate relations via Cypher summarizing `RELATED_TO` edges with confidence.
3. Rank relations using ToG-style prompt adapted to GraphRAG metadata (include summaries, community labels).
4. Expand neighbor entities, merging duplicates by canonical `Entity.id`.
5. Record provenance (TextUnits, claims) for each edge to surface in reasoning chain.
6. Evaluate sufficiency; if insufficient, iterate depth or switch to community summary retrieval.

### Handling Community Structure

- Use community summaries (`community_summarization.py`:142-312) as macro nodes when `width` pruning removes granular entities.
- Maintain dual queues: entity-level traversal and community-level expansion for hierarchical reasoning.
- Cache community subgraphs keyed by `community_id` in `cache_service.py` to accelerate repeated hops.

### Required Schema Enhancements (Optional)

- Add `importance` or `weight` property to `RELATED_TO` during extraction (`advanced_extraction.py`) to seed scores.
- Introduce `:PATH_STEP` meta-nodes only if ToG reasoning trace persistence is needed; otherwise serialize in PostgreSQL.

---

## Task 1.5 – API Design & Specifications

### Request Schema (JSON)

```jsonc
{
  "query": "How does Project X relate to Company Y?",
  "mode": "auto",              // auto | graphrag | tog | hybrid
  "hop_limit": 2,              // Backward-compatible with existing field
  "tog_config": {
    "width": 3,
    "depth": 3,
    "temperature_exploration": 0.4,
    "temperature_reasoning": 0.0,
    "num_retain_entity": 5
  },
  "document_id": "optional-document-uuid"
}
```

- `mode` defaults to `auto`; legacy clients can omit and keep GraphRAG-only flow.
- `tog_config` is optional; defaults align with Table above.

### Response Schema

```jsonc
{
  "answer": "string",
  "sources": [
    {
      "text_unit_id": "uuid",
      "document_id": "uuid",
      "excerpt": "string"
    }
  ],
  "reasoning": {
    "strategy": "tog",
    "depth_reached": 3,
    "path": [
      {
        "step": 1,
        "entity": {"id": "E1", "name": "Entity A", "type": "Organization"},
        "relation": {"type": "PARTNERS_WITH", "score": 0.42},
        "target": {"id": "E2", "name": "Entity B", "type": "Project"},
        "evidence": [{"text_unit_id": "T5", "claim_id": "C2"}]
      }
    ],
    "sufficiency": {
      "status": "complete",
      "confidence": 0.78,
      "notes": "Gemini evaluation summary"
    }
  },
  "query_type": "tog",
  "confidence_score": "0.78"
}
```

- `reasoning` block is self-contained for LangGraph + LangSmith tracing.
- Preserve existing fields (`answer`, `sources`, `query_type`, `confidence_score`) for compatibility.

### Backward Compatibility & Versioning

- Maintain current POST `/queries` signature; add optional fields only.
- Include `X-GraphToG-Mode` response header summarizing final strategy.
- Document breaking changes in `docs/api/query.md`; plan API v1.1 tag once ToG ships.
- Store reasoning path JSON in PostgreSQL via `Query.reasoning_chain` (already string field) for audit trails.

### Implementation Backlog

1. Flesh out `query_service.py` with strategy selection glue code.
2. Implement ToG traversal helpers in a new `tog_service.py` built atop `graph_service`.
3. Extend `prompt.py` with Gemini-optimized ToG prompts mirroring `prompt_list.py`.
4. Add integration tests covering GraphRAG-only, ToG-only, and hybrid flows.

---

## Next Steps (Post Phase 1)

- Prototype ToG traversal service using above pseudocode.
- Validate prompt adaptations with Gemini using sample graph slices.
- Align community-level reasoning output with frontend visualization requirements.
- Prepare caching strategy spikes (Redis vs. in-memory) before Phase 2 execution.
