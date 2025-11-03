# ToG vs GraphRAG Analysis: Integration Strategy

**Date**: 2025-02-11
**Question**: Nếu implement ToG cho retrieval và answer generation, có cần thực hiện đầy đủ GraphRAG improvements không?

---

## Executive Summary

**Câu trả lời ngắn gọn**: **KHÔNG, không cần implement đầy đủ tất cả GraphRAG improvements nếu dùng ToG.**

**Lý do**: ToG và GraphRAG giải quyết **các vấn đề khác nhau** ở **các tầng khác nhau** của stack. Chúng có thể **bổ sung lẫn nhau** thay vì thay thế hoàn toàn.

---

## So sánh ToG vs GraphRAG

### ToG (Tree-of-Thoughts with Graph)

**Mục đích chính**: **Reasoning layer** - Cách LLM suy luận trên knowledge graph

**Cách hoạt động**:
```
Question → Extract Relations → Score Entities → Multi-hop Traversal → Evaluate Sufficiency → Generate Answer
```

**Key Features**:
1. **Structured graph reasoning** với explicit triplets (entity, relation, entity)
2. **Multi-stage prompting**:
   - Stage 1: Extract relevant relations
   - Stage 2: Score candidate entities
   - Stage 3: Evaluate sufficiency
   - Stage 4: Generate answer
3. **Backward chaining**: Từ question → intermediate entities → answer
4. **Sufficiency check**: Kiểm tra xem có đủ thông tin chưa trước khi trả lời
5. **Pruning**: Filter relations và entities không liên quan

**Điểm mạnh**:
- ✅ Reasoning rõ ràng, có thể trace
- ✅ Multi-hop tốt (3-5 hops)
- ✅ Kết hợp graph facts + external knowledge
- ✅ Structured, interpretable

**Điểm yếu**:
- ⚠️ Yêu cầu graph structure rõ ràng (Freebase-like)
- ⚠️ Nhiều LLM calls (mỗi stage = 1 call)
- ⚠️ Chậm hơn direct retrieval
- ⚠️ Không xử lý unstructured text tốt

---

### GraphRAG (Microsoft)

**Mục đích chính**: **Retrieval layer** - Cách extract và retrieve context từ documents

**Cách hoạt động**:
```
Documents → Entity Extraction → Graph Construction → Community Detection → Context Retrieval → Answer
```

**Key Features**:
1. **Document processing**: Parse markdown/text → entities + relationships
2. **Context assembly**:
   - Entity ranking (by relationship count)
   - Relationship prioritization (in-network vs out-of-network)
   - Token budget management
   - Community weighting
3. **Multi-level retrieval**:
   - Local: Entity neighborhoods
   - Community: Entity groups
   - Global: Dataset overview (Map-Reduce)
4. **Grounding**: Cite sources với [Data: Entities (id1, id2)]

**Điểm mạnh**:
- ✅ Xử lý unstructured documents tốt
- ✅ Scalable với large datasets
- ✅ Context quality cao (ranked, prioritized)
- ✅ Token efficiency

**Điểm yếu**:
- ⚠️ Reasoning không structured như ToG
- ⚠️ Không có explicit multi-hop logic
- ⚠️ Phụ thuộc vào LLM để connect entities

---

## Sự khác biệt căn bản

| Aspect | ToG | GraphRAG |
|--------|-----|----------|
| **Focus** | Reasoning process | Retrieval process |
| **Input** | Existing knowledge graph | Raw documents |
| **Graph type** | Freebase-like (typed relations) | Entity-relationship (flexible) |
| **Main strength** | Structured multi-hop reasoning | High-quality context assembly |
| **Answer method** | Chain triplets step-by-step | LLM synthesis from context |
| **Traceability** | Very high (explicit steps) | Medium (citations) |
| **Speed** | Slower (multiple stages) | Faster (single retrieval) |
| **Best for** | Complex reasoning queries | Document Q&A, summarization |

---

## Khi nào nên dùng gì?

### Dùng ToG khi:
- ✅ Có sẵn **structured knowledge graph** (Freebase, Wikidata)
- ✅ Cần **multi-hop reasoning** rõ ràng (3+ hops)
- ✅ Queries phức tạp kiểu: "Where was the founder of X educated?"
- ✅ Cần **explainability** cao (trace từng bước)
- ✅ Có budget LLM calls (mỗi query = 3-5 calls)

