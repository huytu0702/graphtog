"""
Pruning methods for ToG reasoning - different approaches to score and filter relations and entities.

Supports LLM, BM25, and SentenceBERT-based pruning for optimal performance vs accuracy trade-offs.
"""

import logging
from typing import List, Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class PruningMethod(ABC):
    """Abstract base class for pruning methods."""

    @abstractmethod
    async def score_relations(
        self, question: str, relations: List[str], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Score relations based on relevance to question."""
        pass

    @abstractmethod
    async def score_entities(
        self, question: str, entities: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Score entities based on relevance to question."""
        pass


class LLMPruning(PruningMethod):
    """LLM-based pruning (highest quality, slowest)."""

    def __init__(self, llm_service):
        self.llm_service = llm_service

    async def score_relations(self, question: str, relations: List[str], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Use LLM to score relations."""
        # Import here to avoid circular imports
        from app.services.prompt import TOG_RELATION_EXTRACTION_PROMPT

        entities = context.get('entities', '')
        previous_relations = context.get('previous_relations', 'None')

        prompt = TOG_RELATION_EXTRACTION_PROMPT.format(
            question=question,
            entities=entities,
            relations=', '.join(relations),
            previous_relations=previous_relations
        )

        try:
            response = await self.llm_service.generate_text(prompt, temperature=0.4)
            scored_relations = self.llm_service._parse_json_response(response)

            if isinstance(scored_relations, dict) and 'relations' in scored_relations:
                return scored_relations['relations']
            elif isinstance(scored_relations, list):
                return scored_relations
            else:
                logger.warning("Unexpected LLM response format for relations")
                return self._fallback_relation_scoring(relations)

        except Exception as e:
            logger.error(f"LLM relation scoring failed: {e}")
            return self._fallback_relation_scoring(relations)

    async def score_entities(self, question: str, entities: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Use LLM to score entities."""
        # Import here to avoid circular imports
        from app.services.prompt import TOG_ENTITY_SCORING_PROMPT

        entities_text = "\\n".join([
            f"- {e['entity_name']}: {e.get('description', '')}"
            for e in entities
        ])

        reasoning_summary = context.get('reasoning_summary', '')
        relation = context.get('relation', 'RELATES_TO')

        prompt = TOG_ENTITY_SCORING_PROMPT.format(
            question=question,
            reasoning_summary=reasoning_summary,
            relation=relation,
            candidates=entities_text
        )

        try:
            response = await self.llm_service.generate_text(prompt, temperature=0.4)
            scored_entities = self.llm_service._parse_json_response(response)

            if isinstance(scored_entities, dict) and 'entity_scores' in scored_entities:
                scores = scored_entities['entity_scores']
            elif isinstance(scored_entities, list):
                scores = scored_entities
            else:
                logger.warning("Unexpected LLM response format for entities")
                return self._fallback_entity_scoring(entities)

            # Merge scores back into entities
            score_map = {s.get('entity', s.get('entity_name', '')): s for s in scores}

            for entity in entities:
                entity_name = entity['entity_name']
                if entity_name in score_map:
                    entity['score'] = score_map[entity_name].get('score', 0.5)
                    entity['score_reasoning'] = score_map[entity_name].get('reasoning', '')
                else:
                    entity['score'] = 0.5
                    entity['score_reasoning'] = 'Fallback scoring'

            return entities

        except Exception as e:
            logger.error(f"LLM entity scoring failed: {e}")
            return self._fallback_entity_scoring(entities)

    def _fallback_relation_scoring(self, relations: List[str]) -> List[Dict[str, Any]]:
        """Fallback scoring when LLM fails."""
        return [
            {
                "relation": rel,
                "score": 0.5,
                "reasoning": "Fallback scoring due to LLM error"
            }
            for rel in relations
        ]

    def _fallback_entity_scoring(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback scoring when LLM fails."""
        for entity in entities:
            entity['score'] = 0.5
            entity['score_reasoning'] = 'Fallback scoring due to LLM error'
        return entities


class BM25Pruning(PruningMethod):
    """BM25-based pruning (fast, keyword-based)."""

    def __init__(self):
        try:
            from rank_bm25 import BM25Okapi
            self.bm25_available = True
        except ImportError:
            logger.warning("rank_bm25 not available, BM25 pruning will use fallback")
            self.bm25_available = False

    async def score_relations(self, question: str, relations: List[str], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Score relations using BM25."""
        if not self.bm25_available:
            return self._fallback_relation_scoring(relations)

        # Tokenize question
        question_tokens = question.lower().split()

        # Tokenize relations (convert underscores to spaces for better matching)
        relation_docs = [rel.lower().replace('_', ' ').split() for rel in relations]

        try:
            from rank_bm25 import BM25Okapi
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

        except Exception as e:
            logger.error(f"BM25 relation scoring failed: {e}")
            return self._fallback_relation_scoring(relations)

    async def score_entities(self, question: str, entities: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Score entities using BM25."""
        if not self.bm25_available:
            return self._fallback_entity_scoring(entities)

        # Tokenize question
        question_tokens = question.lower().split()

        # Create documents from entity names and descriptions
        entity_docs = []
        for e in entities:
            text = f"{e['entity_name']} {e.get('description', '')}".lower()
            entity_docs.append(text.split())

        try:
            from rank_bm25 import BM25Okapi
            bm25 = BM25Okapi(entity_docs)
            scores = bm25.get_scores(question_tokens)

            # Normalize
            max_score = max(scores) if max(scores) > 0 else 1.0
            normalized_scores = [s / max_score for s in scores]

            # Add scores to entities
            for entity, score in zip(entities, normalized_scores):
                entity['score'] = float(score)
                entity['score_reasoning'] = f"BM25 keyword relevance"

            entities.sort(key=lambda x: x['score'], reverse=True)
            return entities

        except Exception as e:
            logger.error(f"BM25 entity scoring failed: {e}")
            return self._fallback_entity_scoring(entities)

    def _fallback_relation_scoring(self, relations: List[str]) -> List[Dict[str, Any]]:
        """Fallback scoring when BM25 fails."""
        return [
            {
                "relation": rel,
                "score": 0.5,
                "reasoning": "Fallback scoring - BM25 unavailable"
            }
            for rel in relations
        ]

    def _fallback_entity_scoring(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback scoring when BM25 fails."""
        for entity in entities:
            entity['score'] = 0.5
            entity['score_reasoning'] = 'Fallback scoring - BM25 unavailable'
        return entities


class SentenceBERTPruning(PruningMethod):
    """SentenceBERT-based pruning (semantic similarity, medium speed)."""

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.sbert_available = True
            logger.info(f"Loaded SentenceBERT model: {model_name}")
        except ImportError:
            logger.warning("sentence_transformers not available, SentenceBERT pruning will use fallback")
            self.sbert_available = False
        except Exception as e:
            logger.warning(f"Failed to load SentenceBERT model: {e}")
            self.sbert_available = False

    async def score_relations(self, question: str, relations: List[str], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Score relations using SentenceBERT."""
        if not self.sbert_available:
            return self._fallback_relation_scoring(relations)

        try:
            # Encode question
            question_embedding = self.model.encode(question, convert_to_tensor=True)

            # Encode relations (convert underscores to spaces)
            relation_texts = [rel.replace('_', ' ') for rel in relations]
            relation_embeddings = self.model.encode(relation_texts, convert_to_tensor=True)

            # Compute cosine similarities
            from sentence_transformers import util
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

        except Exception as e:
            logger.error(f"SentenceBERT relation scoring failed: {e}")
            return self._fallback_relation_scoring(relations)

    async def score_entities(self, question: str, entities: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Score entities using SentenceBERT."""
        if not self.sbert_available:
            return self._fallback_entity_scoring(entities)

        try:
            # Encode question
            question_embedding = self.model.encode(question, convert_to_tensor=True)

            # Encode entity descriptions
            entity_texts = [
                f"{e['entity_name']} {e.get('description', '')}"
                for e in entities
            ]
            entity_embeddings = self.model.encode(entity_texts, convert_to_tensor=True)

            # Compute similarities
            from sentence_transformers import util
            similarities = util.cos_sim(question_embedding, entity_embeddings)[0]

            # Add scores to entities
            for entity, score in zip(entities, similarities):
                entity['score'] = float(score)
                entity['score_reasoning'] = f"Semantic similarity"

            entities.sort(key=lambda x: x['score'], reverse=True)
            return entities

        except Exception as e:
            logger.error(f"SentenceBERT entity scoring failed: {e}")
            return self._fallback_entity_scoring(entities)

    def _fallback_relation_scoring(self, relations: List[str]) -> List[Dict[str, Any]]:
        """Fallback scoring when SentenceBERT fails."""
        return [
            {
                "relation": rel,
                "score": 0.5,
                "reasoning": "Fallback scoring - SentenceBERT unavailable"
            }
            for rel in relations
        ]

    def _fallback_entity_scoring(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback scoring when SentenceBERT fails."""
        for entity in entities:
            entity['score'] = 0.5
            entity['score_reasoning'] = 'Fallback scoring - SentenceBERT unavailable'
        return entities


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
