"""
Centralized prompt templates for LLM interactions used across backend services.
"""

from typing import List, Optional

# Few-shot examples used for advanced extraction
FEW_SHOT_EXAMPLES = {
    "entity": """
Examples of entity extraction:
1. Text: "Apple Inc. was founded by Steve Jobs in 1976."
   Output: [{"name": "Apple Inc.", "type": "ORGANIZATION", "context": "Founded company"}, 
            {"name": "Steve Jobs", "type": "PERSON", "context": "Founder"}]

2. Text: "The Python programming language was created by Guido van Rossum."
   Output: [{"name": "Python", "type": "PRODUCT", "context": "Programming language"},
            {"name": "Guido van Rossum", "type": "PERSON", "context": "Creator"}]
""",
    "relationship": """
Examples of relationship extraction:
1. Text: "Microsoft acquired LinkedIn for $26.2 billion in 2016."
   Output: [{"source": "Microsoft", "target": "LinkedIn", "type": "ACQUIRED", "description": "Microsoft acquired LinkedIn for $26.2 billion"}]

2. Text: "OpenAI developed GPT-3, an advanced language model."
   Output: [{"source": "OpenAI", "target": "GPT-3", "type": "DEVELOPED", "description": "OpenAI developed GPT-3"}]
""",
}


def build_few_shot_entity_prompt(text: str, entity_types: str, few_shot_example: Optional[str] = None) -> str:
    """Create prompt for few-shot entity extraction."""
    example = few_shot_example or FEW_SHOT_EXAMPLES["entity"]
    return f"""{example}

Now extract entities from the following text. Only extract the specified entity types: {entity_types}

Text: "{text}"

Return a JSON array with entities in this format:
[{{"name": "...", "type": "...", "context": "..."}}]

Only return valid JSON, no additional text.
"""


def build_coreference_prompt(text: str) -> str:
    """Create prompt for coreference resolution."""
    return f"""Identify and resolve coreferences (pronouns, aliases, etc.) in the following text.
For each pronoun or reference, identify which entity it refers to.

Text: "{text}"

Return a JSON object with coreference resolutions:
{{
    "coreferences": [
        {{
            "mention": "...",
            "referent": "...",
            "type": "pronoun|alias|abbreviation"
        }}
    ],
    "entities": ["..."] // list of main entities
}}

Only return valid JSON.
"""


def build_attribute_extraction_prompt(entity_name: str, text: str) -> str:
    """Create prompt for extracting entity attributes."""
    return f"""Extract all attributes, properties, and characteristics of the entity "{entity_name}" from the following text:

Text: "{text}"

Return JSON in this format:
{{
    "entity": "{entity_name}",
    "attributes": {{
        "description": "...",
        "properties": ["..."],
        "relationships": ["..."],
        "roles": ["..."],
        "characteristics": ["..."]
    }}
}}

Only return valid JSON.
"""


def build_event_extraction_prompt(text: str) -> str:
    """Create prompt for extracting events and temporal data."""
    return f"""Extract all events, actions, and temporal information from the following text:

Text: "{text}"

Return a JSON object:
{{
    "events": [
        {{
            "event": "...",
            "participants": ["..."],
            "date": "...",
            "location": "...",
            "description": "...",
            "importance": "high|medium|low"
        }}
    ]
}}

Only return valid JSON.
"""


def build_multi_perspective_prompt(query: str, context: str, perspectives: List[str]) -> str:
    """Create prompt for generating multi-perspective answers."""
    perspectives_text = ", ".join(perspectives)
    return f"""Generate answers to the following query from different perspectives:

Query: "{query}"

Context: "{context}"

Perspectives to consider: {perspectives_text}

Return a JSON object:
{{
    "query": "{query}",
    "perspectives": {{
        "technical": {{"answer": "...", "confidence": 0.0-1.0}},
        "business": {{"answer": "...", "confidence": 0.0-1.0}},
        "social": {{"answer": "...", "confidence": 0.0-1.0}},
        "ethical": {{"answer": "...", "confidence": 0.0-1.0}}
    }},
    "synthesis": "..."
}}

Only return valid JSON.
"""