### Dùng GraphRAG khi:
- ✅ Input là **unstructured documents** (MD, PDF, text)
- ✅ Cần **extract knowledge** từ raw text
- ✅ Queries broad: "What are main themes?", "Summarize dataset"
- ✅ Cần **speed** (1 LLM call cho answer)
- ✅ Dataset lớn, cần scalability

---

## Chiến lược Integration: ToG + GraphRAG

### Option 1: Hybrid Approach (Recommended) ⭐⭐⭐

**Kết hợp cả hai** - dùng GraphRAG để build graph, ToG để reasoning:

```
Documents
    ↓
GraphRAG Processing (Entity Extraction, Graph Construction)
    ↓
Knowledge Graph (Neo4j)
    ↓
Query Classification
    ↓
    ├─ Simple Queries → GraphRAG Retrieval (fast)
    │   └─ Direct context assembly → LLM answer
    │
    └─ Complex Queries → ToG Reasoning (accurate)
        └─ Multi-stage graph traversal → Chained answer
```

**Ưu điểm**:
- ✅ Best of both worlds
- ✅ GraphRAG xử lý documents → build graph
- ✅ ToG reasoning trên graph đã build
- ✅ Query routing: simple → fast, complex → accurate

**Nhược điểm**:
- ⚠️ Complex implementation
- ⚠️ Cần maintain 2 systems

---

### Option 2: ToG-Only Approach ⭐⭐

**Chỉ dùng ToG** - skip GraphRAG improvements:

```
Documents → Manual Graph Construction → ToG Reasoning → Answer
```

**Khi nào phù hợp**:
- ✅ Bạn đã có **structured graph** sẵn (không cần extract từ documents)
- ✅ Queries chủ yếu **phức tạp, cần reasoning**
- ✅ Dataset **nhỏ** (không cần scalability)
- ✅ Ưu tiên **explainability** hơn speed

**GraphRAG improvements có thể skip**:
- ❌ Relationship prioritization (ToG tự rank relations)
- ❌ Token budget management (ToG query graph, ít text)
- ❌ Community weighting (ToG không dùng communities)
- ❌ Entity ranking (ToG score entities riêng)

**GraphRAG improvements NÊN GIỮ**:
- ✅ Entity extraction (nếu build graph từ documents)
- ✅ Graph construction (cần graph đúng format)
- ⚠️ Text unit retrieval (optional - ToG có thể query graph trực tiếp)

---

### Option 3: GraphRAG-Only Approach ⭐⭐⭐

**Chỉ dùng GraphRAG** - implement đầy đủ improvements:

```
Documents → GraphRAG Processing → Context Retrieval → LLM Answer
```

**Khi nào phù hợp**:
- ✅ Input là **unstructured documents**
- ✅ Queries chủ yếu **simple-to-medium complexity**
- ✅ Cần **speed** (< 5s response time)
- ✅ Dataset **lớn** (1000+ documents)
- ✅ Budget LLM calls **hạn chế**

**Implement đầy đủ Phase 1**:
- ✅ Relationship prioritization
- ✅ Token budget management
- ✅ Community weighting
- ✅ Entity ranking

---

## Đề xuất cho GraphToG project

### Phân tích hiện trạng:

Dự án của bạn:
- ✅ Input: **Markdown documents** (unstructured)
- ✅ Có graph service (Neo4j)
- ✅ Có entity extraction
- ✅ Có community detection
- ✅ Queries: **mixed complexity**

### Chiến lược đề xuất: **Hybrid Approach (ToG + GraphRAG)** 🎯

#### Phase 1: Implement Core GraphRAG (2 weeks)

**Mục tiêu**: Build high-quality graph foundation

Implement:
1. ✅ **Entity Ranking** (1 day) - cần cho cả ToG và GraphRAG
2. ✅ **Token Budget Management** (2 days) - important cho GraphRAG retrieval
3. ⚠️ **Relationship Prioritization** (2 days) - có thể skip nếu dùng ToG reasoning
4. ⚠️ **Community Weighting** (1 day) - skip nếu không dùng global search

**Lý do**:
- Entity ranking giúp ToG chọn starting entities tốt hơn
- Token budgets giúp fallback queries (khi ToG không phù hợp)
- Relationship prioritization có thể thay bằng ToG relation scoring

#### Phase 2: Implement ToG Reasoning (2 weeks)

**Mục tiêu**: Add structured reasoning capability

Implement:
1. ✅ **ToG Prompts** (1 day)
   - Relation extraction prompt
   - Entity scoring prompt
   - Sufficiency evaluation prompt
   - Answer generation prompt

