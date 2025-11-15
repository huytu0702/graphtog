# GraphToG Information Retrieval Flow: Complete Technical Documentation

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Query Processing Pipeline](#query-processing-pipeline)
4. [Neo4j Graph Database Retrieval](#neo4j-graph-database-retrieval)
5. [PostgreSQL Metadata Retrieval](#postgresql-metadata-retrieval)
6. [LLM Integration and Processing](#llm-integration-and-processing)
7. [Tree of Graphs (ToG) Reasoning Engine](#tree-of-graphs-tog-reasoning-engine)
8. [Pruning Strategies](#pruning-strategies)
9. [Answer Generation Workflow](#answer-generation-workflow)
10. [Data Flow Diagrams](#data-flow-diagrams)
11. [Code References](#code-references)

---

## Overview

GraphToG implements a sophisticated multi-hop reasoning system using **Tree of Graphs (ToG) methodology** to answer complex questions that require traversing relationships in a knowledge graph. The system combines:

- **Neo4j** for graph storage and traversal (entities, relationships, text units)
- **PostgreSQL** for relational metadata (users, documents, query history)
- **Google Gemini 2.5 Flash** (LLM) for entity extraction, relation scoring, and answer generation
- **Redis** for caching (optional performance optimization)

The information retrieval flow involves multiple stages of graph exploration, LLM-guided pruning, and iterative refinement to construct a reasoning path that supports the final answer.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Query                               │
│                    "What connects X to Y?"                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ToG API Endpoint                              │
│              (POST /api/tog/query)                               │
│   - Receives question and ToGConfig                              │
│   - Authenticates user (JWT)                                     │
│   - Initializes ToG service                                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ToG Service (Core Engine)                       │
│                                                                  │
│  1. Topic Entity Extraction (LLM + Fuzzy Match)                 │
│  2. Iterative Graph Exploration (Multi-hop)                     │
│  3. Relation Scoring (Pruning Method)                           │
│  4. Entity Scoring (Pruning Method)                             │
│  5. Sufficiency Check (LLM)                                     │
│  6. Answer Generation (LLM + Context)                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Neo4j      │  │  LLM Service │  │ PostgreSQL   │
│              │  │              │  │              │
│ - Entities   │  │ - Gemini API │  │ - User info  │
│ - Relations  │  │ - Prompts    │  │ - Queries    │
│ - TextUnits  │  │ - Parsing    │  │ - Documents  │
│ - Communities│  │ - Rate limit │  │ - History    │
└──────────────┘  └──────────────┘  └──────────────┘
          │              │              │
          └──────────────┼──────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ToG Reasoning Path                            │
│                                                                  │
│  - Exploration steps (depth-by-depth)                           │
│  - Retrieved entities and relations                             │
│  - Triplets (subject-relation-object)                           │
│  - Sufficiency scores                                           │
│  - Final answer with confidence                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Response to User                               │
│                                                                  │
│  - Answer text                                                   │
│  - Confidence score                                              │
│  - Reasoning path (for visualization)                           │
│  - Query ID (for future reference)                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Query Processing Pipeline

### Phase 1: Query Reception and Initialization

**Location:** `backend/app/api/endpoints/tog.py:146-184`

```python
@router.post("/query", response_model=ToGQueryResponse)
async def tog_query(request: ToGQueryRequest, current_user: User, db: Session):
    # 1. Authenticate user (JWT token validation)
    # 2. Extract question and ToGConfig from request
    # 3. Convert schema config to service config
    config = ToGConfig(
        search_width=request.config.search_width,
        search_depth=request.config.search_depth,
        num_retain_entity=request.config.num_retain_entity,
        exploration_temp=request.config.exploration_temp,
        reasoning_temp=request.config.reasoning_temp,
        pruning_method=request.config.pruning_method,
        enable_sufficiency_check=request.config.enable_sufficiency_check,
        document_ids=request.document_ids,
    )

    # 4. Process query with ToG reasoning
    reasoning_path = await tog_service.process_query(request.question, config)
```

**Data Sources:**
- **PostgreSQL**: User authentication via `get_current_user()` dependency
- **Request Payload**: Question text and configuration parameters

**Key Configuration Parameters:**
- `search_width`: Max relations to explore per depth (default: 3)
- `search_depth`: Max traversal depth for multi-hop reasoning (default: 3)
- `num_retain_entity`: Max entities to keep at each level (default: 5)
- `pruning_method`: "llm", "bm25", or "sentence_bert" (default: "llm")
- `enable_sufficiency_check`: Evaluate if info is sufficient (default: true)
- `exploration_temp`: LLM temperature for exploration (default: 0.4)
- `reasoning_temp`: LLM temperature for final answer (default: 0.0)

---

### Phase 2: Topic Entity Extraction

**Location:** `backend/app/services/tog_service.py:178-239`

This phase identifies the **starting entities** from the user's question by querying the graph and using LLM to match entities.

#### Step 2.1: Get Available Entities from Neo4j

**Location:** `tog_service.py:241-262`

```cypher
MATCH (e:Entity)
[WHERE e.document_id IN $document_ids]  -- Optional filter
WITH DISTINCT e.name as name, e.mention_count as mention_count
RETURN name
ORDER BY mention_count DESC
LIMIT 1000
```

**Purpose:** Retrieve up to 1000 entity names from the graph, optionally filtered by document IDs.

**Graph Schema Used:**
- **Node**: `Entity` with properties: `name`, `mention_count`, `document_id`
- **Index**: `entity_name_lookup`, `entity_document`, `entity_mention_count` (for optimization)

**Output:** List of entity names like `["PERSON_A", "ORGANIZATION_B", "CONCEPT_C"]`

---

#### Step 2.2: LLM-Based Topic Entity Extraction

**Location:** `tog_service.py:200-217`

**Prompt:** `TOG_TOPIC_ENTITY_EXTRACTION_PROMPT` from `backend/app/services/prompt.py:883-901`

```
Given a question and a list of available entities from a knowledge graph,
identify which entities are mentioned or relevant to answering the question.

Question: {question}
Available Entities: {available_entities}

Return JSON: {
    "topic_entities": ["Entity1", "Entity2", "Entity3"]
}
```

**LLM Call:**
```python
response = await llm_service.generate_text(
    prompt=prompt,
    temperature=0.2  # Low temperature for consistent extraction
)
result = llm_service._parse_json_response(response)
topic_entities = result.get("topic_entities", [])
```

**LLM Service Details:**
- **Model**: Google Gemini 2.5 Flash (`gemini-2.5-flash`)
- **Rate Limiting**: 60 requests/minute (1 request per second)
- **Retry Logic**: Exponential backoff with 3 max retries
- **Response Parsing**: Handles markdown code blocks, control characters, JSON cleanup

**Output:** List of entity names extracted by LLM: `["ENTITY_X", "ENTITY_Y"]`

---

#### Step 2.3: Fuzzy Matching and Validation

**Location:** `tog_service.py:220-238`

If LLM extraction fails or returns no entities, the system falls back to **fuzzy matching**:

```python
def _fuzzy_match_entity(target_entity: str, available_entities: List[str]):
    # Uses difflib.SequenceMatcher with 0.8 threshold
    # Matches variations like "JOHN DOE" vs "John Doe"
```

**Fallback Strategy:**
1. Direct match: Exact name match
2. Case-insensitive match
3. Token-based fuzzy matching (e.g., "What is Apple?" → "APPLE INC.")
4. Substring matching with scoring

**Output:** Validated list of entity names that exist in the graph.

---

#### Step 2.4: Retrieve Full Entity Objects from Neo4j

**Location:** `tog_service.py:319-365`

```cypher
MATCH (e:Entity {name: $name})
[WHERE e.document_id IN $document_ids]

-- Retrieve TextUnits that mention this entity
OPTIONAL MATCH (e)<-[:MENTIONS]-(tu:TextUnit)

WITH e, collect(DISTINCT tu.text) as text_chunks

RETURN e.id as id, e.name as name, e.type as type,
       e.description as description, e.confidence as confidence,
       e.document_id as document_id,
       text_chunks[0..3] as source_texts
LIMIT 1
```

**Purpose:** Convert entity names to `ToGEntity` objects with full context including:
- Entity metadata (id, name, type, description, confidence)
- Source text chunks where entity is mentioned (for context)

**Graph Relationships Used:**
- `(Entity)<-[:MENTIONS]-(TextUnit)`: Links entities to their source text

**Output:** List of `ToGEntity` objects ready for exploration.

---

## Neo4j Graph Database Retrieval

### Graph Schema

**Nodes:**
```
Document {id, name, file_path, created_at, status}
TextUnit {id, document_id, text, start_char, end_char}
Entity {id, name, type, description, confidence, mention_count, document_id}
Community {id, level, size, summary, themes}
```

**Relationships:**
```
(Document)<-[:PART_OF]-(TextUnit)
(TextUnit)-[:MENTIONS]->(Entity)
(Entity)-[r:RELATED_TO {type, description, confidence}]->(Entity)
(Entity)-[:BELONGS_TO]->(Community)
(Community)-[:PART_OF]->(Community)  -- Hierarchical
```

**Indexes and Constraints:**
- Unique constraint: `(Entity.name, Entity.type)`
- Indexes: `entity_name_lookup`, `entity_document`, `entity_mention_count`, `relation_type`, `relation_confidence`

---

### Phase 3: Iterative Graph Exploration (Multi-Hop Reasoning)

**Location:** `tog_service.py:930-1006`

This is the **core ToG reasoning loop** that explores the graph depth-by-depth.

```python
for depth in range(config.search_depth):  # Default: 3 depths
    # Step 1: Explore relations from current entities
    relations = await self._explore_relations(question, current_entities, config)

    # Step 2: Expand to target entities via relations
    next_entities = []
    for relation in relations:
        target_entity = await self._expand_entity_from_relation(
            relation, config.document_ids, question
        )
        if target_entity and target_entity not in self.explored_entities:
            next_entities.append(target_entity)

            # Track triplet: (subject, relation, object)
            self._add_triplet(
                subject=relation.source_entity.name,
                relation=relation.type,
                object=target_entity.name,
                confidence=relation.confidence,
                source=f"depth_{depth + 1}"
            )

    # Step 3: Check sufficiency
    if config.enable_sufficiency_check:
        sufficiency = await self._check_sufficiency(question, relations, config)
        if sufficiency.get("sufficient", False):
            break  # Stop exploration

    # Step 4: Prepare for next depth
    current_entities = next_entities[:config.num_retain_entity]
```

**Exploration Strategy:**
- **Breadth-First with Pruning**: Explore top-scored relations at each level
- **Cycle Detection**: Prevent revisiting entities from previous steps
- **Early Stopping**: Sufficiency check can terminate exploration early

---

#### Step 3.1: Relation Exploration

**Location:** `tog_service.py:367-451`

##### A. Get Available Relations from Neo4j

**Location:** `tog_service.py:500-551`

```cypher
MATCH (e:Entity)-[r:RELATED_TO]->(other:Entity)
WHERE e.name IN $entity_names
AND e.document_id IN $document_ids
AND other.document_id IN $document_ids
AND r.confidence > 0.3

WITH COALESCE(r.type, r.description, type(r)) as relation_type,
     count(*) as frequency,
     avg(r.confidence) as avg_confidence
WHERE relation_type IS NOT NULL

RETURN relation_type, frequency, avg_confidence
ORDER BY frequency DESC
LIMIT 50
```

**Purpose:** Get all relation types connected to current entities, ordered by frequency.

**Optimizations:**
- Uses `COALESCE` to handle different relation type storage formats
- Filters by confidence threshold (0.3) to exclude low-quality relations
- Limits to top 50 most frequent relations

**Output:** List of relation types like `["WORKS_AT", "LOCATED_IN", "COLLABORATES_WITH"]`

---

##### B. Filter Already Explored Relations

```python
new_relations = [
    r for r in available_relations
    if r["relation_type"] not in self.explored_relations
]
```

**Purpose:** Avoid cycles by tracking explored relation types.

---

##### C. Score Relations Using Pruning Method

**Location:** `tog_service.py:403-412`

Delegates to selected pruning method (LLM, BM25, or SentenceBERT):

```python
scored_relations = await self.pruning_method.score_relations(
    question=question,
    relations=relation_names,
    context={
        "entities": ", ".join([e.name for e in entities]),
        "previous_relations": ", ".join(self.explored_relations)
    }
)
```

**Pruning Methods:**

1. **LLM Pruning** (`backend/app/services/pruning_methods.py:32-68`)
   - Uses `TOG_RELATION_EXTRACTION_PROMPT`
   - Returns JSON with scored relations and reasoning
   - Example: `[{"relation_type": "WORKS_AT", "score": 0.9, "reasoning": "..."}]`

2. **BM25 Pruning** (`pruning_methods.py:138-183`)
   - Keyword-based scoring using BM25Okapi algorithm
   - Fast but less semantically aware
   - Tokenizes relation names and matches against question tokens

3. **SentenceBERT Pruning** (`pruning_methods.py:239-286`)
   - Uses sentence embeddings for semantic similarity
   - Model: `all-MiniLM-L6-v2`
   - Computes cosine similarity between question and relation embeddings

**Output:** Scored and sorted list of relations.

---

##### D. Select Top Relations

```python
scored_relations.sort(key=lambda x: x.get("score", 0), reverse=True)
top_relations = scored_relations[:config.search_width]  # Default: 3
```

**Purpose:** Keep only the most relevant relations based on pruning method scores.

---

#### Step 3.2: Entity Expansion via Relations

**Location:** `tog_service.py:553-593`

For each selected relation, find target entities connected via that relation:

```cypher
MATCH (source:Entity)-[r:RELATED_TO]->(target:Entity)
WHERE source.name = $source_name
AND r.type = $relation_type
[AND source.document_id IN $document_ids
 AND target.document_id IN $document_ids]

-- Retrieve TextUnits mentioning target entity
OPTIONAL MATCH (target)<-[:MENTIONS]-(tu:TextUnit)

WITH target, r, collect(DISTINCT tu.text) as text_chunks

RETURN target.id, target.name, target.type,
       target.description, target.confidence, target.document_id,
       r.confidence as relation_confidence,
       r.description as relation_description,
       text_chunks[0..3] as source_texts
ORDER BY r.confidence DESC, target.mention_count DESC
LIMIT 20
```

**Key Features:**
- Retrieves up to 20 candidate entities per relation
- Orders by relation confidence and entity mention count
- Includes source text chunks for context enrichment
- Filters by document IDs if specified

**Output:** List of candidate `ToGEntity` objects.

---

##### Entity Scoring and Selection

**Location:** `tog_service.py:576-593`

If multiple candidate entities exist, use LLM to score them:

**Prompt:** `TOG_ENTITY_SCORING_PROMPT` from `prompt.py:935-964`

```
Given a question, a relation type, a source entity, and candidate target entities,
score each candidate entity based on how well it helps answer the question.

Question: {question}
Relation Type: {relation_type}
Source Entity: {source_entity}
Candidate Entities: {candidate_entities}

Return JSON: {
    "entity_scores": [
        {"entity_name": "Entity1", "score": 0.9, "reasoning": "..."},
        {"entity_name": "Entity2", "score": 0.4, "reasoning": "..."}
    ]
}
```

**Purpose:** Select the most relevant target entity among multiple candidates.

**Output:** Best-scored `ToGEntity` for each relation.

---

#### Step 3.3: Sufficiency Check

**Location:** `tog_service.py:696-733`

If enabled, evaluate whether collected information is sufficient to answer the question:

**Prompt:** `TOG_SUFFICIENCY_CHECK_PROMPT` from `prompt.py:966-985`

```
Given a question and the relations that have been explored so far,
determine if there is sufficient information to answer the question.

Question: {question}
Explored Relations: {relations}

Return JSON: {
    "sufficient": true,
    "confidence_score": 0.85,
    "reasoning": "Explanation..."
}
```

**Purpose:** Stop exploration early if LLM determines sufficient information has been gathered.

**Output:** Sufficiency status and confidence score.

---

### Phase 4: Triplet Collection

**Location:** `tog_service.py:595-607`

Throughout exploration, the system collects **knowledge triplets**:

```python
def _add_triplet(subject: str, relation: str, object: str,
                  confidence: float, source: str):
    triplet = ToGTriplet(
        subject=subject,
        relation=relation,
        object=object,
        confidence=confidence,
        source=source  # e.g., "depth_1", "depth_2"
    )
    self.retrieved_triplets.add(triplet)
```

**Example Triplets:**
```
("JOHN DOE", "WORKS_AT", "ACME CORP", confidence=0.9, source="depth_1")
("ACME CORP", "LOCATED_IN", "NEW YORK", confidence=0.85, source="depth_2")
```

**Purpose:** Build structured knowledge base for answer generation.

---

## LLM Integration and Processing

### LLM Service Architecture

**Location:** `backend/app/services/llm_service.py`

The `LLMService` class manages all interactions with Google Gemini 2.5 Flash:

```python
class LLMService:
    def __init__(self):
        self.model_name = "gemini-2.5-flash"
        self.rate_limit_delay = 1.0 / 60  # 60 requests/minute
        self.max_retries = 3
        self.retry_delay = 1
```

**Key Methods:**

1. **`generate_text(prompt, temperature)`** - General text generation
2. **`extract_entities(text, chunk_id)`** - Entity extraction from text
3. **`extract_relationships(text, entities, chunk_id)`** - Relationship extraction
4. **`extract_claims(text, entities, chunk_id)`** - Claims extraction
5. **`classify_query(query)`** - Query type classification
6. **`generate_answer(query, context, citations)`** - Answer generation

---

### Rate Limiting and Retry Logic

**Location:** `llm_service.py:52-78`

```python
def _apply_rate_limit(self):
    elapsed = time.time() - self.last_request_time
    if elapsed < self.rate_limit_delay:
        time.sleep(self.rate_limit_delay - elapsed)
    self.last_request_time = time.time()

def _retry_with_backoff(self, func, *args, **kwargs):
    for attempt in range(self.max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == self.max_retries - 1:
                raise
            wait_time = self.retry_delay * (2**attempt)
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s")
            time.sleep(wait_time)
```

**Features:**
- **Rate Limiting**: Ensures 60 requests/minute max
- **Exponential Backoff**: 1s, 2s, 4s retry delays
- **API Key Validation**: Checks for Google API key errors

---

### Response Parsing

**Location:** `llm_service.py:79-148`

```python
@staticmethod
def _parse_json_response(response: str) -> Dict[str, Any]:
    # 1. Check for empty response
    if not response:
        return {}

    # 2. Try direct JSON parse
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass

    # 3. Remove markdown code blocks
    if response.startswith("```"):
        # Extract content between ```json and ```
        ...

    # 4. Remove invalid control characters
    response = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", response)

    # 5. Final parse attempt
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        return {}
```

**Purpose:** Robust JSON extraction from LLM responses that may include:
- Markdown code blocks (```json ... ```)
- Control characters
- Extra whitespace
- Malformed JSON

---

### Prompt Templates

**Location:** `backend/app/services/prompt.py`

All prompts are centralized in `prompt.py`:

**ToG-Specific Prompts:**

1. **`TOG_TOPIC_ENTITY_EXTRACTION_PROMPT`** (lines 883-901)
   - Identifies starting entities from question
   - Returns: `{"topic_entities": [...]}`

2. **`TOG_RELATION_EXTRACTION_PROMPT`** (lines 903-933)
   - Scores relation types for exploration
   - Returns: `{"relations": [{"relation_type": "...", "score": 0.8, "reasoning": "..."}]}`

3. **`TOG_ENTITY_SCORING_PROMPT`** (lines 935-964)
   - Scores candidate entities for a relation
   - Returns: `{"entity_scores": [{"entity_name": "...", "score": 0.9, "reasoning": "..."}]}`

4. **`TOG_SUFFICIENCY_CHECK_PROMPT`** (lines 966-985)
   - Evaluates if information is sufficient
   - Returns: `{"sufficient": true, "confidence_score": 0.85, "reasoning": "..."}`

5. **`TOG_FINAL_ANSWER_PROMPT`** (lines 987-1006)
   - Generates final answer from reasoning path
   - Returns: `{"answer": "...", "confidence": 0.8, "reasoning_summary": "..."}`

**GraphRAG Prompts:**

1. **`GRAPH_EXTRACTION_PROMPT_TEMPLATE`** (lines 30-150)
   - Joint entity and relationship extraction
   - Returns tuple-based format: `("entity"|||NAME|||TYPE|||DESCRIPTION)`

2. **`EXTRACT_CLAIMS_PROMPT_TEMPLATE`** (lines 158-209)
   - Claims extraction with subject, object, type, status
   - Returns tuple format with temporal data

3. **`COMMUNITY_REPORT_PROMPT_TEMPLATE`** (lines 256-361)
   - Community summarization with structured findings
   - Returns JSON with title, summary, rating, findings

---

## Answer Generation Workflow

### Phase 5: Final Answer Generation with Context Enrichment

**Location:** `tog_service.py:786-877`

This phase synthesizes all collected information into a comprehensive answer.

#### Step 5.1: Collect All Explored Entities

```python
all_entities = []
for step in self.reasoning_path.steps:
    all_entities.extend(step.entities_explored)
```

**Purpose:** Gather all entities from all exploration depths for context.

---

#### Step 5.2: Format Reasoning Path

```python
path_summary = []
for step in self.reasoning_path.steps:
    for rel in step.relations_selected:
        source_desc = rel.source_entity.description or rel.source_entity.name
        target_desc = rel.target_entity.description or rel.target_entity.name
        rel_desc = rel.description or rel.type

        detail = (
            f"{rel.source_entity.name} ({source_desc}) "
            f"--[{rel.type}: {rel_desc}]--> "
            f"{rel.target_entity.name} ({target_desc})"
        )
        path_summary.append(detail)

reasoning_text = "\n".join(path_summary)
```

**Example Output:**
```
JOHN DOE (Software Engineer) --[WORKS_AT: Employment relationship]--> ACME CORP (Technology company)
ACME CORP (Technology company) --[LOCATED_IN: Headquarters location]--> NEW YORK (City)
```

---

#### Step 5.3: Enrich with Source Text Chunks

**Location:** `tog_service.py:735-784`

Retrieve the most relevant TextUnit chunks mentioning explored entities:

```cypher
MATCH (e:Entity)<-[:MENTIONS]-(tu:TextUnit)
WHERE e.name IN $entity_names

WITH tu, count(DISTINCT e) as entity_count,
     collect(DISTINCT e.name) as mentioned_entities

ORDER BY entity_count DESC, tu.start_char ASC

RETURN tu.text as text, entity_count, mentioned_entities
LIMIT $top_k
```

**Purpose:** Get top-k (default: 5) text chunks that:
1. Mention the most explored entities
2. Are ordered by document position for context flow
3. Provide factual grounding for the answer

**Output:** List of text snippets from source documents.

---

#### Step 5.4: Combine Context

```python
# Entity-specific context snippets (max 3)
entity_context_snippets = []
for entity in all_entities:
    if entity.source_texts:
        snippet = f"[Context for {entity.name}]: {entity.source_texts[0][:500]}"
        entity_context_snippets.append(snippet)

# Additional top-k relevant chunks
enrichment_chunks = await self._enrich_answer_with_chunks(
    question=question,
    entities=all_entities,
    top_k=3
)

# Combine all context
all_context_snippets = entity_context_snippets[:3]
all_context_snippets.extend([
    f"[Additional Context]: {chunk[:500]}"
    for chunk in enrichment_chunks
])

context_text = "\n\n".join(all_context_snippets)
```

**Purpose:** Build comprehensive context from:
1. Entity-attached source texts (stored during exploration)
2. Additional relevant chunks (queried separately)

---

#### Step 5.5: Generate Final Answer with LLM

**Prompt Construction:**

```python
prompt = f"""Given a question, reasoning path with entity details,
and source text excerpts from the knowledge graph, generate a
comprehensive and detailed answer.

Question: {question}

Reasoning Path (entities and relationships explored):
{reasoning_text}

Source Text Excerpts:
{context_text}

Instructions:
- Provide a clear, comprehensive answer based on BOTH the reasoning
  path and source text excerpts
- Include specific facts, details, numbers, dates, and quotes from
  the source texts
- Reference entities and relationships from the reasoning path
- If the information is insufficient, clearly state what is missing
- Use a professional, informative tone

Return JSON format:
{{
    "answer": "Your detailed answer here with specific information
               from source texts",
    "confidence": 0.8,
    "reasoning_summary": "Brief summary of how the answer was derived
                          from graph reasoning and source texts"
}}
"""

response = await llm_service.generate_text(
    prompt=prompt,
    temperature=config.reasoning_temp  # Default: 0.0 for factual answers
)
```

**LLM Parameters:**
- **Temperature**: 0.0 (deterministic, factual)
- **Model**: Gemini 2.5 Flash
- **Max Tokens**: Default (no limit specified)

**Output:** JSON with answer, confidence, and reasoning summary.

---

## PostgreSQL Metadata Retrieval

While Neo4j handles the knowledge graph, PostgreSQL stores relational metadata and query history.

### User Authentication

**Location:** `backend/app/services/auth.py`

```python
def get_current_user(token: str, db: Session) -> User:
    # 1. Decode JWT token
    payload = jwt.decode(token, settings.SECRET_KEY,
                         algorithms=[settings.ALGORITHM])
    user_id = payload.get("sub")

    # 2. Query PostgreSQL for user
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
```

**Database Schema:**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### Query History Storage

**Location:** `backend/app/api/endpoints/tog.py:189-213`

After ToG query completes:

```python
# Convert reasoning path to JSON-serializable dict
reasoning_path_dict = convert_reasoning_path_to_dict(reasoning_path)

# Store in PostgreSQL
db_query = Query(
    user_id=current_user.id,
    document_id=None,  # ToG queries can span multiple documents
    query_text=request.question,
    response=reasoning_path.final_answer,
    query_mode="tog",
    confidence_score=float(reasoning_path.confidence_score),
    processing_time_ms=int(processing_time * 1000),
    tog_config=config.__dict__,
    reasoning_path=reasoning_path_dict.get("steps", []),
    retrieved_triplets=reasoning_path_dict.get("retrieved_triplets", []),
)
db.add(db_query)
db.commit()
```

**Database Schema:**
```sql
CREATE TABLE queries (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    document_id UUID REFERENCES documents(id),
    query_text TEXT NOT NULL,
    response TEXT NOT NULL,
    query_mode VARCHAR(50),  -- 'tog', 'local', 'global', 'hybrid'
    confidence_score FLOAT,
    processing_time_ms INTEGER,
    tog_config JSONB,  -- ToG configuration parameters
    reasoning_path JSONB,  -- Serialized reasoning steps
    retrieved_triplets JSONB,  -- Retrieved knowledge triplets
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Purpose:**
- **Query History**: Track user queries for analytics
- **Visualization**: Reconstruct reasoning paths for frontend display
- **Analytics**: Analyze query performance and patterns
- **Debugging**: Inspect failed queries and reasoning paths

---

### Document Metadata

**Location:** `backend/app/models/document.py`

```python
class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    title = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer)
    upload_status = Column(String(50), default="pending")
    processing_status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Purpose:** Track uploaded documents for filtering ToG queries by document.

---

## Data Flow Diagrams

### Complete ToG Query Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Submits Query                          │
│                   "How is Entity X related to Y?"                   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  Authenticate  │──► PostgreSQL: Validate JWT
                    │      User      │    Query users table
                    └────────┬───────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                   PHASE 1: Topic Entity Extraction                  │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Query Neo4j for available entities                             │
│     MATCH (e:Entity) RETURN e.name                                 │
│     ↓                                                               │
│  2. LLM: Identify topic entities from question                     │
│     Prompt: TOG_TOPIC_ENTITY_EXTRACTION_PROMPT                     │
│     ↓                                                               │
│  3. Fuzzy match LLM output to graph entities                       │
│     ↓                                                               │
│  4. Query Neo4j for full entity objects + source texts             │
│     MATCH (e:Entity)<-[:MENTIONS]-(tu:TextUnit)                    │
│                                                                     │
│  Output: List[ToGEntity] (starting entities)                       │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│         PHASE 2: Iterative Graph Exploration (Multi-Hop)           │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  FOR depth = 1 to search_depth (default: 3):                       │
│                                                                     │
│    ┌──────────────────────────────────────────────────────┐        │
│    │ Step A: Get Available Relations from Neo4j          │        │
│    │ MATCH (e:Entity)-[r:RELATED_TO]->(other:Entity)     │        │
│    │ WHERE e.name IN [current_entities]                  │        │
│    │ RETURN DISTINCT r.type, count(*), avg(r.confidence) │        │
│    └──────────────────┬───────────────────────────────────┘        │
│                       │                                            │
│                       ▼                                            │
│    ┌──────────────────────────────────────────────────────┐        │
│    │ Step B: Filter Already Explored Relations           │        │
│    │ Remove relation types in explored_relations set     │        │
│    └──────────────────┬───────────────────────────────────┘        │
│                       │                                            │
│                       ▼                                            │
│    ┌──────────────────────────────────────────────────────┐        │
│    │ Step C: Score Relations (Pruning Method)            │        │
│    │ - LLM: TOG_RELATION_EXTRACTION_PROMPT                │        │
│    │ - BM25: Keyword matching                            │        │
│    │ - SentenceBERT: Semantic similarity                 │        │
│    │ Returns: [{"relation": "...", "score": 0.9}]        │        │
│    └──────────────────┬───────────────────────────────────┘        │
│                       │                                            │
│                       ▼                                            │
│    ┌──────────────────────────────────────────────────────┐        │
│    │ Step D: Select Top-K Relations (search_width)       │        │
│    │ Sort by score DESC, take top 3 (default)            │        │
│    └──────────────────┬───────────────────────────────────┘        │
│                       │                                            │
│                       ▼                                            │
│    ┌──────────────────────────────────────────────────────┐        │
│    │ Step E: Expand to Target Entities                   │        │
│    │ FOR each selected relation:                         │        │
│    │   - Query Neo4j for target entities via relation    │        │
│    │   - If multiple candidates, score with LLM          │        │
│    │   - Select best target entity                       │        │
│    │   - Add triplet: (source, relation, target)         │        │
│    └──────────────────┬───────────────────────────────────┘        │
│                       │                                            │
│                       ▼                                            │
│    ┌──────────────────────────────────────────────────────┐        │
│    │ Step F: Sufficiency Check (if enabled)              │        │
│    │ LLM: TOG_SUFFICIENCY_CHECK_PROMPT                   │        │
│    │ If sufficient: BREAK loop                           │        │
│    └──────────────────┬───────────────────────────────────┘        │
│                       │                                            │
│                       ▼                                            │
│    ┌──────────────────────────────────────────────────────┐        │
│    │ Step G: Prepare Next Depth                          │        │
│    │ current_entities = next_entities[:num_retain_entity]│        │
│    │ Mark relations as explored                          │        │
│    └──────────────────────────────────────────────────────┘        │
│                                                                     │
│  Output: ToGReasoningPath with steps and triplets                  │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│              PHASE 3: Answer Generation with Context               │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Collect all explored entities from all steps                   │
│     ↓                                                               │
│  2. Format reasoning path as text                                  │
│     "Entity1 --[RELATION]--> Entity2"                              │
│     ↓                                                               │
│  3. Query Neo4j for top-k source text chunks                       │
│     MATCH (e:Entity)<-[:MENTIONS]-(tu:TextUnit)                    │
│     ORDER BY entity_count DESC                                     │
│     ↓                                                               │
│  4. Combine context:                                               │
│     - Reasoning path (graph structure)                             │
│     - Entity descriptions                                          │
│     - Source text excerpts (factual grounding)                     │
│     ↓                                                               │
│  5. LLM: Generate final answer                                     │
│     Prompt: TOG_FINAL_ANSWER_PROMPT                                │
│     Temperature: 0.0 (factual)                                     │
│     ↓                                                               │
│  6. Parse LLM response                                             │
│     Extract: answer, confidence, reasoning_summary                 │
│                                                                     │
│  Output: Final answer with confidence score                        │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                  PHASE 4: Store Query History                      │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Convert reasoning path to JSON-serializable dict               │
│     ↓                                                               │
│  2. Store in PostgreSQL queries table:                             │
│     - user_id, query_text, response                                │
│     - query_mode: "tog"                                            │
│     - confidence_score, processing_time_ms                         │
│     - tog_config (JSON)                                            │
│     - reasoning_path (JSON)                                        │
│     - retrieved_triplets (JSON)                                    │
│     ↓                                                               │
│  3. Record analytics metrics (optional)                            │
│                                                                     │
│  Output: query_id for future reference                             │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
                  ┌──────────────────┐
                  │  Return Response │
                  │   to User        │
                  └──────────────────┘
```

---

### Neo4j Query Patterns Summary

| **Phase** | **Query Purpose** | **Cypher Pattern** | **Returns** |
|-----------|-------------------|--------------------|-------------|
| Topic Entity Extraction | Get available entity names | `MATCH (e:Entity) RETURN e.name ORDER BY e.mention_count DESC LIMIT 1000` | List of entity names |
| Topic Entity Retrieval | Get full entity object | `MATCH (e:Entity {name: $name}) OPTIONAL MATCH (e)<-[:MENTIONS]-(tu:TextUnit) RETURN e, tu.text` | Entity with source texts |
| Relation Exploration | Get relation types for entities | `MATCH (e:Entity)-[r:RELATED_TO]->(other:Entity) WHERE e.name IN $names RETURN r.type, count(*), avg(r.confidence)` | List of relation types with stats |
| Entity Expansion | Get target entities via relation | `MATCH (source:Entity)-[r:RELATED_TO {type: $type}]->(target:Entity) OPTIONAL MATCH (target)<-[:MENTIONS]-(tu:TextUnit) RETURN target, tu.text` | Target entities with source texts |
| Context Enrichment | Get relevant text chunks | `MATCH (e:Entity)<-[:MENTIONS]-(tu:TextUnit) WHERE e.name IN $names RETURN tu.text ORDER BY count(e) DESC LIMIT $k` | Top-k text chunks |

---

## Pruning Strategies

ToG supports three pruning methods for scoring relations and entities:

### 1. LLM Pruning (Highest Quality, Slowest)

**Location:** `backend/app/services/pruning_methods.py:32-136`

**Advantages:**
- Most semantically aware
- Can reason about context and question intent
- Provides reasoning for scores

**Disadvantages:**
- Slowest (requires LLM API call per batch)
- Costs API quota
- Subject to LLM rate limits

**Use Cases:**
- Complex multi-hop questions
- When accuracy is critical
- When semantic understanding is needed

**Configuration:**
```json
{
    "pruning_method": "llm"
}
```

---

### 2. BM25 Pruning (Fast, Keyword-Based)

**Location:** `pruning_methods.py:138-236`

**Advantages:**
- Very fast (local computation)
- No API costs
- Works well for keyword-heavy queries

**Disadvantages:**
- Keyword-based, not semantically aware
- Misses synonyms and paraphrases
- Less effective for complex questions

**Use Cases:**
- Simple factual questions
- When speed is critical
- Large-scale batch processing

**Configuration:**
```json
{
    "pruning_method": "bm25"
}
```

**Implementation:**
```python
from rank_bm25 import BM25Okapi

# Tokenize question and relations
question_tokens = question.lower().split()
relation_docs = [rel.lower().replace('_', ' ').split() for rel in relations]

# Compute BM25 scores
bm25 = BM25Okapi(relation_docs)
scores = bm25.get_scores(question_tokens)

# Normalize to 0-1 range
max_score = max(scores)
normalized_scores = [s / max_score for s in scores]
```

---

### 3. SentenceBERT Pruning (Balanced)

**Location:** `pruning_methods.py:239-336`

**Advantages:**
- Semantic similarity via embeddings
- Faster than LLM, more accurate than BM25
- Handles synonyms and paraphrases

**Disadvantages:**
- Requires embedding model (230MB download)
- GPU recommended for speed
- Still slower than BM25

**Use Cases:**
- Balanced speed/accuracy requirements
- Semantic queries with paraphrasing
- Moderate-scale processing

**Configuration:**
```json
{
    "pruning_method": "sentence_bert"
}
```

**Implementation:**
```python
from sentence_transformers import SentenceTransformer, util

# Load model (cached after first load)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Encode question and relations
question_embedding = model.encode(question, convert_to_tensor=True)
relation_embeddings = model.encode(relation_texts, convert_to_tensor=True)

# Compute cosine similarities
similarities = util.cos_sim(question_embedding, relation_embeddings)[0]
```

---

## Code References

### Key Files and Line Numbers

| **Component** | **File Path** | **Key Lines** |
|---------------|---------------|---------------|
| ToG API Endpoint | `backend/app/api/endpoints/tog.py` | 146-248 (query endpoint) |
| ToG Service Main | `backend/app/services/tog_service.py` | 164-176 (process_query), 897-1015 (implementation) |
| Topic Entity Extraction | `tog_service.py` | 178-239 |
| Neo4j Entity Lookup | `tog_service.py` | 241-262, 319-365 |
| Relation Exploration | `tog_service.py` | 367-451 |
| Neo4j Relation Query | `tog_service.py` | 500-551 |
| Entity Expansion | `tog_service.py` | 553-593 |
| Neo4j Target Entity Query | `tog_service.py` | 609-669 |
| Sufficiency Check | `tog_service.py` | 696-733 |
| Answer Generation | `tog_service.py` | 786-877 |
| Context Enrichment | `tog_service.py` | 735-784 |
| LLM Service | `backend/app/services/llm_service.py` | 41-927 |
| LLM Rate Limiting | `llm_service.py` | 52-78 |
| JSON Response Parsing | `llm_service.py` | 79-148 |
| LLM Text Generation | `llm_service.py` | 662-690 |
| Prompt Templates | `backend/app/services/prompt.py` | 883-1142 |
| ToG Prompts | `prompt.py` | 883-1006 (ToG-specific) |
| Graph Service | `backend/app/services/graph_service.py` | 17-1300 |
| Neo4j Schema Init | `graph_service.py` | 28-85 |
| Entity Creation | `graph_service.py` | 189-249 |
| Relation Creation | `graph_service.py` | 290-341 |
| Entity Context Query | `graph_service.py` | 430-553 |
| Pruning Methods | `backend/app/services/pruning_methods.py` | 14-351 |
| LLM Pruning | `pruning_methods.py` | 32-136 |
| BM25 Pruning | `pruning_methods.py` | 138-236 |
| SentenceBERT Pruning | `pruning_methods.py` | 239-336 |
| ToG Schemas | `backend/app/schemas/tog.py` | 1-119 |
| PostgreSQL Models | `backend/app/models/query.py` | - (Query model) |

---

## Performance Optimizations

### Neo4j Optimizations

1. **Indexes**: Entity name, document_id, mention_count, relation type
2. **Constraints**: Unique (name, type) for entities
3. **Query Limits**: Limit to top 50 relations, top 20 entities per relation
4. **Confidence Filtering**: Filter relations with confidence < 0.3
5. **COALESCE**: Handle missing relation types gracefully

### LLM Optimizations

1. **Rate Limiting**: Prevent API quota exhaustion
2. **Exponential Backoff**: Retry failed requests intelligently
3. **Temperature Tuning**: Low temp (0.0) for factual answers, higher (0.4) for exploration
4. **Response Caching**: Redis can cache LLM responses (optional)

### Pruning Optimizations

1. **Early Stopping**: Sufficiency check can stop exploration early
2. **Cycle Detection**: Avoid revisiting entities
3. **Relation Filtering**: Track explored relations to avoid duplicates
4. **Entity Limiting**: Keep top-k entities at each depth (default: 5)

---

## Error Handling and Fallbacks

### ToG Query Processing

**Location:** `tog_service.py:881-1159`

```python
async def process_query_safe(question: str, config: ToGConfig):
    try:
        return await self._process_query_impl(question, config)
    except Exception as e:
        logger.error(f"ToG reasoning failed: {e}")
        return await self._fallback_reasoning(question, config)
```

**Fallback Strategy:**
1. Extract basic entities via fuzzy matching
2. Create minimal reasoning step
3. Return generic answer explaining the error
4. Set confidence to 0.1

### Entity Extraction Fallback

**Location:** `tog_service.py:1017-1041`

1. **Primary**: LLM topic entity extraction
2. **Fallback 1**: Retry without document filter
3. **Fallback 2**: Fuzzy matching on question tokens

### Relation Exploration Fallback

**Location:** `tog_service.py:1043-1051`

```python
try:
    return await self._explore_relations(question, entities, config)
except Exception as e:
    logger.error(f"Relation exploration failed: {e}")
    return []  # Empty relations, continue to next depth
```

### LLM Call Fallback

**Location:** `llm_service.py:59-78`

```python
for attempt in range(self.max_retries):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if "API_KEY" in str(e):
            raise  # Don't retry API key errors
        if attempt == self.max_retries - 1:
            raise
        wait_time = self.retry_delay * (2**attempt)
        time.sleep(wait_time)
```

---

## Conclusion

The GraphToG information retrieval flow is a sophisticated multi-stage pipeline that combines:

1. **Graph Database Queries**: Efficient Cypher queries on Neo4j for entity and relationship retrieval
2. **LLM-Guided Reasoning**: Google Gemini 2.5 Flash for entity extraction, relation scoring, and answer generation
3. **Iterative Exploration**: Multi-hop traversal with pruning and cycle detection
4. **Context Enrichment**: Source text retrieval for factual grounding
5. **Metadata Tracking**: PostgreSQL for query history and analytics

The system is designed for:
- **Accuracy**: LLM-guided pruning ensures semantic relevance
- **Scalability**: Graph indexes and query limits prevent performance degradation
- **Robustness**: Multi-layer fallback strategies handle errors gracefully
- **Flexibility**: Three pruning methods (LLM, BM25, SentenceBERT) for different use cases

This architecture enables answering complex multi-hop questions that require reasoning through relationships in a knowledge graph, with full transparency via reasoning paths and triplet tracking.
