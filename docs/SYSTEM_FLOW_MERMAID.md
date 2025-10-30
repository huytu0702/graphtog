### System Flow (GraphToG Backend)

This document visualizes the current backend flows discovered in `app/main.py`, `api/endpoints/*`, and `services/*`.

#### Application Lifecycle

```mermaid
flowchart TD
    A[FastAPI app start] --> B[Init PostgreSQL]
    A --> C[Init Neo4j]
    A --> D[Init Graph Schema]
    A -. include .-> E[/Routers/]
    E --> E1[/Auth/]
    E --> E2[/Documents/]
    E --> E3[/Queries/]
    E --> E4[/Communities/]
    E --> E5[/Advanced Extract/]
    E --> E6[/Visualization/]
    E --> E7[/Cache/]
    E --> E8[/Retrieval/]
    E --> E9[/Analyze/]
    subgraph Shutdown
      S1[Close Neo4j]
    end
    A -->|on shutdown| S1
```

#### Document Upload and Processing (GraphRAG Pipeline)

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as POST /api/documents/upload
    participant DB as Postgres
    participant BG as BackgroundTasks
    participant DP as document_processor
    participant GS as graph_service
    participant EMB as embedding_service
    participant LLM as llm_service
    participant ER as entity_resolution_service
    participant CD as community_detection_service
    participant CS as community_summarization_service

    FE->>API: Upload .md file
    API->>DB: Insert Document(status=processing)
    API->>BG: add_task(process_document)
    BG->>DP: process_document_with_graph(doc_id, file_path, db)

    DP->>DP: parse_md(file)
    DP->>GS: init_schema()
    DP->>GS: create_document_node()
    DP->>DP: chunking_service.create_chunks()
    loop for each chunk
        DP->>GS: create_textunit_node()
    end
    DP->>EMB: generate_and_store_embeddings(pgvector)

    DP->>LLM: batch_extract_entities(chunks)
    loop entities per chunk
        DP->>GS: create_or_merge_entity()
        DP->>GS: create_mention_relationship()
    end

    alt ENABLE_ENTITY_RESOLUTION
        DP->>ER: find_duplicate_entity_pairs()
        ER-->>DP: candidate pairs
        opt LLM-assisted resolution
            DP->>ER: resolve_with_llm()
        end
        DP->>ER: merge_entities()
    end

    DP->>LLM: batch_extract_relationships()
    DP->>GS: create_relationship(source->target)

    DP->>LLM: batch_extract_claims()
    DP->>GS: create_claim_node() and links

    DP->>CD: detect_communities(Leiden)
    DP->>CS: summarize_all_communities()

    DP->>DB: update Document(status=completed, progress=100)
    API-->>FE: {id, filename, status}
```

#### Incremental Reprocessing

```mermaid
flowchart LR
    U[PUT /api/documents/{id}/update] --> P[Parse new content]
    P --> H[Compute SHA256 hash]
    H -- "unchanged" --> SKIP[Skip reprocessing]
    H -- "changed" --> M[Mark status=processing; ++version]
    M --> A[Get affected communities]
    A --> C[Delete old graph data for document]
    C --> R[Re-run full pipeline]
    R --> I[Incremental community detection (if any affected)]
    I --> F[Update metadata and finish]
```

#### Query Processing (Entity-centric GraphRAG)

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant QAPI as POST /api/queries
    participant QS as query_service
    participant GS as graph_service
    participant LLM as llm_service
    participant DB as Postgres

    FE->>QAPI: {query, hop_limit, document_id?}
    QAPI->>QS: process_query()
    QS->>LLM: classify_query()
    alt entities found
        QS->>GS: find_entity_by_name()
    else none
        QS->>GS: get_top_entities(limit=10, document_id?)
    end
    loop for each entity
        QS->>GS: get_entity_context(hop_limit)
        Note right of QS: include related entities + text units
    end
    QS->>LLM: generate_answer(query, context, citations)
    QAPI->>DB: save Query(query_mode, response, reasoning_chain,...)
    QAPI-->>FE: {answer, context, citations, confidence}
```

#### Global Query with Map-Reduce (Summaries-based)

```mermaid
flowchart TD
    A[POST /api/queries/global] --> B[retrieval_service.retrieve_global_context(use_summaries=true)]
    B -->|no summaries| E[Error: process documents first]
    B --> C{Use Map-Reduce?}
    C -- Yes --> M1[Map: split communities into batches]
    M1 --> M2[LLM summarize_community_batch per batch]
    M2 --> R[Reduce: synthesize_final_answer]
    C -- No --> S[Assemble summaries into context]
    S --> R
    R --> O[Return answer + confidence + metadata]
```