2. ✅ **Graph Query Functions** (2 days)
   - Get relations for entity
   - Get entities by relation
   - Multi-hop traversal
   - Triplet assembly

3. ✅ **ToG Service** (2 days)
   - Stage 1: Extract relevant relations
   - Stage 2: Score candidate entities
   - Stage 3: Multi-hop traversal
   - Stage 4: Evaluate sufficiency
   - Stage 5: Generate answer

4. ✅ **Query Router** (1 day)
   - Classify query complexity
   - Route simple → GraphRAG
   - Route complex → ToG

#### Phase 3: Optimization & Testing (1 week)

**Mục tiêu**: Optimize performance, test thoroughly

1. ✅ Caching ToG intermediate results
2. ✅ Parallel relation scoring
3. ✅ Fallback strategies (ToG fails → GraphRAG)
4. ✅ Performance benchmarks
5. ✅ Integration tests

---

## Implementation Roadmap cho Hybrid Approach

### Week 1-2: GraphRAG Core (Selective)

**Skip những gì không cần**:
- ❌ Community weighting (ToG không dùng)
- ❌ Full relationship prioritization (ToG tự rank)

**Implement những gì cần**:
- ✅ Entity ranking (support ToG entity selection)
- ✅ Token budgets (fallback queries)
- ✅ Basic graph schema improvements

**Files to modify**:
- `backend/app/services/graph_service.py` - entity ranking
- `backend/app/services/retrieval_service.py` - basic token budgets
- `backend/requirements.txt` - add tiktoken

### Week 3-4: ToG Implementation

**New files to create**:

#### 1. `backend/app/services/tog_prompts.py`

```python
"""
ToG (Tree-of-Thoughts with Graph) prompt templates
Based on: https://github.com/GasolSun36/ToG
"""

EXTRACT_RELATIONS_PROMPT = """
Given a topic entity and a question, identify the most relevant relations to explore.

Topic Entity: {entity}
Question: {question}

Available Relations from this entity:
{available_relations}

Task: Score each relation's relevance (0.0 to 1.0, sum = 1.0).
Output format:
relation_name (Score: X.X)

Only include highly relevant relations. Irrelevant relations get 0.0.

Output:"""

SCORE_ENTITIES_PROMPT = """
Given candidate entities reached via a relation, score their relevance to answering the question.

Question: {question}
Relation used: {relation}
Current reasoning path: {path}

Candidate Entities:
{candidate_entities}

Task: Score each entity's relevance (0.0 to 1.0, sum = 1.0).
Output format:
entity_name (Score: X.X)

Output:"""

EVALUATE_SUFFICIENCY_PROMPT = """
Given retrieved triplets, evaluate if we have sufficient information to answer the question.

Question: {question}

Retrieved Triplets:
{triplets}

Task: Can we answer the question with these triplets?
Output format:
Sufficient: YES/NO
Reasoning: <brief explanation>
Missing: <what info is still needed, if any>

Output:"""

GENERATE_ANSWER_FROM_TRIPLETS_PROMPT = """
Answer the question using the retrieved knowledge graph triplets.

Question: {question}

Retrieved Triplets:
{triplets}

Task: Generate a coherent answer by chaining the triplets.
Use step-by-step reasoning.

Example format:
"First, [entity A] [relation] [entity B]. Second, [entity B] [relation] [entity C]. Therefore, the answer is [C]."

Answer:"""
```

#### 2. `backend/app/services/tog_service.py`