def build_entity_extraction_prompt(text: str) -> str:
    """Create prompt for base entity extraction."""
    return f"""Extract entities from the following text. For each entity, provide:
- name: The entity name
- type: One of PERSON, ORGANIZATION, LOCATION, CONCEPT, EVENT, PRODUCT, OTHER
- description: 1-2 sentence description
- confidence: 0.0-1.0 confidence score

Return as JSON array:
[{{"name": "...", "type": "...", "description": "...", "confidence": ...}}, ...]

TEXT:
{text}

JSON:"""


def build_relationship_extraction_prompt(text: str, entity_names: Optional[List[str]] = None) -> str:
    """Create prompt for relationship extraction."""
    entities_text = ", ".join(entity_names) if entity_names else ""
    entities_line = (
        f"Relationships should be between entities from this list: {entities_text}\n\n"
        if entities_text
        else ""
    )
    return (
        "Extract relationships between entities in the text.\n"
        f"{entities_line}"
        "For each relationship, provide:\n"
        "- source: Source entity name\n"
        "- target: Target entity name\n"
        "- type: One of RELATED_TO, MENTIONS, CAUSES, PRECEDES, OPPOSES, SUPPORTS, CONTAINS, PART_OF\n"
        "- description: 1-2 sentence description\n"
        "- confidence: 0.0-1.0 confidence score\n\n"
        "Return as JSON array:\n"
        '[{"source": "...", "target": "...", "type": "...", "description": "...", "confidence": ...}, ...]\n\n'
        "TEXT:\n"
        f"{text}\n\n"
        "JSON:"
    )


def build_query_classification_prompt(query: str) -> str:
    """Create prompt for classifying query type."""
    return f"""Classify this query type. Return JSON with:
- type: One of FACTUAL, ANALYTICAL, EXPLORATORY, COMPARISON
- reasoning: Brief explanation
- key_entities: List of likely key entities to search for
- suggested_depth: Number from 1-3 (1=local/simple, 2=community, 3=global/complex)

QUERY: {query}

JSON:"""


def build_contextual_answer_prompt(query: str, context: str, citations: Optional[List[str]] = None) -> str:
    """Create prompt for contextual answer generation."""
    citations_text = (
        "\n\nCitations:\n" + "\n".join([f"- {citation}" for citation in citations]) if citations else ""
    )
    return f"""Answer the following question based on the provided context.
Be concise and accurate. If the context doesn't contain enough information, say so.

QUESTION: {query}

CONTEXT:
{context}{citations_text}

ANSWER:"""


def build_community_summary_prompt(entity_names: List[str], relationships_desc: str, sample_text: str) -> str:
    """Create prompt for summarizing a community of entities."""
    entities_text = ", ".join(entity_names)
    return f"""Create a concise summary (2-3 sentences) of this community of related entities.

ENTITIES: {entities_text}

RELATIONSHIPS:
{relationships_desc}

SAMPLE TEXT:
{sample_text}

SUMMARY:"""


def build_graph_community_summary_prompt(context: str) -> str:
    """Create prompt for summarizing communities with structured JSON output."""
    return f"""Based on the following community of entities and their relationships, generate a concise summary:

{context}

Provide:
1. A brief summary (2-3 sentences) of what this community represents
2. Key themes (list 3-5 main themes)
3. Main focus area (one line)

Format your response as JSON:
{{
    "summary": "...",
    "themes": ["theme1", "theme2", "..."],
    "focus_area": "..."
}}
"""


def build_detailed_community_summary_prompt(
    community_level: int, member_count: int, members_text: str, relationships_text: str
) -> str:
    """Create prompt used by the community summarization service for GraphRAG summaries."""
    return f"""Generate a comprehensive summary of this community in 2-3 sentences:

Community Level: {community_level}
Member Count: {member_count}

Key Members:
{members_text}

Key Relationships:
{relationships_text}

Provide:
1. A brief summary of what this community represents
2. Main themes or topics (3-5 themes)
3. Significance/importance (high/medium/low)

Format as JSON:
{{
    "summary": "...",
    "themes": ["...", "..."],
    "significance": "high|medium|low"
}}
"""
