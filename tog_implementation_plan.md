# Tree of Graphs (ToG) Implementation Plan for GraphToG

**Project:** GraphToG - GraphRAG + Tree of Graphs Integration
**Document Version:** 1.0
**Date:** 2025-11-03
**Status:** Planning Phase

---

## Executive Summary

This document outlines the comprehensive implementation plan for integrating Tree of Graphs (ToG) reasoning methodology into the existing GraphToG system. ToG enhances traditional retrieval by performing iterative graph traversal with LLM-guided pruning to explore multi-hop reasoning paths before generating answers.

**Current State:** GraphToG has a complete GraphRAG knowledge graph construction pipeline with Neo4j storage.

**Target State:** GraphToG will support ToG-based retrieval that performs depth-first graph exploration with entity scoring, relation pruning, and multi-hop reasoning for complex query answering.

**Expected Benefits:**
- Multi-hop reasoning capabilities for complex questions
- Improved answer quality through structured graph exploration
- Transparent reasoning paths showing how answers were derived
- Support for questions requiring multiple inference steps

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Phase 1: Foundation & Analysis](#phase-1-foundation--analysis)
3. [Phase 2: Core ToG Reasoning Engine](#phase-2-core-tog-reasoning-engine)
4. [Phase 3: Graph Traversal & Exploration](#phase-3-graph-traversal--exploration)
5. [Phase 4: Integration with Existing System](#phase-4-integration-with-existing-system)
6. [Phase 5: Testing & Optimization](#phase-5-testing--optimization)
7. [Phase 6: Documentation & Deployment](#phase-6-documentation--deployment)
8. [Risk Management](#risk-management)
9. [Success Metrics](#success-metrics)

---

## Architecture Overview

### ToG Methodology Summary

Tree of Graphs (ToG) is a reasoning framework that combines LLMs with knowledge graphs through:

1. **Iterative Graph Exploration**: Depth-first traversal with configurable width and depth
2. **LLM-Guided Pruning**: Score entities and relations at each step to focus search
3. **Sufficiency Evaluation**: Determine if retrieved information is sufficient to answer
4. **Multi-hop Reasoning**: Combine multiple graph paths to answer complex questions

### Integration Points with GraphToG

```
┌─────────────────────────────────────────────────────────────┐
│                    GraphToG System                          │
├─────────────────────────────────────────────────────────────┤
│  Existing Components:                                       │
│  ├── Knowledge Graph (Neo4j) ✓                             │
│  ├── Entity Extraction ✓                                   │
│  ├── Community Detection ✓                                 │
│  ├── LLM Service (Gemini) ✓                                │
├─────────────────────────────────────────────────────────────┤
│  NEW: ToG Components (To Be Implemented):                   │
│  ├── ToG Reasoning Engine                                   │
│  │   ├── Graph Traversal Controller                        │
│  │   ├── Entity Scoring System                             │
│  │   ├── Relation Pruning Logic                            │
│  │   └── Sufficiency Evaluator                             │
│  ├── ToG Prompt Templates                                   │
│  │   ├── Relation Extraction Prompts                       │
│  │   ├── Entity Scoring Prompts                            │
│  │   ├── Sufficiency Check Prompts                         │
│  │   └── Multi-hop Answer Generation Prompts               │
│  ├── ToG Query Service                                      │
│  │   ├── Query → Entity Mapping                            │
│  │   ├── Depth-First Search Orchestrator                   │
│  │   └── Reasoning Path Tracker                            │
│  └── ToG API Endpoints                                      │
│      ├── /api/query/tog (Main ToG query endpoint)          │
│      ├── /api/query/tog/explain (Get reasoning paths)      │
│      └── /api/query/tog/config (Configure parameters)      │
└─────────────────────────────────────────────────────────────┘
```

## Phase 1: Foundation & Analysis

**Duration:** 1 week
**Goal:** Understand current system architecture and prepare for ToG integration

### Task 1.1: Code Architecture Analysis

**Objective:** Map current GraphToG components and identify integration points

**Steps:**
1. Document current query processing flow in `backend/app/services/query_service.py`
2. Analyze graph schema and relationship types in Neo4j
3. Review LLM service capabilities and rate limits in `llm_service.py`
4. Map existing prompt templates in `prompt.py`
5. Identify reusable components (graph service, LLM service)

**Deliverables:**
- Architecture diagram showing current flow
- Component dependency map
- Integration points document

**Files to Review:**
- `backend/app/services/query_service.py`
- `backend/app/services/graph_service.py`
- `backend/app/services/llm_service.py`
- `backend/app/services/prompt.py`
- `backend/app/api/endpoints/queries.py`

---

### Task 1.2: Neo4j Graph Schema Review

**Objective:** Ensure graph structure supports ToG traversal requirements

**Steps:**
1. Review existing node types (Document, TextUnit, Entity, Community)
2. Review existing relationships (MENTIONS, RELATES_TO, BELONGS_TO)
3. Verify relationship properties (description, confidence, type)
4. Test graph connectivity and traversal queries
5. Document any schema modifications needed

**Deliverables:**
- Graph schema documentation with Cypher examples
- List of required schema enhancements (if any)
- Sample traversal queries

**Cypher Queries to Test:**
```cypher
// Test entity connectivity
MATCH (e1:Entity)-[r:RELATES_TO*1..3]-(e2:Entity)
WHERE e1.name = 'StartEntity'
RETURN e1, r, e2 LIMIT 50

// Test relation types distribution
MATCH ()-[r:RELATES_TO]->()
RETURN r.type, COUNT(*) as count
ORDER BY count DESC

// Test average connectivity
MATCH (e:Entity)
WITH e, SIZE((e)-[:RELATES_TO]-()) as degree
RETURN AVG(degree), MAX(degree), MIN(degree)
```

---

### Task 1.3: ToG Algorithm Deep Dive

**Objective:** Fully understand ToG methodology from source code

**Steps:**
1. Study `main_freebase.py` algorithm flow
2. Analyze prompt templates in `prompt_list.py`
3. Document scoring mechanisms for entities and relations
4. Understand sufficiency evaluation logic
5. Extract hyperparameters (width=3, depth=3, temperature settings)

**Deliverables:**
- ToG algorithm flowchart
- Prompt template analysis document
- Hyperparameter configuration guide

**Key Concepts to Document:**
- How relations are scored and pruned
- How entities are scored and selected
- How sufficiency is determined
- How reasoning paths are tracked
- How final answers are generated

---

### Task 1.4: Design Adaptation Strategy

**Objective:** Adapt ToG from Freebase/Wikidata to GraphRAG knowledge graphs

**Steps:**
1. Map Freebase/Wikidata structure to GraphRAG schema
2. Adapt relation types (Freebase has standardized relations, GraphRAG has extracted relations)
3. Design entity scoring adapted to GraphRAG entities
4. Plan relation pruning strategy for extracted relationships
5. Define how to handle community structure in ToG

**Deliverables:**
- Mapping document: Freebase ↔ GraphRAG
- Adapted algorithm pseudocode
- Schema modification requirements


---

### Task 1.5: API Design & Specifications

**Objective:** Design ToG query API with backward compatibility

**Steps:**
1. Design ToG query request/response schemas
2. Define configuration parameters (width, depth, temperature)
3. Design reasoning path response format
4. Ensure backward compatibility with existing query API
5. Plan versioning strategy

**Deliverables:**
- API specification document (OpenAPI/Swagger format)
- Request/response schema definitions (Pydantic models)
- API versioning plan

**Proposed API Endpoints:**

```python
# New ToG Query Endpoint
POST /api/query/tog
{
  "question": "What is the relationship between X and Y?",
  "document_ids": [1, 2, 3],  # Optional: filter to specific documents
  "config": {
    "search_width": 3,        # Max entities to explore per depth
    "search_depth": 3,         # Max traversal depth
    "exploration_temp": 0.4,   # Temperature for exploration phase
    "reasoning_temp": 0.0,     # Temperature for reasoning phase
    "num_retain_entity": 5,    # Max entities to retain during search
    "pruning_method": "llm",   # llm, bm25, or sentence_bert
    "enable_sufficiency_check": true
  }
}

Response:
{
  "answer": "X and Y are related through...",
  "reasoning_path": [
    {
      "depth": 0,
      "entities": ["X"],
      "relations_explored": ["works_at", "located_in"],
      "selected_relations": ["works_at"]
    },
    {
      "depth": 1,
      "entities": ["Company A", "Company B"],
      "relations_explored": ["partner_with", "competes_with"],
      "selected_relations": ["partner_with"],
      "sufficiency_score": 0.65
    },
    {
      "depth": 2,
      "entities": ["Y"],
      "relations_explored": ["founded_by"],
      "selected_relations": ["founded_by"],
      "sufficiency_score": 0.95,
      "sufficient": true
    }
  ],
  "retrieved_triplets": [
    {"subject": "X", "relation": "works_at", "object": "Company A"},
    {"subject": "Company A", "relation": "partner_with", "object": "Company B"},
    {"subject": "Y", "relation": "founded_by", "object": "Company B"}
  ],
  "confidence": 0.92,
  "processing_time_ms": 3450
}

# Get Reasoning Explanation
GET /api/query/tog/explain/{query_id}
Response: Detailed reasoning path with LLM reasoning at each step

# Configure ToG Parameters
POST /api/query/tog/config
Body: ToG configuration parameters
Response: Updated configuration
```

**Pydantic Schemas:**

```python
# backend/app/schemas/tog_query.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ToGConfig(BaseModel):
    search_width: int = Field(default=3, ge=1, le=10)
    search_depth: int = Field(default=3, ge=1, le=5)
    exploration_temp: float = Field(default=0.4, ge=0.0, le=1.0)
    reasoning_temp: float = Field(default=0.0, ge=0.0, le=1.0)
    num_retain_entity: int = Field(default=5, ge=1, le=20)
    pruning_method: str = Field(default="llm", regex="^(llm|bm25|sentence_bert)$")
    enable_sufficiency_check: bool = Field(default=True)

class ToGQueryRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000)
    document_ids: Optional[List[int]] = None
    config: Optional[ToGConfig] = ToGConfig()

class ToGReasoningStep(BaseModel):
    depth: int
    entities: List[str]
    relations_explored: List[str]
    selected_relations: List[str]
    entity_scores: Optional[Dict[str, float]] = None
    sufficiency_score: Optional[float] = None
    sufficient: Optional[bool] = None

class ToGTriplet(BaseModel):
    subject: str
    relation: str
    object: str
    confidence: Optional[float] = None

class ToGQueryResponse(BaseModel):
    answer: str
    reasoning_path: List[ToGReasoningStep]
    retrieved_triplets: List[ToGTriplet]
    confidence: float
    processing_time_ms: int
    query_id: Optional[int] = None
```

---

## Phase 2: Core ToG Reasoning Engine

**Duration:** 2-3 weeks
**Goal:** Implement core ToG reasoning logic and prompt templates

### Task 2.1: Create ToG Service Module

**Objective:** Build the main ToG service class structure

**Steps:**
1. Create `backend/app/services/tog_service.py`
2. Define `ToGReasoningEngine` class
3. Implement initialization with configuration
4. Create method stubs for all ToG operations
5. Add logging and error handling framework

**Deliverables:**
- `tog_service.py` with base class structure
- Unit tests for initialization
- Logging configuration

**File Structure:**

```python
# backend/app/services/tog_service.py
from typing import List, Dict, Optional, Tuple
from app.services.graph_service import GraphService
from app.services.llm_service import LLMService
from app.schemas.tog_query import ToGConfig, ToGReasoningStep, ToGTriplet
import logging

logger = logging.getLogger(__name__)

class ToGReasoningEngine:
    """
    Tree of Graphs reasoning engine for multi-hop question answering.

    Implements depth-first graph exploration with LLM-guided pruning
    to discover reasoning paths through the knowledge graph.
    """

    def __init__(
        self,
        graph_service: GraphService,
        llm_service: LLMService,
        config: ToGConfig
    ):
        self.graph_service = graph_service
        self.llm_service = llm_service
        self.config = config

        # Search state
        self.reasoning_path: List[ToGReasoningStep] = []
        self.retrieved_triplets: List[ToGTriplet] = []
        self.current_depth: int = 0

        # Entity and relation tracking
        self.explored_entities: set = set()
        self.explored_relations: set = set()
        self.current_entities: List[str] = []

        logger.info(f"ToG engine initialized with config: {config}")

    async def reason(
        self,
        question: str,
        document_ids: Optional[List[int]] = None
    ) -> Tuple[str, List[ToGReasoningStep], List[ToGTriplet], float]:
        """
        Main ToG reasoning method.

        Args:
            question: User's question
            document_ids: Optional document filtering

        Returns:
            Tuple of (answer, reasoning_path, triplets, confidence)
        """
        logger.info(f"Starting ToG reasoning for question: {question}")

        # Step 1: Extract topic entities from question
        topic_entities = await self._extract_topic_entities(question, document_ids)

        # Step 2: Iterative graph exploration
        sufficient = False
        for depth in range(self.config.search_depth):
            self.current_depth = depth
            logger.info(f"Exploring depth {depth}")

            # Step 2a: Find and score relations
            relations = await self._explore_relations(
                question, topic_entities, document_ids
            )

            # Step 2b: Get candidate entities via relations
            candidate_entities = await self._get_candidate_entities(
                topic_entities, relations, document_ids
            )

            # Step 2c: Score and prune entities
            scored_entities = await self._score_entities(
                question, candidate_entities, document_ids
            )

            # Step 2d: Update topic entities for next iteration
            topic_entities = self._select_top_entities(
                scored_entities, self.config.search_width
            )

            # Step 2e: Check sufficiency
            sufficient = await self._check_sufficiency(
                question, self.retrieved_triplets
            )

            if sufficient:
                logger.info(f"Sufficient information found at depth {depth}")
                break

        # Step 3: Generate final answer
        answer, confidence = await self._generate_answer(
            question, self.retrieved_triplets, self.reasoning_path
        )

        return answer, self.reasoning_path, self.retrieved_triplets, confidence

    # Stub methods (to be implemented in subsequent tasks)
    async def _extract_topic_entities(
        self, question: str, document_ids: Optional[List[int]]
    ) -> List[str]:
        """Extract initial entities from question."""
        raise NotImplementedError

    async def _explore_relations(
        self, question: str, entities: List[str], document_ids: Optional[List[int]]
    ) -> List[Dict]:
        """Find and score relations for current entities."""
        raise NotImplementedError

    async def _get_candidate_entities(
        self, source_entities: List[str], relations: List[Dict], document_ids: Optional[List[int]]
    ) -> List[Dict]:
        """Get entities connected via selected relations."""
        raise NotImplementedError

    async def _score_entities(
        self, question: str, candidates: List[Dict], document_ids: Optional[List[int]]
    ) -> List[Dict]:
        """Score entity candidates using LLM."""
        raise NotImplementedError

    def _select_top_entities(
        self, scored_entities: List[Dict], top_k: int
    ) -> List[str]:
        """Select top-k entities for next iteration."""
        raise NotImplementedError

    async def _check_sufficiency(
        self, question: str, triplets: List[ToGTriplet]
    ) -> bool:
        """Check if retrieved information is sufficient."""
        raise NotImplementedError

    async def _generate_answer(
        self, question: str, triplets: List[ToGTriplet], reasoning_path: List[ToGReasoningStep]
    ) -> Tuple[str, float]:
        """Generate final answer from reasoning path."""
        raise NotImplementedError
```

---

### Task 2.2: Implement ToG Prompt Templates

**Objective:** Create all LLM prompts for ToG reasoning steps

**Steps:**
1. Add ToG prompts to `backend/app/services/prompt.py`
2. Implement relation extraction and scoring prompt
3. Implement entity scoring prompt
4. Implement sufficiency evaluation prompt
5. Implement multi-hop answer generation prompt
6. Test prompts with sample inputs

**Deliverables:**
- Updated `prompt.py` with ToG prompts
- Prompt testing script
- Sample prompt outputs

**Prompt Templates:**

```python
# backend/app/services/prompt.py

# ==================== ToG Prompt Templates ====================

TOG_RELATION_EXTRACTION_PROMPT = """# Task: Identify Relevant Relations

You are analyzing a knowledge graph to answer a question through multi-hop reasoning.

## Question
{question}

## Current Entities
The current entities being explored:
{entities}

## Available Relations
These are the relations connected to the current entities in the knowledge graph:
{relations}

## Previous Context
Relations already explored: {previous_relations}

## Instructions
1. Analyze which relations are most likely to lead toward answering the question
2. Score each relation based on its relevance (0.0 to 1.0 scale)
3. Consider:
   - Direct relevance to the question
   - Potential to reach answer entities
   - Avoiding redundant paths already explored

## Output Format
Return a JSON array with relation scores:
```json
[
  {{"relation": "works_at", "score": 0.9, "reasoning": "Directly relevant to employment question"}},
  {{"relation": "located_in", "score": 0.6, "reasoning": "May provide geographic context"}},
  {{"relation": "friend_of", "score": 0.2, "reasoning": "Less relevant to the question"}}
]
```

Return only the JSON array, no other text.
"""

TOG_ENTITY_SCORING_PROMPT = """# Task: Score Entity Candidates

You are exploring a knowledge graph to answer a question. Score the candidate entities based on their relevance.

## Question
{question}

## Current Exploration Path
{reasoning_summary}

## Relation Used
{relation}

## Candidate Entities
These entities are connected via the "{relation}" relation:
{candidates}

## Instructions
1. Score each candidate entity (0.0 to 1.0) based on:
   - Relevance to answering the question
   - Likelihood of being on the path to the answer
   - Novelty (not just repeating previous information)
2. Provide reasoning for each score

## Output Format
Return a JSON array:
```json
[
  {{"entity": "Microsoft Corporation", "score": 0.95, "reasoning": "Direct match to question subject"}},
  {{"entity": "Bill Gates", "score": 0.75, "reasoning": "Related but indirect"}},
  {{"entity": "Seattle", "score": 0.3, "reasoning": "Geographic context only"}}
]
```

Return only the JSON array, no other text.
"""

TOG_SUFFICIENCY_CHECK_PROMPT = """# Task: Evaluate Information Sufficiency

Determine if the retrieved knowledge graph information is sufficient to answer the question.

## Question
{question}

## Retrieved Knowledge Graph Triplets
{triplets}

## Reasoning Path Summary
{reasoning_summary}

## Instructions
1. Analyze whether the triplets provide enough information to answer the question
2. Consider:
   - Are all key entities mentioned in the question covered?
   - Are the relationships between entities clear?
   - Is there enough context to form a complete answer?
3. Make a binary decision: sufficient or not sufficient

## Output Format
Return JSON:
```json
{{
  "sufficient": true,  // or false
  "confidence": 0.85,  // 0.0 to 1.0
  "reasoning": "The triplets show X works at Y, and Y is located in Z, which fully answers the question about X's work location.",
  "missing_information": []  // List what's missing if not sufficient
}}
```

Return only the JSON object, no other text.
"""

TOG_MULTI_HOP_ANSWER_GENERATION_PROMPT = """# Task: Generate Answer from Multi-hop Reasoning

Generate a comprehensive answer based on multi-hop reasoning through the knowledge graph.

## Question
{question}

## Retrieved Knowledge Graph Triplets
{triplets}

## Reasoning Path
{reasoning_path}

## Instructions
1. Synthesize the information from multiple graph hops
2. Explain the reasoning chain: how entities connect to answer the question
3. Ground your answer in the retrieved triplets (cite specific facts)
4. If information is incomplete, acknowledge limitations
5. Provide a confidence score

## Output Format
Return JSON:
```json
{{
  "answer": "Based on the knowledge graph, X works at Company Y. Company Y is a partner of Company Z, which is founded by Person W. Therefore, X is indirectly connected to W through their company relationships.",
  "reasoning_chain": [
    "X works_at Company Y (direct connection from graph)",
    "Company Y partner_with Company Z (2-hop connection)",
    "W founded_by Company Z (3-hop connection)",
    "Therefore: X → Company Y → Company Z → W"
  ],
  "confidence": 0.88,
  "grounding": [
    "X works_at Company Y",
    "Company Y partner_with Company Z",
    "W founded_by Company Z"
  ],
  "limitations": []  // Any information gaps or uncertainties
}}
```

Return only the JSON object, no other text.
"""

TOG_TOPIC_ENTITY_EXTRACTION_PROMPT = """# Task: Extract Topic Entities from Question

Identify the main entities mentioned in the question that should be starting points for graph exploration.

## Question
{question}

## Available Entities in Knowledge Graph
{available_entities}

## Instructions
1. Identify key entities explicitly or implicitly mentioned in the question
2. Match them to entities that exist in the knowledge graph
3. Return the matched entity names for graph exploration
4. Prioritize entities that are most central to the question

## Output Format
Return JSON:
```json
{{
  "topic_entities": ["Entity1", "Entity2"],
  "reasoning": "Entity1 is directly mentioned, Entity2 is the implicit subject"
}}
```

Return only the JSON object, no other text.
"""

# Helper function to format reasoning path for prompts
def format_reasoning_path_for_prompt(reasoning_path: List) -> str:
    """Format reasoning path as readable text for prompts."""
    if not reasoning_path:
        return "No previous reasoning steps."

    summary = []
    for i, step in enumerate(reasoning_path):
        summary.append(f"Depth {step['depth']}:")
        summary.append(f"  Entities explored: {', '.join(step['entities'])}")
        summary.append(f"  Relations used: {', '.join(step['selected_relations'])}")
        if step.get('sufficiency_score'):
            summary.append(f"  Sufficiency: {step['sufficiency_score']:.2f}")

    return "\n".join(summary)

def format_triplets_for_prompt(triplets: List) -> str:
    """Format triplets as readable text for prompts."""
    if not triplets:
        return "No triplets retrieved yet."

    formatted = []
    for i, t in enumerate(triplets, 1):
        formatted.append(f"{i}. ({t['subject']}) --[{t['relation']}]--> ({t['object']})")
        if t.get('confidence'):
            formatted[-1] += f" [confidence: {t['confidence']:.2f}]"

    return "\n".join(formatted)
```

---

### Task 2.3: Implement Topic Entity Extraction

**Objective:** Extract starting entities from user question

**Steps:**
1. Implement `_extract_topic_entities()` method
2. Use LLM to identify entities mentioned in question
3. Match against available entities in graph
4. Handle entity resolution (fuzzy matching)
5. Return ranked list of starting entities

**Deliverables:**
- Implemented topic entity extraction
- Unit tests with sample questions
- Entity matching accuracy metrics

**Implementation:**

```python
# In backend/app/services/tog_service.py

async def _extract_topic_entities(
    self, question: str, document_ids: Optional[List[int]]
) -> List[str]:
    """
    Extract initial topic entities from question.

    Steps:
    1. Get available entities from graph (filtered by documents if specified)
    2. Use LLM to identify entities mentioned in question
    3. Match to actual graph entities (fuzzy matching)
    4. Return top matches
    """
    logger.info(f"Extracting topic entities for: {question}")

    # Get available entities from graph
    available_entities = self._get_available_entities(document_ids)
    logger.debug(f"Found {len(available_entities)} entities in graph")

    # Prepare prompt
    from app.services.prompt import TOG_TOPIC_ENTITY_EXTRACTION_PROMPT

    # Limit to top 100 entities for prompt (avoid token limits)
    entity_sample = available_entities[:100] if len(available_entities) > 100 else available_entities

    prompt = TOG_TOPIC_ENTITY_EXTRACTION_PROMPT.format(
        question=question,
        available_entities=", ".join(entity_sample)
    )

    # Call LLM
    response = await self.llm_service.generate_text(
        prompt=prompt,
        temperature=self.config.exploration_temp
    )

    # Parse response
    result = self.llm_service._parse_json_response(response)
    topic_entities = result.get("topic_entities", [])

    logger.info(f"Extracted topic entities: {topic_entities}")

    # If LLM didn't find matches, fall back to fuzzy matching
    if not topic_entities:
        topic_entities = self._fuzzy_match_entities(question, available_entities)

    return topic_entities

def _get_available_entities(self, document_ids: Optional[List[int]]) -> List[str]:
    """Get entity names from graph, optionally filtered by documents."""
    query = """
    MATCH (e:Entity)
    """

    if document_ids:
        query += """
        WHERE e.document_id IN $document_ids
        """

    query += """
    RETURN DISTINCT e.name as name
    ORDER BY e.mention_count DESC
    LIMIT 1000
    """

    with self.graph_service.get_session() as session:
        result = session.run(query, {"document_ids": document_ids})
        entities = [record["name"] for record in result]

    return entities

def _fuzzy_match_entities(self, question: str, available_entities: List[str], top_k: int = 5) -> List[str]:
    """Fuzzy match question tokens to entity names."""
    from difflib import SequenceMatcher
    import re

    # Tokenize question (simple approach)
    question_lower = question.lower()
    words = re.findall(r'\w+', question_lower)

    # Score each entity
    entity_scores = []
    for entity in available_entities:
        entity_lower = entity.lower()
        max_score = 0.0

        # Check if entity name appears in question
        if entity_lower in question_lower:
            max_score = 1.0
        else:
            # Fuzzy match against question words
            for word in words:
                if len(word) < 3:  # Skip short words
                    continue
                score = SequenceMatcher(None, word, entity_lower).ratio()
                max_score = max(max_score, score)

        if max_score > 0.6:  # Threshold
            entity_scores.append((entity, max_score))

    # Sort and return top-k
    entity_scores.sort(key=lambda x: x[1], reverse=True)
    matched = [entity for entity, score in entity_scores[:top_k]]

    logger.info(f"Fuzzy matched entities: {matched}")
    return matched
```

---

### Task 2.4: Implement Relation Exploration & Scoring

**Objective:** Find and score relations for current entities

**Steps:**
1. Implement `_explore_relations()` method
2. Query Neo4j for relations connected to current entities
3. Use LLM to score relation relevance
4. Filter and rank relations
5. Track explored relations to avoid cycles

**Deliverables:**
- Implemented relation exploration
- Relation scoring tests
- Performance optimization (caching)

**Implementation:**

```python
# In backend/app/services/tog_service.py

async def _explore_relations(
    self, question: str, entities: List[str], document_ids: Optional[List[int]]
) -> List[Dict]:
    """
    Find and score relations connected to current entities.

    Returns:
        List of dicts with {relation_type, score, reasoning}
    """
    logger.info(f"Exploring relations for entities: {entities}")

    # Step 1: Get relations from graph
    available_relations = self._get_entity_relations(entities, document_ids)

    if not available_relations:
        logger.warning(f"No relations found for entities: {entities}")
        return []

    # Step 2: Filter out already explored relations (avoid cycles)
    new_relations = [
        r for r in available_relations
        if r not in self.explored_relations
    ]

    if not new_relations:
        logger.warning("All relations already explored")
        return []

    # Step 3: Use LLM to score relations
    from app.services.prompt import (
        TOG_RELATION_EXTRACTION_PROMPT,
        format_reasoning_path_for_prompt
    )

    prompt = TOG_RELATION_EXTRACTION_PROMPT.format(
        question=question,
        entities=", ".join(entities),
        relations=", ".join(new_relations),
        previous_relations=", ".join(self.explored_relations) if self.explored_relations else "None"
    )

    response = await self.llm_service.generate_text(
        prompt=prompt,
        temperature=self.config.exploration_temp
    )

    scored_relations = self.llm_service._parse_json_response(response)

    # Step 4: Sort by score and select top relations
    scored_relations.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_relations = scored_relations[:self.config.search_width]

    # Step 5: Mark as explored
    for rel in top_relations:
        self.explored_relations.add(rel['relation'])

    logger.info(f"Selected relations: {[r['relation'] for r in top_relations]}")

    return top_relations

def _get_entity_relations(
    self, entity_names: List[str], document_ids: Optional[List[int]]
) -> List[str]:
    """Get unique relation types connected to given entities."""
    query = """
    MATCH (e:Entity)-[r:RELATES_TO]->(other:Entity)
    WHERE e.name IN $entity_names
    """

    if document_ids:
        query += """
        AND e.document_id IN $document_ids
        AND other.document_id IN $document_ids
        """

    query += """
    RETURN DISTINCT r.type as relation_type
    """

    with self.graph_service.get_session() as session:
        result = session.run(query, {
            "entity_names": entity_names,
            "document_ids": document_ids
        })
        relations = [record["relation_type"] for record in result if record["relation_type"]]

    # Handle case where relation type might be None (extracted without type)
    if not relations:
        # Fall back to generic "RELATES_TO"
        relations = ["RELATES_TO"]

    return relations
```

---

### Task 2.5: Implement Entity Candidate Retrieval & Scoring

**Objective:** Get and score entities connected via selected relations

**Steps:**
1. Implement `_get_candidate_entities()` method
2. Query graph for entities connected via relations
3. Implement `_score_entities()` with LLM scoring
4. Handle large candidate sets (sampling)
5. Implement `_select_top_entities()` for pruning

**Deliverables:**
- Entity candidate retrieval implementation
- Entity scoring implementation
- Top-k selection logic
- Tests with various graph structures

**Implementation:**

```python
# In backend/app/services/tog_service.py

async def _get_candidate_entities(
    self,
    source_entities: List[str],
    relations: List[Dict],
    document_ids: Optional[List[int]]
) -> List[Dict]:
    """
    Get entities connected to source entities via specified relations.

    Returns:
        List of dicts with {entity_name, relation_used, confidence, description}
    """
    candidates = []

    for relation_info in relations:
        relation_type = relation_info['relation']

        # Query graph
        entities = self._query_entities_by_relation(
            source_entities, relation_type, document_ids
        )

        # Add relation context
        for entity in entities:
            entity['relation_used'] = relation_type
            entity['relation_score'] = relation_info.get('score', 1.0)

        candidates.extend(entities)

    # Remove duplicates (entity might be reached via multiple relations)
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c['entity_name'] not in seen:
            seen.add(c['entity_name'])
            unique_candidates.append(c)

    # Sample if too many candidates (avoid LLM token limits)
    if len(unique_candidates) > 20:
        import random
        random.seed(42)  # Reproducible sampling
        unique_candidates = random.sample(unique_candidates, self.config.num_retain_entity)

    logger.info(f"Retrieved {len(unique_candidates)} candidate entities")

    return unique_candidates

def _query_entities_by_relation(
    self,
    source_entities: List[str],
    relation_type: str,
    document_ids: Optional[List[int]]
) -> List[Dict]:
    """Query graph for entities connected via specific relation."""
    query = """
    MATCH (source:Entity)-[r:RELATES_TO]->(target:Entity)
    WHERE source.name IN $source_entities
    """

    if relation_type and relation_type != "RELATES_TO":
        query += """
        AND r.type = $relation_type
        """

    if document_ids:
        query += """
        AND source.document_id IN $document_ids
        AND target.document_id IN $document_ids
        """

    query += """
    RETURN DISTINCT
        target.name as entity_name,
        target.description as description,
        target.type as entity_type,
        r.confidence as confidence
    LIMIT 50
    """

    with self.graph_service.get_session() as session:
        result = session.run(query, {
            "source_entities": source_entities,
            "relation_type": relation_type,
            "document_ids": document_ids
        })

        entities = []
        for record in result:
            entities.append({
                "entity_name": record["entity_name"],
                "description": record["description"] or "No description",
                "entity_type": record["entity_type"] or "UNKNOWN",
                "confidence": record["confidence"] or 0.5
            })

    return entities

async def _score_entities(
    self,
    question: str,
    candidates: List[Dict],
    document_ids: Optional[List[int]]
) -> List[Dict]:
    """
    Score entity candidates using LLM.

    Returns:
        List of candidates with added 'score' field
    """
    if not candidates:
        return []

    from app.services.prompt import (
        TOG_ENTITY_SCORING_PROMPT,
        format_reasoning_path_for_prompt
    )

    # Format candidates for prompt
    candidates_text = "\n".join([
        f"- {c['entity_name']} ({c['entity_type']}): {c['description'][:100]}"
        for c in candidates
    ])

    # Get first relation used (simplification)
    relation_used = candidates[0].get('relation_used', 'RELATES_TO')

    prompt = TOG_ENTITY_SCORING_PROMPT.format(
        question=question,
        reasoning_summary=format_reasoning_path_for_prompt(self.reasoning_path),
        relation=relation_used,
        candidates=candidates_text
    )

    response = await self.llm_service.generate_text(
        prompt=prompt,
        temperature=self.config.exploration_temp
    )

    scored_entities = self.llm_service._parse_json_response(response)

    # Merge scores back into candidates
    score_map = {e['entity']: e for e in scored_entities}

    for candidate in candidates:
        entity_name = candidate['entity_name']
        if entity_name in score_map:
            candidate['score'] = score_map[entity_name].get('score', 0.5)
            candidate['score_reasoning'] = score_map[entity_name].get('reasoning', '')
        else:
            candidate['score'] = 0.5  # Default

    return candidates

def _select_top_entities(
    self, scored_entities: List[Dict], top_k: int
) -> List[str]:
    """
    Select top-k entities based on scores.

    Returns:
        List of entity names
    """
    # Sort by score
    scored_entities.sort(key=lambda x: x.get('score', 0), reverse=True)

    # Select top-k
    top_entities = scored_entities[:top_k]

    # Add to explored set
    for entity in top_entities:
        self.explored_entities.add(entity['entity_name'])

        # Store triplet
        # (This is simplified - in full implementation, track source entity)
        self.retrieved_triplets.append(
            ToGTriplet(
                subject=entity.get('source', 'previous_entity'),
                relation=entity.get('relation_used', 'RELATES_TO'),
                object=entity['entity_name'],
                confidence=entity.get('score', 0.5)
            )
        )

    entity_names = [e['entity_name'] for e in top_entities]
    logger.info(f"Selected top {len(entity_names)} entities: {entity_names}")

    return entity_names
```

---

### Task 2.6: Implement Sufficiency Evaluation

**Objective:** Determine if retrieved information is sufficient to answer

**Steps:**
1. Implement `_check_sufficiency()` method
2. Use LLM to evaluate information completeness
3. Return boolean + confidence score
4. Handle edge cases (empty triplets, first iteration)
5. Add caching to avoid redundant checks

**Deliverables:**
- Sufficiency check implementation
- Tests with various triplet sets
- Performance benchmarks

**Implementation:**

```python
# In backend/app/services/tog_service.py

async def _check_sufficiency(
    self, question: str, triplets: List[ToGTriplet]
) -> bool:
    """
    Check if retrieved triplets are sufficient to answer question.

    Returns:
        True if sufficient, False otherwise
    """
    # Skip check on first iteration (not enough info yet)
    if self.current_depth == 0:
        return False

    # Skip if disabled
    if not self.config.enable_sufficiency_check:
        # Fall back to depth-based stopping
        return self.current_depth >= (self.config.search_depth - 1)

    # Must have retrieved some triplets
    if not triplets:
        return False

    from app.services.prompt import (
        TOG_SUFFICIENCY_CHECK_PROMPT,
        format_triplets_for_prompt,
        format_reasoning_path_for_prompt
    )

    prompt = TOG_SUFFICIENCY_CHECK_PROMPT.format(
        question=question,
        triplets=format_triplets_for_prompt([t.dict() for t in triplets]),
        reasoning_summary=format_reasoning_path_for_prompt(self.reasoning_path)
    )

    response = await self.llm_service.generate_text(
        prompt=prompt,
        temperature=self.config.reasoning_temp  # Use reasoning temp (lower)
    )

    result = self.llm_service._parse_json_response(response)

    sufficient = result.get('sufficient', False)
    confidence = result.get('confidence', 0.0)
    reasoning = result.get('reasoning', '')

    # Update reasoning path with sufficiency info
    if self.reasoning_path:
        self.reasoning_path[-1].sufficiency_score = confidence
        self.reasoning_path[-1].sufficient = sufficient

    logger.info(
        f"Sufficiency check: {sufficient} (confidence: {confidence:.2f}) - {reasoning}"
    )

    return sufficient
```

---

### Task 2.7: Implement Multi-hop Answer Generation

**Objective:** Generate final answer from reasoning path and triplets

**Steps:**
1. Implement `_generate_answer()` method
2. Use multi-hop reasoning prompt
3. Synthesize information from all retrieved triplets
4. Generate reasoning chain explanation
5. Return answer + confidence score

**Deliverables:**
- Answer generation implementation
- Quality tests with sample questions
- Confidence calibration analysis

**Implementation:**

```python
# In backend/app/services/tog_service.py

async def _generate_answer(
    self,
    question: str,
    triplets: List[ToGTriplet],
    reasoning_path: List[ToGReasoningStep]
) -> Tuple[str, float]:
    """
    Generate final answer from multi-hop reasoning.

    Returns:
        Tuple of (answer_text, confidence_score)
    """
    from app.services.prompt import (
        TOG_MULTI_HOP_ANSWER_GENERATION_PROMPT,
        format_triplets_for_prompt,
        format_reasoning_path_for_prompt
    )

    # Handle case with no triplets (fallback)
    if not triplets:
        logger.warning("No triplets available for answer generation")
        return await self._generate_fallback_answer(question)

    prompt = TOG_MULTI_HOP_ANSWER_GENERATION_PROMPT.format(
        question=question,
        triplets=format_triplets_for_prompt([t.dict() for t in triplets]),
        reasoning_path=format_reasoning_path_for_prompt([s.dict() for s in reasoning_path])
    )

    response = await self.llm_service.generate_text(
        prompt=prompt,
        temperature=self.config.reasoning_temp  # Low temperature for final answer
    )

    result = self.llm_service._parse_json_response(response)

    answer = result.get('answer', 'Unable to generate answer from retrieved information.')
    confidence = result.get('confidence', 0.5)
    reasoning_chain = result.get('reasoning_chain', [])

    logger.info(f"Generated answer with confidence {confidence:.2f}")
    logger.debug(f"Reasoning chain: {reasoning_chain}")

    return answer, confidence

async def _generate_fallback_answer(self, question: str) -> Tuple[str, float]:
    """Generate answer without graph exploration (fallback)."""
    logger.warning("Using fallback answer generation")

    prompt = f"""Answer the following question based on your general knowledge:

Question: {question}

Provide a concise answer and indicate if you're uncertain.
"""

    response = await self.llm_service.generate_text(
        prompt=prompt,
        temperature=0.7
    )

    return response, 0.3  # Low confidence for fallback
```

### Coding Phase 2 Execution Plan

**Phase 1 dependencies leveraged**
- Architecture and integration analysis (docs/phase1/tog_phase1_deliverables.md) defines how `backend/app/services/query_service.py` and `backend/app/services/graph_service.py` will host ToG orchestration.
- Neo4j schema validation confirms `Entity`, `RELATED_TO`, `Community`, and `Claim` structures are production ready for multi-hop traversal without additional migrations.
- Prompt adaptation strategy is documented; placeholders already exist in `backend/app/services/prompt.py` for ToG-specific templates.
- API contract for optional `tog_config` payload and reasoning block is established, keeping Phase 2 coding backwards compatible.

**Milestone sequencing**

| Milestone | Focus | Key Deliverables | Dependencies |
| --- | --- | --- | --- |
| M2.1 (Week 1) | ToG service scaffolding & config wiring | `ToGReasoningEngine` constructor, async `reason` loop skeleton, Pydantic models in `backend/app/schemas/tog_query.py`, logging hooks | Dependency map and DI setup from Phase 1 |
| M2.2 (Week 2) | Graph exploration loop | `_extract_topic_entities`, `_explore_relations`, `_get_candidate_entities`, `_score_entities`, `_select_top_entities` implemented with GraphService helpers and prompt wiring | Prompt templates and graph metadata access |
| M2.3 (Week 3) | Sufficiency + answer synthesis + harness | `_check_sufficiency`, `_generate_answer`, `_generate_fallback_answer`, reasoning path serialization, async test harness | Config toggles, caching layer, Gemini stubs |

**Detailed work items**

1. `M2.1 ToG service foundation`
   - Create `backend/app/services/tog_service.py` with dependency-injected `GraphService` and `LLMService`, maintaining search state per Task 2.1.
   - Materialize `ToGConfig`, `ToGReasoningStep`, `ToGTriplet`, and `ToGQueryResponse` in `backend/app/schemas/tog_query.py` with defaults from Phase 1 hyperparameter table.
   - Register `ToGReasoningEngine` within FastAPI dependency wiring so `QueryService` can resolve it during request handling.
   - Add constructor/unit tests in `backend/tests/services/test_tog_service.py` covering config validation and logging instrumentation.

2. `M2.2 Exploration loop implementation`
   - Implement `_extract_topic_entities` with entity sampling from `GraphService` plus Gemini prompt and fuzzy fallback, exercising fixtures from Phase 1 graph slices.
   - Implement `_explore_relations` and supporting `GraphService` helper to return relation metadata with confidence scores and caching hooks.
   - Implement `_get_candidate_entities`, `_score_entities`, and `_select_top_entities`, ensuring deduplication, relation context, and reasoning path updates (Tasks 2.4-2.5).
   - Introduce Redis-backed caching via `backend/app/services/cache_service.py` (or in-memory shim) for relation/entity lists to hit performance targets.
   - Add async unit tests exercising breadth/width limits using Neo4j fixtures or stubs to verify pruning.

3. `M2.3 Sufficiency & answer synthesis`
   - Implement `_check_sufficiency` with LLM prompt plus fallback heuristics, persisting confidence into `ToGReasoningStep`.
   - Implement `_generate_answer` and `_generate_fallback_answer`, including reasoning chain serialization for LangSmith exports (Task 2.7).
   - Wire `ToGReasoningEngine.reason` into `backend/app/services/query_service.py` behind the `mode == "tog"` branch with structured response assembly.
   - Deliver integration tests hitting FastAPI endpoints with mocked Gemini and Neo4j, verifying schema compliance, logging, and latency.

**Testing & validation**
- Unit tests for each private method with Gemini and Neo4j fixtures, maintaining >= 80% coverage for `backend/app/services/tog_service.py`.
- Contract tests for prompt builders to guarantee JSON-only outputs and error handling.
- Integration tests for `QueryService.process_query` ToG path plus load test capturing iteration latency budgets.
- QA checklist: sufficiency gating, answer construction, LangSmith trace emission, and fallback behavior.

**Resourcing & prerequisites**
- Seed Neo4j fixture dataset exported from Phase 1 knowledge graph snapshot.
- Gemini mock harness or recorded responses for deterministic testing.
- Redis service via docker-compose (or in-memory adapter) to support caching experiments during Phase 2.

**Definition of done**
- `ToGReasoningEngine.reason` returns populated `ToGQueryResponse` objects with reasoning path, triplets, and confidence for sample queries.
- Test suites in `backend/tests/services` and `backend/tests/api` pass in CI alongside linting and type checks.
- Updated documentation in `docs/api/query.md` and new runbook entry (`docs/phase2/tog_coding.md`) describing setup, config, and troubleshooting.
- Demo script or notebook captures end-to-end ToG reasoning for stakeholder review.

---

## Phase 3: Graph Traversal & Exploration

**Duration:** 1-2 weeks
**Goal:** Implement graph traversal logic and optimization

### Task 3.1: Optimize Neo4j Queries for ToG

**Objective:** Ensure graph queries are efficient for iterative traversal

**Steps:**
1. Review all Cypher queries in ToG service
2. Add appropriate indexes for traversal patterns
3. Optimize query performance (EXPLAIN/PROFILE)
4. Add query result caching
5. Benchmark query performance

**Deliverables:**
- Optimized Cypher queries
- New indexes added to graph schema
- Performance benchmark report
- Caching strategy document

**Index Strategy:**

```cypher
// Indexes for ToG traversal
CREATE INDEX entity_name_lookup IF NOT EXISTS
FOR (e:Entity) ON (e.name);

CREATE INDEX entity_document IF NOT EXISTS
FOR (e:Entity) ON (e.document_id);

CREATE INDEX entity_mention_count IF NOT EXISTS
FOR (e:Entity) ON (e.mention_count);

CREATE INDEX relation_type IF NOT EXISTS
FOR ()-[r:RELATES_TO]-() ON (r.type);

CREATE INDEX relation_confidence IF NOT EXISTS
FOR ()-[r:RELATES_TO]-() ON (r.confidence);

// Composite index for filtered queries
CREATE INDEX entity_name_doc_composite IF NOT EXISTS
FOR (e:Entity) ON (e.name, e.document_id);
```

**Query Optimization Examples:**

```cypher
// BEFORE: Slow query
MATCH (e:Entity)-[r:RELATES_TO*1..3]-(other:Entity)
WHERE e.name = 'StartEntity'
RETURN e, r, other

// AFTER: Optimized with path length limit and filtering
MATCH path = (e:Entity)-[r:RELATES_TO*1..2]-(other:Entity)
WHERE e.name = $entity_name
  AND e.document_id IN $document_ids
  AND ALL(rel IN relationships(path) WHERE rel.confidence > 0.3)
RETURN other.name, other.description, length(path) as distance
ORDER BY distance, other.mention_count DESC
LIMIT 50
```

---

### Task 3.2: Implement Reasoning Path Tracking

**Objective:** Track and store complete reasoning paths for transparency

**Steps:**
1. Enhance `ToGReasoningStep` data structure
2. Track entities, relations, and scores at each depth
3. Store reasoning paths in database (Query model)
4. Implement path visualization data format
5. Add path export functionality (JSON)

**Deliverables:**
- Enhanced reasoning path tracking
- Database schema updates
- Path visualization format
- Export API endpoint

**Database Schema Update:**

```python
# backend/app/models/query.py

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.postgres import Base
import datetime

class Query(Base):
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    question = Column(Text, nullable=False)
    answer = Column(Text)
    query_type = Column(String(50))  # "local", "global", "hybrid", "tog"
    confidence = Column(Float)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # ToG-specific fields
    tog_config = Column(JSON)  # Store ToGConfig as JSON
    reasoning_path = Column(JSON)  # Store full reasoning path
    retrieved_triplets = Column(JSON)  # Store triplets

    # Relationships
    user = relationship("User", back_populates="queries")
```

**Migration Script:**

```python
# Create Alembic migration
# alembic revision --autogenerate -m "add_tog_fields_to_query"

"""add_tog_fields_to_query

Revision ID: abc123def456
Create Date: 2025-11-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('queries', sa.Column('tog_config', postgresql.JSON, nullable=True))
    op.add_column('queries', sa.Column('reasoning_path', postgresql.JSON, nullable=True))
    op.add_column('queries', sa.Column('retrieved_triplets', postgresql.JSON, nullable=True))

def downgrade():
    op.drop_column('queries', 'retrieved_triplets')
    op.drop_column('queries', 'reasoning_path')
    op.drop_column('queries', 'tog_config')
```

---

### Task 3.3: Add Pruning Method Options

**Objective:** Support multiple pruning methods (LLM, BM25, SentenceBERT)

**Steps:**
1. Implement BM25-based relation/entity scoring
2. Implement SentenceBERT-based scoring
3. Create pruning method factory
4. Add configuration to switch between methods
5. Benchmark pruning methods (accuracy vs speed)

**Deliverables:**
- Multiple pruning implementations
- Pruning method factory
- Benchmark comparison report
- Configuration documentation

**Implementation:**

```python
# backend/app/services/pruning_methods.py

from typing import List, Dict
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, util
import numpy as np
from abc import ABC, abstractmethod

class PruningMethod(ABC):
    """Abstract base class for pruning methods."""

    @abstractmethod
    async def score_relations(
        self, question: str, relations: List[str], context: Dict
    ) -> List[Dict]:
        """Score relations based on relevance to question."""
        pass

    @abstractmethod
    async def score_entities(
        self, question: str, entities: List[Dict], context: Dict
    ) -> List[Dict]:
        """Score entities based on relevance to question."""
        pass

class LLMPruning(PruningMethod):
    """LLM-based pruning (highest quality, slowest)."""

    def __init__(self, llm_service):
        self.llm_service = llm_service

    async def score_relations(self, question: str, relations: List[str], context: Dict) -> List[Dict]:
        # Use existing LLM scoring (implemented in Task 2.4)
        from app.services.prompt import TOG_RELATION_EXTRACTION_PROMPT

        prompt = TOG_RELATION_EXTRACTION_PROMPT.format(
            question=question,
            entities=context.get('entities', ''),
            relations=', '.join(relations),
            previous_relations=context.get('previous_relations', 'None')
        )

        response = await self.llm_service.generate_text(prompt, temperature=0.4)
        return self.llm_service._parse_json_response(response)

    async def score_entities(self, question: str, entities: List[Dict], context: Dict) -> List[Dict]:
        # Use existing LLM scoring (implemented in Task 2.5)
        from app.services.prompt import TOG_ENTITY_SCORING_PROMPT

        entities_text = "\n".join([
            f"- {e['entity_name']}: {e.get('description', '')}"
            for e in entities
        ])

        prompt = TOG_ENTITY_SCORING_PROMPT.format(
            question=question,
            reasoning_summary=context.get('reasoning_summary', ''),
            relation=context.get('relation', 'RELATES_TO'),
            candidates=entities_text
        )

        response = await self.llm_service.generate_text(prompt, temperature=0.4)
        return self.llm_service._parse_json_response(response)

class BM25Pruning(PruningMethod):
    """BM25-based pruning (fast, keyword-based)."""

    def __init__(self):
        pass

    async def score_relations(self, question: str, relations: List[str], context: Dict) -> List[Dict]:
        # Tokenize question
        question_tokens = question.lower().split()

        # Tokenize relations
        relation_docs = [rel.lower().replace('_', ' ').split() for rel in relations]

        # BM25 scoring
        bm25 = BM25Okapi(relation_docs)
        scores = bm25.get_scores(question_tokens)

        # Normalize scores to 0-1
        max_score = max(scores) if max(scores) > 0 else 1.0
        normalized_scores = [s / max_score for s in scores]

        # Format results
        results = []
        for rel, score in zip(relations, normalized_scores):
            results.append({
                "relation": rel,
                "score": float(score),
                "reasoning": f"BM25 relevance score based on keyword matching"
            })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results

    async def score_entities(self, question: str, entities: List[Dict], context: Dict) -> List[Dict]:
        # Tokenize question
        question_tokens = question.lower().split()

        # Create documents from entity names and descriptions
        entity_docs = []
        for e in entities:
            text = f"{e['entity_name']} {e.get('description', '')}".lower()
            entity_docs.append(text.split())

        # BM25 scoring
        bm25 = BM25Okapi(entity_docs)
        scores = bm25.get_scores(question_tokens)

        # Normalize
        max_score = max(scores) if max(scores) > 0 else 1.0
        normalized_scores = [s / max_score for s in scores]

        # Add scores to entities
        results = []
        for entity, score in zip(entities, normalized_scores):
            results.append({
                "entity": entity['entity_name'],
                "score": float(score),
                "reasoning": f"BM25 keyword relevance"
            })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results

class SentenceBERTPruning(PruningMethod):
    """SentenceBERT-based pruning (semantic similarity, medium speed)."""

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)

    async def score_relations(self, question: str, relations: List[str], context: Dict) -> List[Dict]:
        # Encode question
        question_embedding = self.model.encode(question, convert_to_tensor=True)

        # Encode relations (convert underscores to spaces)
        relation_texts = [rel.replace('_', ' ') for rel in relations]
        relation_embeddings = self.model.encode(relation_texts, convert_to_tensor=True)

        # Compute cosine similarities
        similarities = util.cos_sim(question_embedding, relation_embeddings)[0]

        # Format results
        results = []
        for rel, score in zip(relations, similarities):
            results.append({
                "relation": rel,
                "score": float(score),
                "reasoning": f"Semantic similarity to question"
            })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results

    async def score_entities(self, question: str, entities: List[Dict], context: Dict) -> List[Dict]:
        # Encode question
        question_embedding = self.model.encode(question, convert_to_tensor=True)

        # Encode entity descriptions
        entity_texts = [
            f"{e['entity_name']} {e.get('description', '')}"
            for e in entities
        ]
        entity_embeddings = self.model.encode(entity_texts, convert_to_tensor=True)

        # Compute similarities
        similarities = util.cos_sim(question_embedding, entity_embeddings)[0]

        # Format results
        results = []
        for entity, score in zip(entities, similarities):
            results.append({
                "entity": entity['entity_name'],
                "score": float(score),
                "reasoning": f"Semantic similarity"
            })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results

# Factory
def create_pruning_method(method: str, llm_service=None) -> PruningMethod:
    """Factory to create pruning method instance."""
    if method == "llm":
        if not llm_service:
            raise ValueError("LLM service required for llm pruning method")
        return LLMPruning(llm_service)
    elif method == "bm25":
        return BM25Pruning()
    elif method == "sentence_bert":
        return SentenceBERTPruning()
    else:
        raise ValueError(f"Unknown pruning method: {method}")
```

**Update ToGReasoningEngine to use pruning methods:**

```python
# In backend/app/services/tog_service.py

class ToGReasoningEngine:
    def __init__(self, graph_service, llm_service, config: ToGConfig):
        # ... existing init code ...

        # Initialize pruning method
        from app.services.pruning_methods import create_pruning_method
        self.pruning_method = create_pruning_method(
            config.pruning_method,
            llm_service=llm_service
        )

    async def _explore_relations(self, question, entities, document_ids):
        # Get relations from graph (same as before)
        available_relations = self._get_entity_relations(entities, document_ids)

        # Use pruning method for scoring
        scored_relations = await self.pruning_method.score_relations(
            question=question,
            relations=available_relations,
            context={
                'entities': ', '.join(entities),
                'previous_relations': ', '.join(self.explored_relations)
            }
        )

        # ... rest of method ...

    async def _score_entities(self, question, candidates, document_ids):
        # Use pruning method for scoring
        scored_entities = await self.pruning_method.score_entities(
            question=question,
            entities=candidates,
            context={
                'reasoning_summary': self._format_reasoning_summary(),
                'relation': candidates[0].get('relation_used', 'RELATES_TO') if candidates else ''
            }
        )

        # Merge scores into candidates
        # ... (same as before) ...
```

---

### Task 3.4: Handle Edge Cases & Error Scenarios

**Objective:** Robust error handling for graph traversal

**Steps:**
1. Handle empty graph (no entities/relations)
2. Handle disconnected entities (no path found)
3. Handle LLM API failures (retry + fallback)
4. Handle infinite loops (cycle detection)
5. Handle timeout scenarios

**Deliverables:**
- Error handling code
- Fallback strategies
- Tests for edge cases
- Error logging and monitoring

**Implementation:**

```python
# In backend/app/services/tog_service.py

class ToGReasoningEngine:

    # Add error handling wrapper
    async def reason(self, question: str, document_ids: Optional[List[int]] = None):
        """Main reasoning method with error handling."""
        import time
        start_time = time.time()

        try:
            return await self._reason_impl(question, document_ids)
        except Exception as e:
            logger.error(f"ToG reasoning failed: {str(e)}", exc_info=True)

            # Fallback to direct answer generation
            answer, confidence = await self._generate_fallback_answer(question)

            processing_time = int((time.time() - start_time) * 1000)

            return (
                answer,
                [],  # No reasoning path
                [],  # No triplets
                confidence
            )

    async def _reason_impl(self, question: str, document_ids: Optional[List[int]] = None):
        """Internal reasoning implementation (original logic)."""
        # Original reason() implementation goes here
        # ... (all the code from Task 2.3) ...

        # Add max iteration safeguard
        MAX_ITERATIONS = 10
        iteration = 0

        sufficient = False
        for depth in range(self.config.search_depth):
            iteration += 1
            if iteration > MAX_ITERATIONS:
                logger.warning(f"Max iterations ({MAX_ITERATIONS}) reached")
                break

            # ... rest of reasoning loop ...

            # Cycle detection
            if self._detect_cycle():
                logger.warning("Cycle detected, stopping exploration")
                break

        # ... generate answer ...

    def _detect_cycle(self) -> bool:
        """Detect if we're revisiting same entities (cycle)."""
        if len(self.reasoning_path) < 2:
            return False

        # Check if current entities same as previous step
        if len(self.reasoning_path) >= 2:
            current_entities = set(self.reasoning_path[-1].entities)
            previous_entities = set(self.reasoning_path[-2].entities)

            # If 80%+ overlap, likely a cycle
            overlap = len(current_entities & previous_entities)
            if overlap / len(current_entities) > 0.8:
                return True

        return False

    # Handle empty graph
    async def _extract_topic_entities(self, question, document_ids):
        entities = await self._extract_topic_entities_impl(question, document_ids)

        if not entities:
            logger.warning("No topic entities found in graph")
            # Try without document filter
            if document_ids:
                logger.info("Retrying without document filter")
                entities = await self._extract_topic_entities_impl(question, None)

            # Still nothing? Use fallback
            if not entities:
                raise ValueError(
                    "No entities found in knowledge graph. "
                    "Please ensure documents have been processed and entities extracted."
                )

        return entities

    # Handle disconnected entities
    async def _get_candidate_entities(self, source_entities, relations, document_ids):
        candidates = await self._get_candidate_entities_impl(
            source_entities, relations, document_ids
        )

        if not candidates:
            logger.warning(f"No connected entities found for: {source_entities}")

            # Try expanding to 2-hop neighbors
            logger.info("Attempting 2-hop expansion")
            candidates = await self._get_2hop_entities(source_entities, document_ids)

            if not candidates:
                logger.warning("Graph exploration dead-end reached")
                # This will trigger sufficiency check / answer generation

        return candidates

    async def _get_2hop_entities(self, source_entities, document_ids):
        """Try 2-hop expansion to find connected entities."""
        query = """
        MATCH (source:Entity)-[:RELATES_TO*1..2]-(target:Entity)
        WHERE source.name IN $source_entities
        AND NOT target.name IN $source_entities
        """

        if document_ids:
            query += " AND target.document_id IN $document_ids"

        query += """
        RETURN DISTINCT target.name as entity_name,
               target.description as description,
               target.type as entity_type
        LIMIT 20
        """

        with self.graph_service.get_session() as session:
            result = session.run(query, {
                "source_entities": source_entities,
                "document_ids": document_ids
            })

            entities = []
            for record in result:
                entities.append({
                    "entity_name": record["entity_name"],
                    "description": record["description"] or "",
                    "entity_type": record["entity_type"] or "UNKNOWN",
                    "relation_used": "2-HOP",
                    "confidence": 0.3
                })

        return entities
```

---

## Phase 4: Integration with Existing System

**Duration:** 1-2 weeks
**Goal:** Integrate ToG with existing GraphToG API and frontend

### Task 4.1: Create ToG API Endpoints

**Objective:** Add FastAPI endpoints for ToG queries

**Steps:**
1. Create `backend/app/api/endpoints/tog_queries.py`
2. Implement POST `/api/query/tog` endpoint
3. Implement GET `/api/query/tog/explain/{query_id}` endpoint
4. Implement POST `/api/query/tog/config` endpoint
5. Add endpoints to main FastAPI router

**Deliverables:**
- ToG API endpoints
- API documentation (Swagger)
- Integration tests

**Implementation:**

```python
# backend/app/api/endpoints/tog_queries.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import time
import logging

from app.db.postgres import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.query import Query
from app.schemas.tog_query import (
    ToGQueryRequest,
    ToGQueryResponse,
    ToGConfig,
    ToGReasoningStep,
    ToGTriplet
)
from app.services.tog_service import ToGReasoningEngine
from app.services.graph_service import GraphService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/query/tog", tags=["ToG Queries"])

@router.post("", response_model=ToGQueryResponse)
async def query_with_tog(
    request: ToGQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process a query using Tree of Graphs (ToG) reasoning.

    ToG performs iterative graph exploration with LLM-guided pruning
    to discover multi-hop reasoning paths for complex questions.

    **Parameters:**
    - **question**: The question to answer
    - **document_ids**: Optional list of document IDs to search within
    - **config**: ToG configuration parameters (width, depth, pruning method, etc.)

    **Returns:**
    - **answer**: Generated answer
    - **reasoning_path**: Step-by-step reasoning process
    - **retrieved_triplets**: Knowledge graph triplets used
    - **confidence**: Answer confidence score (0-1)
    - **processing_time_ms**: Processing time in milliseconds
    """
    logger.info(f"ToG query from user {current_user.id}: {request.question}")

    start_time = time.time()

    try:
        # Initialize services
        graph_service = GraphService()
        llm_service = LLMService()

        # Create ToG reasoning engine
        config = request.config or ToGConfig()
        tog_engine = ToGReasoningEngine(
            graph_service=graph_service,
            llm_service=llm_service,
            config=config
        )

        # Perform reasoning
        answer, reasoning_path, triplets, confidence = await tog_engine.reason(
            question=request.question,
            document_ids=request.document_ids
        )

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Save query to database
        db_query = Query(
            user_id=current_user.id,
            question=request.question,
            answer=answer,
            query_type="tog",
            confidence=confidence,
            processing_time_ms=processing_time_ms,
            tog_config=config.dict(),
            reasoning_path=[step.dict() for step in reasoning_path],
            retrieved_triplets=[triplet.dict() for triplet in triplets]
        )
        db.add(db_query)
        db.commit()
        db.refresh(db_query)

        logger.info(
            f"ToG query completed in {processing_time_ms}ms "
            f"with confidence {confidence:.2f}"
        )

        # Return response
        return ToGQueryResponse(
            answer=answer,
            reasoning_path=reasoning_path,
            retrieved_triplets=triplets,
            confidence=confidence,
            processing_time_ms=processing_time_ms,
            query_id=db_query.id
        )

    except Exception as e:
        logger.error(f"ToG query failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ToG query processing failed: {str(e)}"
        )

@router.get("/explain/{query_id}")
async def get_reasoning_explanation(
    query_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed reasoning explanation for a ToG query.

    Returns the complete reasoning path with entity scores, relation selections,
    and sufficiency evaluations at each depth level.
    """
    # Fetch query
    db_query = db.query(Query).filter(
        Query.id == query_id,
        Query.user_id == current_user.id
    ).first()

    if not db_query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query {query_id} not found"
        )

    if db_query.query_type != "tog":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query {query_id} is not a ToG query"
        )

    return {
        "query_id": db_query.id,
        "question": db_query.question,
        "answer": db_query.answer,
        "confidence": db_query.confidence,
        "reasoning_path": db_query.reasoning_path,
        "retrieved_triplets": db_query.retrieved_triplets,
        "config": db_query.tog_config,
        "created_at": db_query.created_at.isoformat()
    }

@router.get("/history")
async def get_tog_query_history(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's ToG query history."""
    queries = db.query(Query).filter(
        Query.user_id == current_user.id,
        Query.query_type == "tog"
    ).order_by(
        Query.created_at.desc()
    ).offset(skip).limit(limit).all()

    return {
        "queries": [
            {
                "id": q.id,
                "question": q.question,
                "answer": q.answer[:200] + "..." if len(q.answer) > 200 else q.answer,
                "confidence": q.confidence,
                "processing_time_ms": q.processing_time_ms,
                "created_at": q.created_at.isoformat()
            }
            for q in queries
        ],
        "total": db.query(Query).filter(
            Query.user_id == current_user.id,
            Query.query_type == "tog"
        ).count()
    }

# Add default config endpoint
DEFAULT_TOG_CONFIG = ToGConfig()

@router.get("/config/default", response_model=ToGConfig)
async def get_default_config():
    """Get default ToG configuration."""
    return DEFAULT_TOG_CONFIG

@router.post("/config/validate", response_model=ToGConfig)
async def validate_config(config: ToGConfig):
    """Validate ToG configuration parameters."""
    # Pydantic validation happens automatically
    return config
```

**Add to main router:**

```python
# backend/app/main.py

from app.api.endpoints import tog_queries

# ... existing code ...

# Include ToG router
app.include_router(tog_queries.router)
```

---

### Task 4.2: Update Frontend UI for ToG Queries

**Objective:** Add ToG query interface to frontend

**Steps:**
1. Create ToG query component (React)
2. Add ToG configuration panel
3. Display reasoning path visualization
4. Add triplet visualization
5. Update query interface to support multiple query types

**Deliverables:**
- ToG query React component
- Configuration UI
- Reasoning path visualization
- Updated query interface

**Implementation:**

```typescript
// frontend/components/tog-query-interface.tsx

'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Loader2, Network, GitBranch, ChevronRight } from 'lucide-react';

interface ToGConfig {
  search_width: number;
  search_depth: number;
  exploration_temp: number;
  reasoning_temp: number;
  num_retain_entity: number;
  pruning_method: 'llm' | 'bm25' | 'sentence_bert';
  enable_sufficiency_check: boolean;
}

interface ToGReasoningStep {
  depth: number;
  entities: string[];
  relations_explored: string[];
  selected_relations: string[];
  entity_scores?: Record<string, number>;
  sufficiency_score?: number;
  sufficient?: boolean;
}

interface ToGTriplet {
  subject: string;
  relation: string;
  object: string;
  confidence?: number;
}

interface ToGQueryResponse {
  answer: string;
  reasoning_path: ToGReasoningStep[];
  retrieved_triplets: ToGTriplet[];
  confidence: number;
  processing_time_ms: number;
  query_id?: number;
}

export default function ToGQueryInterface() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ToGQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ToG configuration
  const [config, setConfig] = useState<ToGConfig>({
    search_width: 3,
    search_depth: 3,
    exploration_temp: 0.4,
    reasoning_temp: 0.0,
    num_retain_entity: 5,
    pruning_method: 'llm',
    enable_sufficiency_check: true,
  });

  const [showConfig, setShowConfig] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!question.trim()) return;

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch('/api/query/tog', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          question,
          config,
        }),
      });

      if (!res.ok) {
        throw new Error(`Query failed: ${res.statusText}`);
      }

      const data: ToGQueryResponse = await res.json();
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Query Input */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="w-5 h-5" />
            Tree of Graphs Query
          </CardTitle>
          <CardDescription>
            Ask complex questions that require multi-hop reasoning through the knowledge graph
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="question">Question</Label>
              <Input
                id="question"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="e.g., How is entity A connected to entity B?"
                disabled={loading}
              />
            </div>

            <div className="flex gap-2">
              <Button type="submit" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  'Submit Query'
                )}
              </Button>

              <Button
                type="button"
                variant="outline"
                onClick={() => setShowConfig(!showConfig)}
              >
                {showConfig ? 'Hide' : 'Show'} Configuration
              </Button>
            </div>

            {/* Configuration Panel */}
            {showConfig && (
              <Card className="mt-4">
                <CardHeader>
                  <CardTitle className="text-sm">ToG Configuration</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Search Width: {config.search_width}</Label>
                      <Slider
                        value={[config.search_width]}
                        onValueChange={(val) => setConfig({ ...config, search_width: val[0] })}
                        min={1}
                        max={10}
                        step={1}
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Max entities to explore per depth level
                      </p>
                    </div>

                    <div>
                      <Label>Search Depth: {config.search_depth}</Label>
                      <Slider
                        value={[config.search_depth]}
                        onValueChange={(val) => setConfig({ ...config, search_depth: val[0] })}
                        min={1}
                        max={5}
                        step={1}
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Max traversal depth (hops)
                      </p>
                    </div>

                    <div>
                      <Label>Pruning Method</Label>
                      <Select
                        value={config.pruning_method}
                        onValueChange={(val: any) => setConfig({ ...config, pruning_method: val })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="llm">LLM (Highest Quality)</SelectItem>
                          <SelectItem value="sentence_bert">SentenceBERT (Balanced)</SelectItem>
                          <SelectItem value="bm25">BM25 (Fastest)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label>Retain Entities: {config.num_retain_entity}</Label>
                      <Slider
                        value={[config.num_retain_entity]}
                        onValueChange={(val) => setConfig({ ...config, num_retain_entity: val[0] })}
                        min={1}
                        max={20}
                        step={1}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </form>

          {/* Error Display */}
          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
              <strong>Error:</strong> {error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {response && (
        <Tabs defaultValue="answer" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="answer">Answer</TabsTrigger>
            <TabsTrigger value="reasoning">Reasoning Path</TabsTrigger>
            <TabsTrigger value="triplets">Retrieved Triplets</TabsTrigger>
          </TabsList>

          <TabsContent value="answer">
            <Card>
              <CardHeader>
                <CardTitle>Answer</CardTitle>
                <div className="flex gap-2 items-center text-sm text-muted-foreground">
                  <Badge variant="outline">
                    Confidence: {(response.confidence * 100).toFixed(1)}%
                  </Badge>
                  <Badge variant="outline">
                    {response.processing_time_ms}ms
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap">{response.answer}</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="reasoning">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <GitBranch className="w-5 h-5" />
                  Reasoning Path
                </CardTitle>
                <CardDescription>
                  Step-by-step graph exploration process
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {response.reasoning_path.map((step, idx) => (
                    <div key={idx} className="border-l-2 border-blue-500 pl-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge>Depth {step.depth}</Badge>
                        {step.sufficient && (
                          <Badge variant="outline" className="bg-green-50">
                            ✓ Sufficient
                          </Badge>
                        )}
                      </div>

                      <div className="space-y-2 text-sm">
                        <div>
                          <strong>Entities:</strong>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {step.entities.map((entity, i) => (
                              <Badge key={i} variant="secondary">{entity}</Badge>
                            ))}
                          </div>
                        </div>

                        <div>
                          <strong>Relations Explored:</strong>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {step.relations_explored.map((rel, i) => (
                              <Badge key={i} variant="outline">{rel}</Badge>
                            ))}
                          </div>
                        </div>

                        <div>
                          <strong>Selected:</strong>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {step.selected_relations.map((rel, i) => (
                              <Badge key={i} className="bg-blue-100">{rel}</Badge>
                            ))}
                          </div>
                        </div>

                        {step.sufficiency_score !== undefined && (
                          <div>
                            <strong>Sufficiency Score:</strong>{' '}
                            {(step.sufficiency_score * 100).toFixed(1)}%
                          </div>
                        )}
                      </div>

                      {idx < response.reasoning_path.length - 1 && (
                        <ChevronRight className="w-4 h-4 text-muted-foreground mt-2" />
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="triplets">
            <Card>
              <CardHeader>
                <CardTitle>Retrieved Triplets</CardTitle>
                <CardDescription>
                  Knowledge graph facts used to answer the question
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {response.retrieved_triplets.map((triplet, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 p-3 bg-gray-50 rounded-md text-sm"
                    >
                      <Badge variant="outline">{triplet.subject}</Badge>
                      <span className="text-muted-foreground">→</span>
                      <Badge>{triplet.relation}</Badge>
                      <span className="text-muted-foreground">→</span>
                      <Badge variant="outline">{triplet.object}</Badge>

                      {triplet.confidence !== undefined && (
                        <Badge variant="secondary" className="ml-auto">
                          {(triplet.confidence * 100).toFixed(0)}%
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
```

---

### Task 4.3: Add ToG to Existing Query Service

**Objective:** Integrate ToG as a query type option alongside local/global/hybrid

**Steps:**
1. Update query classification to include ToG option
2. Add logic to route queries to ToG when appropriate
3. Update existing query endpoint to support ToG
4. Ensure backward compatibility
5. Add query type selection in frontend

**Deliverables:**
- Updated query service with ToG integration
- Query routing logic
- Updated API endpoint
- Frontend query type selector

**Implementation:**

```python
# backend/app/services/query_service.py

from typing import Tuple, Optional, List
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.tog_service import ToGReasoningEngine
from app.services.graph_service import GraphService
from app.schemas.tog_query import ToGConfig

class QueryService:
    """Enhanced query service with ToG support."""

    def __init__(self):
        self.llm_service = LLMService()
        self.retrieval_service = RetrievalService()
        self.graph_service = GraphService()

    async def process_query(
        self,
        question: str,
        document_ids: Optional[List[int]] = None,
        query_type: Optional[str] = None,  # "local", "global", "hybrid", "tog", or None for auto
        tog_config: Optional[ToGConfig] = None
    ) -> Tuple[str, str, float, dict]:
        """
        Process query with automatic or manual query type selection.

        Returns:
            Tuple of (answer, query_type_used, confidence, metadata)
        """
        # Auto-classify if not specified
        if query_type is None:
            query_type = await self._classify_query_type(question)

        # Route to appropriate method
        if query_type == "tog":
            return await self._process_tog_query(question, document_ids, tog_config)
        elif query_type == "local":
            return await self._process_local_query(question, document_ids)
        elif query_type == "global":
            return await self._process_global_query(question, document_ids)
        elif query_type == "hybrid":
            return await self._process_hybrid_query(question, document_ids)
        else:
            raise ValueError(f"Unknown query type: {query_type}")

    async def _classify_query_type(self, question: str) -> str:
        """
        Classify question into query type.

        Classification logic:
        - Multi-hop questions (how is X connected to Y) → tog
        - Specific entity questions → local
        - Broad thematic questions → global
        - Mixed questions → hybrid
        """
        from app.services.prompt import QUERY_CLASSIFICATION_PROMPT

        # Enhanced prompt with ToG option
        prompt = f"""Classify the following question into one of these query types:

1. **local**: Questions about specific entities or relationships
   - Example: "What is the relationship between X and Y?"
   - Example: "Tell me about entity X"

2. **global**: Broad questions about themes, trends, or summaries
   - Example: "What are the main themes in the documents?"
   - Example: "Summarize the key findings"

3. **hybrid**: Questions that combine specific and broad aspects
   - Example: "How does X relate to the overall theme?"

4. **tog**: Questions requiring multi-hop reasoning or connection discovery
   - Example: "How is X connected to Y through intermediate entities?"
   - Example: "What is the chain of relationships between A and B?"
   - Example: "Trace the path from X to Y"

Question: {question}

Return JSON: {{"query_type": "local|global|hybrid|tog", "reasoning": "..."}}
"""

        response = await self.llm_service.generate_text(prompt, temperature=0.0)
        result = self.llm_service._parse_json_response(response)

        query_type = result.get("query_type", "hybrid")
        return query_type

    async def _process_tog_query(
        self,
        question: str,
        document_ids: Optional[List[int]],
        config: Optional[ToGConfig]
    ) -> Tuple[str, str, float, dict]:
        """Process query using ToG reasoning."""
        config = config or ToGConfig()

        tog_engine = ToGReasoningEngine(
            graph_service=self.graph_service,
            llm_service=self.llm_service,
            config=config
        )

        answer, reasoning_path, triplets, confidence = await tog_engine.reason(
            question, document_ids
        )

        metadata = {
            "reasoning_path": [step.dict() for step in reasoning_path],
            "retrieved_triplets": [t.dict() for t in triplets],
            "config": config.dict()
        }

        return answer, "tog", confidence, metadata

    # Existing methods (local, global, hybrid) remain unchanged
    async def _process_local_query(self, question, document_ids):
        # ... existing implementation ...
        pass

    async def _process_global_query(self, question, document_ids):
        # ... existing implementation ...
        pass

    async def _process_hybrid_query(self, question, document_ids):
        # ... existing implementation ...
        pass
```

**Update main query endpoint:**

```python
# backend/app/api/endpoints/queries.py

from app.schemas.tog_query import ToGConfig

@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    query_type: Optional[str] = None,  # New parameter
    tog_config: Optional[ToGConfig] = None,  # New parameter
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process a query with automatic or manual query type selection.

    Supports: local, global, hybrid, and tog (Tree of Graphs) queries.
    """
    query_service = QueryService()

    answer, query_type_used, confidence, metadata = await query_service.process_query(
        question=request.question,
        document_ids=request.document_ids,
        query_type=query_type,
        tog_config=tog_config
    )

    # Save to database
    # ... (existing code) ...

    return QueryResponse(
        answer=answer,
        query_type=query_type_used,
        confidence=confidence,
        metadata=metadata
    )
```

---

### Task 4.4: Testing & Validation

**Objective:** Comprehensive testing of ToG integration

**Steps:**
1. Create integration tests for ToG API
2. Test with various question types
3. Validate reasoning paths
4. Performance testing (latency, throughput)
5. Compare ToG vs existing methods (accuracy)

**Deliverables:**
- Integration test suite
- Test cases with expected outputs
- Performance benchmark report
- Accuracy comparison report

**Test Implementation:**

```python
# backend/tests/test_tog_integration.py

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.tog_query import ToGConfig

@pytest.mark.integration
class TestToGIntegration:

    def test_tog_query_basic(self, authenticated_client, sample_documents):
        """Test basic ToG query."""
        response = authenticated_client.post(
            "/api/query/tog",
            json={
                "question": "How is Microsoft related to AI research?",
                "config": {
                    "search_width": 3,
                    "search_depth": 2,
                    "pruning_method": "llm"
                }
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "reasoning_path" in data
        assert "retrieved_triplets" in data
        assert "confidence" in data
        assert len(data["reasoning_path"]) > 0

    def test_tog_multi_hop_reasoning(self, authenticated_client, sample_documents):
        """Test multi-hop reasoning capability."""
        response = authenticated_client.post(
            "/api/query/tog",
            json={
                "question": "What connects Entity A to Entity C through intermediate entities?",
                "config": {
                    "search_width": 3,
                    "search_depth": 3
                }
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should have multiple reasoning steps
        assert len(data["reasoning_path"]) >= 2

        # Should have retrieved multiple triplets
        assert len(data["retrieved_triplets"]) >= 2

    def test_tog_sufficiency_check(self, authenticated_client, sample_documents):
        """Test that sufficiency check stops exploration early."""
        response = authenticated_client.post(
            "/api/query/tog",
            json={
                "question": "What is Entity X?",  # Simple question
                "config": {
                    "search_width": 3,
                    "search_depth": 5,  # Max depth
                    "enable_sufficiency_check": True
                }
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should stop before max depth for simple question
        assert len(data["reasoning_path"]) < 5

        # Last step should indicate sufficiency
        last_step = data["reasoning_path"][-1]
        assert last_step.get("sufficient") == True

    def test_tog_pruning_methods(self, authenticated_client, sample_documents):
        """Test different pruning methods."""
        pruning_methods = ["llm", "bm25", "sentence_bert"]

        for method in pruning_methods:
            response = authenticated_client.post(
                "/api/query/tog",
                json={
                    "question": "How are X and Y related?",
                    "config": {
                        "pruning_method": method
                    }
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "answer" in data

    @pytest.mark.benchmark
    def test_tog_performance(self, authenticated_client, sample_documents, benchmark):
        """Benchmark ToG query performance."""
        def run_query():
            return authenticated_client.post(
                "/api/query/tog",
                json={
                    "question": "How is A connected to B?",
                    "config": {
                        "search_width": 3,
                        "search_depth": 2
                    }
                }
            )

        result = benchmark(run_query)
        assert result.status_code == 200

        # Should complete within reasonable time (< 30s)
        assert benchmark.stats.mean < 30.0

    def test_tog_vs_local_comparison(self, authenticated_client, sample_documents):
        """Compare ToG with local query for same question."""
        question = "What is the relationship between X and Y?"

        # ToG query
        tog_response = authenticated_client.post(
            "/api/query/tog",
            json={"question": question}
        )

        # Local query
        local_response = authenticated_client.post(
            "/api/query",
            json={"question": question, "query_type": "local"}
        )

        assert tog_response.status_code == 200
        assert local_response.status_code == 200

        tog_data = tog_response.json()
        local_data = local_response.json()

        # Both should produce answers
        assert len(tog_data["answer"]) > 0
        assert len(local_data["answer"]) > 0

        # ToG should have reasoning path (local doesn't)
        assert len(tog_data["reasoning_path"]) > 0

    def test_tog_empty_graph(self, authenticated_client):
        """Test ToG behavior with empty/minimal graph."""
        response = authenticated_client.post(
            "/api/query/tog",
            json={
                "question": "Tell me about nonexistent entity",
                "document_ids": [999999]  # Non-existent document
            }
        )

        # Should handle gracefully (not crash)
        assert response.status_code in [200, 404, 500]

        if response.status_code == 200:
            data = response.json()
            # Should provide fallback answer
            assert "answer" in data
            # Confidence should be low
            assert data["confidence"] < 0.5
```

---

## Phase 5: Testing & Optimization

**Duration:** 1-2 weeks
**Goal:** Ensure quality, performance, and reliability

### Task 5.1: Unit Testing

**Objective:** Comprehensive unit tests for all ToG components

**Steps:**
1. Test each ToG service method individually
2. Mock external dependencies (LLM, Neo4j)
3. Test edge cases and error conditions
4. Achieve >80% code coverage
5. Add tests to CI/CD pipeline

**Deliverables:**
- Complete unit test suite
- Mocked dependencies
- Coverage report (>80%)
- CI/CD integration

---

### Task 5.2: Performance Optimization

**Objective:** Optimize ToG query processing speed

**Steps:**
1. Profile ToG queries (identify bottlenecks)
2. Optimize Neo4j queries (indexes, batching)
3. Implement caching (Redis) for LLM responses
4. Parallelize entity scoring when possible
5. Tune configuration defaults

**Deliverables:**
- Performance profiling report
- Optimization implementations
- Before/after benchmarks
- Recommended default config

**Optimization Strategies:**

```python
# backend/app/services/tog_service.py

# 1. Parallel entity scoring
async def _score_entities_parallel(self, question, candidates, document_ids):
    """Score entities in parallel batches."""
    import asyncio

    # Split into batches
    batch_size = 10
    batches = [candidates[i:i+batch_size] for i in range(0, len(candidates), batch_size)]

    # Score batches in parallel
    tasks = [
        self._score_entity_batch(question, batch, document_ids)
        for batch in batches
    ]

    results = await asyncio.gather(*tasks)

    # Flatten results
    return [entity for batch_result in results for entity in batch_result]

# 2. Cache LLM responses
from functools import lru_cache
import hashlib

def _cache_key(self, prompt: str) -> str:
    """Generate cache key for prompt."""
    return hashlib.md5(prompt.encode()).hexdigest()

async def _generate_with_cache(self, prompt: str, temperature: float) -> str:
    """Generate LLM response with caching."""
    cache_key = f"tog_llm:{self._cache_key(prompt)}"

    # Check Redis cache
    cached = await self.redis.get(cache_key)
    if cached:
        return cached

    # Generate
    response = await self.llm_service.generate_text(prompt, temperature)

    # Cache for 1 hour
    await self.redis.setex(cache_key, 3600, response)

    return response

# 3. Batch Neo4j queries
def _batch_query_entities(self, entity_relation_pairs):
    """Query multiple entity-relation pairs in single query."""
    query = """
    UNWIND $pairs as pair
    MATCH (e:Entity {name: pair.entity})-[r:RELATES_TO]->(target:Entity)
    WHERE r.type = pair.relation
    RETURN pair.entity as source, target.name as target, r.type as relation
    """

    with self.graph_service.get_session() as session:
        result = session.run(query, {"pairs": entity_relation_pairs})
        return list(result)
```

---

### Task 5.3: Quality Assurance

**Objective:** Validate ToG answer quality and accuracy

**Steps:**
1. Create test dataset with ground-truth answers
2. Run ToG on test questions
3. Evaluate answer correctness (manual + automated)
4. Compare ToG vs baseline methods
5. Tune prompts based on failures

**Deliverables:**
- Test dataset (questions + ground truth)
- Evaluation script
- Quality metrics report
- Prompt improvements

---

### Task 5.4: User Acceptance Testing

**Objective:** Validate ToG with real users

**Steps:**
1. Deploy to staging environment
2. Recruit beta testers
3. Collect user feedback
4. Identify usability issues
5. Iterate on UI/UX

**Deliverables:**
- Beta testing plan
- User feedback report
- UI/UX improvements
- Bug fixes

---

## Phase 6: Documentation & Deployment

**Duration:** 1 week
**Goal:** Complete documentation and production deployment

### Task 6.1: Technical Documentation

**Objective:** Comprehensive developer and user documentation

**Steps:**
1. Write ToG architecture documentation
2. Document API endpoints (Swagger/OpenAPI)
3. Create configuration guide
4. Write troubleshooting guide
5. Add code comments and docstrings

**Deliverables:**
- Architecture documentation
- API documentation (auto-generated)
- Configuration guide
- Troubleshooting guide

---

### Task 6.2: User Documentation

**Objective:** End-user guides and tutorials

**Steps:**
1. Write user guide for ToG queries
2. Create tutorial with examples
3. Document query type selection
4. Explain reasoning path visualization
5. Add FAQ section

**Deliverables:**
- User guide
- Tutorial with examples
- FAQ document

---

### Task 6.3: Production Deployment

**Objective:** Deploy ToG to production

**Steps:**
1. Final testing in staging environment
2. Database migration (add ToG fields)
3. Deploy backend updates
4. Deploy frontend updates
5. Monitor initial production usage

**Deliverables:**
- Production deployment
- Monitoring dashboard
- Rollback plan
- Post-deployment report

**Deployment Checklist:**

```bash
# 1. Database migration
cd backend
uv run alembic upgrade head

# 2. Install new dependencies
uv sync

# 3. Update environment variables
# Add to .env:
# ENABLE_TOG=true
# TOG_DEFAULT_SEARCH_WIDTH=3
# TOG_DEFAULT_SEARCH_DEPTH=3

# 4. Restart services
docker-compose restart backend

# 5. Frontend deployment
cd frontend
npm run build
npm start

# 6. Verify deployment
curl -X POST http://localhost:8000/api/query/tog/config/default
```

---

### Task 6.4: Monitoring & Observability

**Objective:** Set up monitoring for ToG queries

**Steps:**
1. Add logging for ToG queries
2. Track metrics (latency, success rate, confidence)
3. Set up alerts for failures
4. Create monitoring dashboard
5. Implement usage analytics

**Deliverables:**
- Logging implementation
- Metrics collection
- Alerting rules
- Monitoring dashboard

**Metrics to Track:**

```python
# backend/app/services/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# ToG-specific metrics
tog_queries_total = Counter(
    'tog_queries_total',
    'Total number of ToG queries',
    ['status', 'pruning_method']
)

tog_query_duration = Histogram(
    'tog_query_duration_seconds',
    'ToG query processing duration',
    ['pruning_method'],
    buckets=[1, 5, 10, 30, 60, 120]
)

tog_reasoning_depth = Histogram(
    'tog_reasoning_depth',
    'Depth of reasoning path',
    buckets=[1, 2, 3, 4, 5]
)

tog_confidence_score = Histogram(
    'tog_confidence_score',
    'Answer confidence score',
    buckets=[0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
)

tog_triplets_retrieved = Histogram(
    'tog_triplets_retrieved',
    'Number of triplets retrieved',
    buckets=[1, 5, 10, 20, 50, 100]
)
```

---

## Risk Management

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| LLM API rate limits | High | Medium | Implement caching, use alternative pruning methods |
| Neo4j performance issues | High | Low | Optimize queries, add indexes, use query caching |
| ToG slower than existing methods | Medium | Medium | Parallel processing, caching, make ToG optional |
| Graph disconnectivity | Medium | Low | Implement 2-hop fallback, cross-document search |
| Prompt engineering challenges | Medium | Medium | Iterative testing, use proven GraphRAG prompts |
| Integration complexity | Low | Low | Incremental integration, comprehensive testing |

### Project Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Timeline overrun | Medium | Medium | Phased implementation, prioritize core features |
| Scope creep | Medium | Medium | Strict phase boundaries, defer nice-to-haves |
| Resource constraints | Low | Low | Use existing infrastructure, leverage LLMs |
| User adoption | Medium | Low | Comprehensive documentation, gradual rollout |

---

## Success Metrics

### Technical Metrics

1. **Performance:**
   - ToG query latency < 15s (90th percentile)
   - System throughput >= existing query methods
   - Cache hit rate > 30%

2. **Quality:**
   - Answer correctness > 85% on test dataset
   - Confidence calibration (high confidence → correct answers)
   - Reasoning path coherence (human evaluation)

3. **Reliability:**
   - Error rate < 5%
   - Successful fallback on failures
   - Uptime > 99.5%

### User Metrics

1. **Adoption:**
   - ToG usage >= 20% of total queries (after 3 months)
   - User retention (users who try ToG return)

2. **Satisfaction:**
   - User satisfaction score > 4/5
   - Positive feedback on reasoning transparency
   - Low support ticket rate

3. **Use Cases:**
   - Successful use for complex multi-hop questions
   - Preference over existing methods for appropriate queries

---

## Appendix A: Configuration Reference

### ToG Configuration Parameters

```python
class ToGConfig:
    """
    Configuration for Tree of Graphs reasoning.

    Parameters:
        search_width: Maximum number of entities to explore at each depth level.
                      Higher values = more comprehensive but slower.
                      Range: 1-10, Default: 3

        search_depth: Maximum depth of graph traversal (number of hops).
                      Higher values = deeper reasoning but slower.
                      Range: 1-5, Default: 3

        exploration_temp: LLM temperature for exploration phase (entity/relation scoring).
                          Higher values = more diverse exploration.
                          Range: 0.0-1.0, Default: 0.4

        reasoning_temp: LLM temperature for reasoning phase (answer generation).
                        Lower values = more focused answers.
                        Range: 0.0-1.0, Default: 0.0

        num_retain_entity: Maximum entities to retain during candidate sampling.
                           When candidates exceed 20, random sample to this value.
                           Range: 1-20, Default: 5

        pruning_method: Method for scoring entities and relations.
                        - "llm": Highest quality, slowest (uses LLM)
                        - "sentence_bert": Semantic similarity, medium speed
                        - "bm25": Keyword matching, fastest
                        Default: "llm"

        enable_sufficiency_check: Whether to check if information is sufficient
                                  to answer before reaching max depth.
                                  Enables early stopping for simple questions.
                                  Default: True
    """
```

### Recommended Configurations by Use Case

```python
# Fast queries (for real-time applications)
FAST_CONFIG = ToGConfig(
    search_width=2,
    search_depth=2,
    pruning_method="bm25",
    enable_sufficiency_check=True
)

# Balanced (default)
BALANCED_CONFIG = ToGConfig(
    search_width=3,
    search_depth=3,
    pruning_method="sentence_bert",
    enable_sufficiency_check=True
)

# Comprehensive (for complex research questions)
COMPREHENSIVE_CONFIG = ToGConfig(
    search_width=5,
    search_depth=4,
    pruning_method="llm",
    enable_sufficiency_check=False  # Explore full depth
)
```

---

## Appendix B: Troubleshooting Guide

### Common Issues

**Issue:** ToG queries timeout
- **Cause:** Graph too large, depth too high
- **Solution:** Reduce search_width or search_depth, use faster pruning_method

**Issue:** Empty reasoning path returned
- **Cause:** No entities found in graph matching question
- **Solution:** Check entity extraction, try without document_ids filter

**Issue:** Low answer confidence
- **Cause:** Insufficient information in graph, disconnected entities
- **Solution:** Enable 2-hop fallback, check graph connectivity

**Issue:** LLM rate limit errors
- **Cause:** Too many LLM calls (high search_width, using llm pruning)
- **Solution:** Use bm25 or sentence_bert pruning, implement caching

---

## Appendix C: Future Enhancements

### Phase 7+ (Post-Launch)

1. **Interactive ToG:**
   - Allow users to guide exploration (select which relations to follow)
   - Visual graph exploration interface

2. **Multi-document ToG:**
   - Cross-document entity linking
   - Global knowledge graph across all documents

3. **Learning from Feedback:**
   - Track successful reasoning paths
   - Fine-tune entity/relation scoring based on user feedback

4. **Advanced Visualization:**
   - 3D graph visualization of reasoning paths
   - Interactive reasoning tree

5. **ToG Precomputation:**
   - Pre-compute common reasoning paths
   - Cache popular query patterns

6. **Hybrid ToG + RAG:**
   - Combine ToG with vector search
   - Use embeddings to guide exploration

---

## Conclusion

This implementation plan provides a comprehensive roadmap for integrating Tree of Graphs (ToG) reasoning into the GraphToG system. The phased approach ensures:

- **Phase 1:** Solid foundation through analysis and design
- **Phase 2:** Core ToG reasoning engine implementation
- **Phase 3:** Robust graph traversal and optimization
- **Phase 4:** Seamless integration with existing system
- **Phase 5:** Quality assurance and performance optimization
- **Phase 6:** Production deployment with monitoring

Each phase builds on the previous, with clear deliverables and success criteria. The plan balances innovation (ToG multi-hop reasoning) with pragmatism (fallbacks, error handling, performance optimization).

**Estimated Total Timeline:** 8-12 weeks

**Next Steps:**
1. Review and approve this plan
2. Set up development environment
3. Begin Phase 1: Foundation & Analysis
4. Regular progress reviews (weekly)

Good luck with your ToG implementation! 🚀