```python
"""
ToG (Tree-of-Thoughts with Graph) Service
Implements structured multi-hop reasoning on knowledge graph
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from app.services.graph_service import graph_service
from app.services.llm_service import llm_service
from app.services.tog_prompts import *

logger = logging.getLogger(__name__)

class ToGService:
    """
    Tree-of-Thoughts with Graph reasoning service

    Implements structured graph traversal and reasoning:
    1. Extract relevant relations
    2. Score candidate entities
    3. Multi-hop traversal (depth-first or breadth-first)
    4. Evaluate sufficiency
    5. Generate answer from triplets
    """

    def __init__(
        self,
        max_depth: int = 3,
        beam_width: int = 3,
        min_score_threshold: float = 0.1
    ):
        self.max_depth = max_depth
        self.beam_width = beam_width
        self.min_score_threshold = min_score_threshold

    def extract_relevant_relations(
        self,
        entity_id: str,
        question: str,
        available_relations: List[Dict[str, Any]]
    ) -> List[Tuple[str, float]]:
        """
        Stage 1: Extract and score relevant relations from entity

        Args:
            entity_id: Starting entity
            question: User question
            available_relations: List of relations from this entity

        Returns:
            List of (relation_type, score) tuples, sorted by score
        """
        # Format relations for prompt
        relations_text = "\n".join([
            f"- {rel['type']}: {rel.get('description', '')}"
            for rel in available_relations
        ])

        prompt = EXTRACT_RELATIONS_PROMPT.format(
            entity=entity_id,
            question=question,
            available_relations=relations_text
        )

        # Get LLM scoring
        response = llm_service.generate(prompt)

        # Parse scores
        scored_relations = self._parse_relation_scores(response)

        # Filter by threshold and sort
        filtered = [
            (rel, score) for rel, score in scored_relations
            if score >= self.min_score_threshold
        ]

        return sorted(filtered, key=lambda x: x[1], reverse=True)

    def score_candidate_entities(
        self,
        question: str,
        relation: str,
        candidates: List[Dict[str, Any]],
        current_path: List[Dict]
    ) -> List[Tuple[str, float]]:
        """
        Stage 2: Score candidate entities reached via relation

        Args:
            question: User question
            relation: Relation type used
            candidates: Candidate entities
            current_path: Current reasoning path (triplets so far)

        Returns:
            List of (entity_id, score) tuples
        """
        # Format candidates
        candidates_text = "\n".join([
            f"- {c['name']}: {c.get('description', '')}"
            for c in candidates
        ])

        # Format path
        path_text = " -> ".join([
            f"{t['source']} --{t['relation']}--> {t['target']}"
            for t in current_path
        ])

        prompt = SCORE_ENTITIES_PROMPT.format(
            question=question,
            relation=relation,
            candidate_entities=candidates_text,
            path=path_text if path_text else "Starting exploration"
        )

        response = llm_service.generate(prompt)

        # Parse scores
        scored_entities = self._parse_entity_scores(response)

        # Filter and sort
        filtered = [
            (ent, score) for ent, score in scored_entities
            if score >= self.min_score_threshold
        ]

        return sorted(filtered, key=lambda x: x[1], reverse=True)[:self.beam_width]

    def traverse_graph(
        self,
        start_entity_id: str,
        question: str,
        max_hops: int = None
    ) -> List[Dict[str, Any]]:
        """
        Stage 3: Multi-hop graph traversal with beam search

        Args:
            start_entity_id: Starting entity
            question: User question
            max_hops: Maximum traversal depth (default: self.max_depth)

        Returns:
            List of triplets (paths through graph)
        """
        max_hops = max_hops or self.max_depth

        # Track collected triplets
        all_triplets = []

        # Beam search: maintain top-K paths
        current_beams = [{
            "entity_id": start_entity_id,
            "path": [],
            "score": 1.0,
            "depth": 0
        }]

        for depth in range(max_hops):
            next_beams = []

            for beam in current_beams:
                entity_id = beam["entity_id"]
                current_path = beam["path"]

                # Get available relations from current entity
                relations = graph_service.get_entity_relations(entity_id)

                if not relations:
                    continue

                # Stage 1: Score relations
                scored_relations = self.extract_relevant_relations(
                    entity_id=entity_id,
                    question=question,
                    available_relations=relations
                )

                # Explore top relations
                for relation_type, rel_score in scored_relations[:self.beam_width]:
                    # Get entities via this relation
                    candidates = graph_service.get_entities_by_relation(
                        entity_id=entity_id,
                        relation_type=relation_type
                    )

                    if not candidates:
                        continue

                    # Stage 2: Score candidate entities
                    scored_entities = self.score_candidate_entities(
                        question=question,
                        relation=relation_type,
                        candidates=candidates,
                        current_path=current_path
                    )

                    # Add to next beams
                    for target_id, ent_score in scored_entities:
                        triplet = {
                            "source": entity_id,
                            "relation": relation_type,
                            "target": target_id,
                            "score": rel_score * ent_score
                        }

                        new_path = current_path + [triplet]
                        all_triplets.append(triplet)

                        next_beams.append({
                            "entity_id": target_id,
                            "path": new_path,
                            "score": beam["score"] * triplet["score"],
                            "depth": depth + 1
                        })

            # Prune: keep top beams
            current_beams = sorted(
                next_beams,
                key=lambda x: x["score"],
                reverse=True
            )[:self.beam_width]

            if not current_beams:
                break

        return all_triplets

    def evaluate_sufficiency(
        self,
        question: str,
        triplets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Stage 4: Evaluate if retrieved triplets are sufficient to answer

        Args:
            question: User question
            triplets: Retrieved graph triplets

        Returns:
            Dict with sufficiency evaluation
        """
        # Format triplets
        triplets_text = "\n".join([
            f"- {t['source']} --{t['relation']}--> {t['target']}"
            for t in triplets
        ])

        prompt = EVALUATE_SUFFICIENCY_PROMPT.format(
            question=question,
            triplets=triplets_text
        )

        response = llm_service.generate(prompt)

        # Parse response
        is_sufficient = "YES" in response.upper()

        return {
            "sufficient": is_sufficient,
            "evaluation": response,
            "triplet_count": len(triplets)
        }

    def generate_answer(
        self,
        question: str,
        triplets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Stage 5: Generate answer from triplets

        Args:
            question: User question
            triplets: Retrieved triplets

        Returns:
            Dict with answer and metadata
        """
        # Format triplets
        triplets_text = "\n".join([
            f"{i+1}. {t['source']} --{t['relation']}--> {t['target']}"
            for i, t in enumerate(triplets)
        ])

        prompt = GENERATE_ANSWER_FROM_TRIPLETS_PROMPT.format(
            question=question,
            triplets=triplets_text
        )

        answer = llm_service.generate(prompt)

        return {
            "answer": answer,
            "triplets_used": triplets,
            "reasoning_steps": len(triplets),
            "method": "tog"
        }

    def process_query(
        self,
        question: str,
        start_entity: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete ToG reasoning pipeline

        Args:
            question: User question
            start_entity: Starting entity (auto-detected if None)

        Returns:
            Dict with answer and reasoning trace
        """
        logger.info(f"ToG processing query: {question}")

        # Step 0: Find starting entity if not provided
        if not start_entity:
            # Extract entities from question using LLM
            entities = llm_service.extract_entities(question)
            if entities and entities.get("entities"):
                start_entity = entities["entities"][0]["name"]
            else:
                return {
                    "status": "error",
                    "message": "Could not identify starting entity"
                }

        # Find entity in graph
        entity_node = graph_service.find_entity_by_name(start_entity)
        if not entity_node:
            return {
                "status": "error",
                "message": f"Entity '{start_entity}' not found in graph"
            }

        start_entity_id = entity_node["id"]

        # Step 1-3: Traverse graph and collect triplets
        logger.info(f"Starting graph traversal from: {start_entity}")
        triplets = self.traverse_graph(
            start_entity_id=start_entity_id,
            question=question
        )

        logger.info(f"Collected {len(triplets)} triplets")

        if not triplets:
            return {
                "status": "no_paths",
                "message": "No relevant paths found in graph"
            }

        # Step 4: Evaluate sufficiency
        sufficiency = self.evaluate_sufficiency(question, triplets)

        # Step 5: Generate answer
        result = self.generate_answer(question, triplets)

        result["status"] = "success"
        result["start_entity"] = start_entity
        result["sufficiency"] = sufficiency
        result["llm_calls"] = 1 + len(triplets) * 2 + 2  # Extract + (rel + ent) * N + eval + answer

        return result

    def _parse_relation_scores(self, response: str) -> List[Tuple[str, float]]:
        """Parse relation scores from LLM response"""
        scores = []
        for line in response.strip().split("\n"):
            if "Score:" in line:
                parts = line.split("(Score:")
                if len(parts) == 2:
                    rel_name = parts[0].strip().strip("-").strip()
                    score_str = parts[1].strip().rstrip(")").strip()
                    try:
                        score = float(score_str)
                        scores.append((rel_name, score))
                    except ValueError:
                        continue
        return scores

    def _parse_entity_scores(self, response: str) -> List[Tuple[str, float]]:
        """Parse entity scores from LLM response"""
        # Same format as relations
        return self._parse_relation_scores(response)

# Singleton
tog_service = ToGService()
```

#### 3. `backend/app/services/query_router.py`

```python
"""
Query Router: Decide between GraphRAG and ToG
"""

import logging
from typing import Dict, Any
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

class QueryRouter:
    """Routes queries to appropriate processing method"""

    def classify_query_complexity(self, query: str) -> Dict[str, Any]:
        """
        Classify query to determine routing

        Returns:
            {
                "complexity": "simple" | "complex",
                "reasoning": "explanation",
                "method": "graphrag" | "tog"
            }
        """
        prompt = f"""
Classify the query complexity:

Query: "{query}"

Classification criteria:
- SIMPLE: Direct facts, single-hop, straightforward lookup
  Examples: "What is X?", "Who founded Y?"
  → Use GraphRAG (fast retrieval)

- COMPLEX: Multi-hop reasoning, requires chaining facts
  Examples: "Where was X's founder educated?", "What connects A and B?"
  → Use ToG (structured reasoning)

Output JSON:
{{
    "complexity": "simple" or "complex",
    "reasoning": "brief explanation",
    "hops_needed": 1-5
}}
"""

        response = llm_service.generate(prompt)
        classification = llm_service._parse_json_response(response)

        # Route based on complexity
        complexity = classification.get("complexity", "simple")
        method = "tog" if complexity == "complex" else "graphrag"

        classification["method"] = method

        logger.info(f"Query routed to {method}: {classification.get('reasoning')}")

        return classification

query_router = QueryRouter()
```

#### 4. Update `backend/app/api/endpoints/queries.py`

```python
@router.post("/query/auto")
def query_auto_route(
    query_request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Auto-route query to GraphRAG or ToG based on complexity

    - Simple queries → GraphRAG (fast)
    - Complex queries → ToG (accurate multi-hop)
    """
    from app.services.query_router import query_router
    from app.services.tog_service import tog_service
    from app.services.query_service import query_service

    # Classify query
    routing = query_router.classify_query_complexity(query_request.query)

    if routing["method"] == "tog":
        # Use ToG for complex reasoning
        result = tog_service.process_query(
            question=query_request.query,
            start_entity=query_request.get("entity")  # Optional
        )
    else:
        # Use GraphRAG for simple queries
        result = query_service.process_query(
            query=query_request.query,
            hop_limit=query_request.get("hop_limit", 1)
        )

    result["routing"] = routing

    # Save query to database
    # ... (existing code)

    return result
```

### Week 5: Testing & Optimization

1. ✅ Test ToG với complex queries
2. ✅ Test GraphRAG với simple queries
3. ✅ Test routing logic
4. ✅ Performance optimization (caching, parallel calls)
5. ✅ Fallback strategies

---

## Final Recommendation

### **Chiến lược đề xuất cho GraphToG**: Hybrid Approach

**Implement**:
1. **Week 1-2**: Minimal GraphRAG
   - ✅ Entity ranking (support cả ToG lẫn GraphRAG)
   - ✅ Basic token budgets (cho fallback)
   - ❌ Skip relationship prioritization (ToG tự làm)
   - ❌ Skip community weighting (không cần cho ToG)

2. **Week 3-4**: ToG Implementation
   - ✅ ToG prompts
   - ✅ ToG service (5 stages)
   - ✅ Query router
   - ✅ Graph query helpers

3. **Week 5**: Integration & Testing
   - ✅ Auto-routing endpoint
   - ✅ Fallback logic
   - ✅ Performance optimization

**Kết quả**:
- ✅ Simple queries: Fast GraphRAG retrieval (< 5s)
- ✅ Complex queries: Accurate ToG reasoning (10-30s)
- ✅ Best of both worlds
- ✅ Chỉ implement ~40% GraphRAG improvements (tiết kiệm thời gian)
- ✅ Focus effort vào ToG (unique value)

**Cost**:
- 5 tuần instead of 8 tuần (full GraphRAG)
- Tiết kiệm 3 tuần (~37%)
- Better explainability và reasoning

---

## Kết luận

**Trả lời câu hỏi ban đầu:**

> Nếu cài đặt ToG cho retrieval và sinh câu trả lời, có cần thực hiện đầy đủ GraphRAG improvements không?

**KHÔNG CẦN** implement đầy đủ tất cả GraphRAG improvements.

**Chỉ cần implement**:
- ✅ Entity ranking (hỗ trợ ToG)
- ✅ Basic token budgets (fallback)
- ✅ Graph schema improvements (quality)

**Có thể skip**:
- ❌ Relationship prioritization (ToG tự rank)
- ❌ Community weighting (ToG không dùng communities)
- ❌ Advanced context assembly (ToG query graph trực tiếp)

**Focus vào**:
- ⭐ ToG implementation (reasoning layer)
- ⭐ Query routing (phân loại complexity)
- ⭐ Hybrid approach (best of both)

Cách này **tiết kiệm thời gian** (5 tuần vs 8 tuần) và mang lại **unique value** (structured reasoning) mà pure GraphRAG không có!
