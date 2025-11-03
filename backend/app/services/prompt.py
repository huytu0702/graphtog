"""
GraphRAG-compatible prompt templates for LLM interactions used across backend services.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

# Defaults aligned with Microsoft GraphRAG prompt requirements
DEFAULT_ENTITY_TYPES = (
    "PERSON",
    "ORGANIZATION",
    "GEO",
    "EVENT",
    "PRODUCT",
    "FACILITY",
    "WORK_OF_ART",
    "LAW",
)

DEFAULT_TUPLE_DELIMITER = "|||"
DEFAULT_RECORD_DELIMITER = "\n"
DEFAULT_COMPLETION_DELIMITER = "<COMPLETE>"

# ---------------------------------------------------------------------------
# GraphRAG prompt templates sourced from
# https://github.com/microsoft/graphrag/tree/main/graphrag/prompts/index
# ---------------------------------------------------------------------------

GRAPH_EXTRACTION_PROMPT_TEMPLATE = """
-Goal-
Given a text document that is potentially relevant to this activity and a list of entity types, identify all entities of those types from the text and all relationships among the identified entities.
 
-Steps-
1. Identify all entities. For each identified entity, extract the following information:
- entity_name: Name of the entity, capitalized
- entity_type: One of the following types: [{entity_types}]
- entity_description: Comprehensive description of the entity's attributes and activities
Format each entity as ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)
 
2. From the entities identified in step 1, identify all pairs of (source_entity, target_entity) that are *clearly related* to each other.
For each pair of related entities, extract the following information:
- source_entity: name of the source entity, as identified in step 1
- target_entity: name of the target entity, as identified in step 1
- relationship_description: explanation as to why you think the source entity and the target entity are related to each other
- relationship_strength: a numeric score indicating strength of the relationship between the source entity and target entity
 Format each relationship as ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_strength>)
 
3. Return output in English as a single list of all the entities and relationships identified in steps 1 and 2. Use **{record_delimiter}** as the list delimiter.
 
4. When finished, output {completion_delimiter}
 
######################
-Examples-
######################
Example 1:
Entity_types: ORGANIZATION,PERSON
Text:
The Verdantis's Central Institution is scheduled to meet on Monday and Thursday, with the institution planning to release its latest policy decision on Thursday at 1:30 p.m. PDT, followed by a press conference where Central Institution Chair Martin Smith will take questions. Investors expect the Market Strategy Committee to hold its benchmark interest rate steady in a range of 3.5%-3.75%.
######################
Output:
("entity"{tuple_delimiter}CENTRAL INSTITUTION{tuple_delimiter}ORGANIZATION{tuple_delimiter}The Central Institution is the Federal Reserve of Verdantis, which is setting interest rates on Monday and Thursday)
{record_delimiter}
("entity"{tuple_delimiter}MARTIN SMITH{tuple_delimiter}PERSON{tuple_delimiter}Martin Smith is the chair of the Central Institution)
{record_delimiter}
("entity"{tuple_delimiter}MARKET STRATEGY COMMITTEE{tuple_delimiter}ORGANIZATION{tuple_delimiter}The Central Institution committee makes key decisions about interest rates and the growth of Verdantis's money supply)
{record_delimiter}
("relationship"{tuple_delimiter}MARTIN SMITH{tuple_delimiter}CENTRAL INSTITUTION{tuple_delimiter}Martin Smith is the Chair of the Central Institution and will answer questions at a press conference{tuple_delimiter}9)
{completion_delimiter}

######################
Example 2:
Entity_types: ORGANIZATION
Text:
TechGlobal's (TG) stock skyrocketed in its opening day on the Global Exchange Thursday. But IPO experts warn that the semiconductor corporation's debut on the public markets isn't indicative of how other newly listed companies may perform.

TechGlobal, a formerly public company, was taken private by Vision Holdings in 2014. The well-established chip designer says it powers 85% of premium smartphones.
######################
Output:
("entity"{tuple_delimiter}TECHGLOBAL{tuple_delimiter}ORGANIZATION{tuple_delimiter}TechGlobal is a stock now listed on the Global Exchange which powers 85% of premium smartphones)
{record_delimiter}
("entity"{tuple_delimiter}VISION HOLDINGS{tuple_delimiter}ORGANIZATION{tuple_delimiter}Vision Holdings is a firm that previously owned TechGlobal)
{record_delimiter}
("relationship"{tuple_delimiter}TECHGLOBAL{tuple_delimiter}VISION HOLDINGS{tuple_delimiter}Vision Holdings formerly owned TechGlobal from 2014 until present{tuple_delimiter}5)
{completion_delimiter}

######################
Example 3:
Entity_types: ORGANIZATION,GEO,PERSON
Text:
Five Aurelians jailed for 8 years in Firuzabad and widely regarded as hostages are on their way home to Aurelia.

The swap orchestrated by Quintara was finalized when $8bn of Firuzi funds were transferred to financial institutions in Krohaara, the capital of Quintara.

The exchange initiated in Firuzabad's capital, Tiruzia, led to the four men and one woman, who are also Firuzi nationals, boarding a chartered flight to Krohaara.

They were welcomed by senior Aurelian officials and are now on their way to Aurelia's capital, Cashion.

The Aurelians include 39-year-old businessman Samuel Namara, who has been held in Tiruzia's Alhamia Prison, as well as journalist Durke Bataglani, 59, and environmentalist Meggie Tazbah, 53, who also holds Bratinas nationality.
######################
Output:
("entity"{tuple_delimiter}FIRUZABAD{tuple_delimiter}GEO{tuple_delimiter}Firuzabad held Aurelians as hostages)
{record_delimiter}
("entity"{tuple_delimiter}AURELIA{tuple_delimiter}GEO{tuple_delimiter}Country seeking to release hostages)
{record_delimiter}
("entity"{tuple_delimiter}QUINTARA{tuple_delimiter}GEO{tuple_delimiter}Country that negotiated a swap of money in exchange for hostages)
{record_delimiter}
{record_delimiter}
("entity"{tuple_delimiter}TIRUZIA{tuple_delimiter}GEO{tuple_delimiter}Capital of Firuzabad where the Aurelians were being held)
{record_delimiter}
("entity"{tuple_delimiter}KROHAARA{tuple_delimiter}GEO{tuple_delimiter}Capital city in Quintara)
{record_delimiter}
("entity"{tuple_delimiter}CASHION{tuple_delimiter}GEO{tuple_delimiter}Capital city in Aurelia)
{record_delimiter}
("entity"{tuple_delimiter}SAMUEL NAMARA{tuple_delimiter}PERSON{tuple_delimiter}Aurelian who spent time in Tiruzia's Alhamia Prison)
{record_delimiter}
("entity"{tuple_delimiter}ALHAMIA PRISON{tuple_delimiter}GEO{tuple_delimiter}Prison in Tiruzia)
{record_delimiter}
("entity"{tuple_delimiter}DURKE BATAGLANI{tuple_delimiter}PERSON{tuple_delimiter}Aurelian journalist who was held hostage)
{record_delimiter}
("entity"{tuple_delimiter}MEGGIE TAZBAH{tuple_delimiter}PERSON{tuple_delimiter}Bratinas national and environmentalist who was held hostage)
{record_delimiter}
("relationship"{tuple_delimiter}FIRUZABAD{tuple_delimiter}AURELIA{tuple_delimiter}Firuzabad negotiated a hostage exchange with Aurelia{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}QUINTARA{tuple_delimiter}AURELIA{tuple_delimiter}Quintara brokered the hostage exchange between Firuzabad and Aurelia{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}QUINTARA{tuple_delimiter}FIRUZABAD{tuple_delimiter}Quintara brokered the hostage exchange between Firuzabad and Aurelia{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}SAMUEL NAMARA{tuple_delimiter}ALHAMIA PRISON{tuple_delimiter}Samuel Namara was a prisoner at Alhamia prison{tuple_delimiter}8)
{record_delimiter}
("relationship"{tuple_delimiter}SAMUEL NAMARA{tuple_delimiter}MEGGIE TAZBAH{tuple_delimiter}Samuel Namara and Meggie Tazbah were exchanged in the same hostage release{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}SAMUEL NAMARA{tuple_delimiter}DURKE BATAGLANI{tuple_delimiter}Samuel Namara and Durke Bataglani were exchanged in the same hostage release{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}MEGGIE TAZBAH{tuple_delimiter}DURKE BATAGLANI{tuple_delimiter}Meggie Tazbah and Durke Bataglani were exchanged in the same hostage release{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}SAMUEL NAMARA{tuple_delimiter}FIRUZABAD{tuple_delimiter}Samuel Namara was a hostage in Firuzabad{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}MEGGIE TAZBAH{tuple_delimiter}FIRUZABAD{tuple_delimiter}Meggie Tazbah was a hostage in Firuzabad{tuple_delimiter}2)
{record_delimiter}
("relationship"{tuple_delimiter}DURKE BATAGLANI{tuple_delimiter}FIRUZABAD{tuple_delimiter}Durke Bataglani was a hostage in Firuzabad{tuple_delimiter}2)
{completion_delimiter}

######################
-Real Data-
######################
Entity_types: {entity_types}
Text: {input_text}
######################
Output:"""

GRAPH_EXTRACTION_CONTINUE_PROMPT = """MANY entities and relationships were missed in the last extraction. Remember to ONLY emit entities that match any of the previously extracted types. Add them below using the same format:
"""

GRAPH_EXTRACTION_LOOP_PROMPT = """It appears some entities and relationships may have still been missed. Answer Y if there are still entities or relationships that need to be added, or N if there are none. Please answer with a single letter Y or N.
"""

EXTRACT_CLAIMS_PROMPT_TEMPLATE = """
-Target activity-
You are an intelligent assistant that helps a human analyst to analyze claims against certain entities presented in a text document.

-Goal-
Given a text document that is potentially relevant to this activity, an entity specification, and a claim description, extract all entities that match the entity specification and all claims against those entities.

-Steps-
1. Extract all named entities that match the predefined entity specification. Entity specification can either be a list of entity names or a list of entity types.
2. For each entity identified in step 1, extract all claims associated with the entity. Claims need to match the specified claim description, and the entity should be the subject of the claim.
For each claim, extract the following information:
- Subject: name of the entity that is subject of the claim, capitalized. The subject entity is one that committed the action described in the claim. Subject needs to be one of the named entities identified in step 1.
- Object: name of the entity that is object of the claim, capitalized. The object entity is one that either reports/handles or is affected by the action described in the claim. If object entity is unknown, use **NONE**.
- Claim Type: overall category of the claim, capitalized. Name it in a way that can be repeated across multiple text inputs, so that similar claims share the same claim type
- Claim Status: **TRUE**, **FALSE**, or **SUSPECTED**. TRUE means the claim is confirmed, FALSE means the claim is found to be False, SUSPECTED means the claim is not verified.
- Claim Description: Detailed description explaining the reasoning behind the claim, together with all the related evidence and references.
- Claim Date: Period (start_date, end_date) when the claim was made. Both start_date and end_date should be in ISO-8601 format. If the claim was made on a single date rather than a date range, set the same date for both start_date and end_date. If date is unknown, return **NONE**.
- Claim Source Text: List of **all** quotes from the original text that are relevant to the claim.

Format each claim as (<subject_entity>{tuple_delimiter}<object_entity>{tuple_delimiter}<claim_type>{tuple_delimiter}<claim_status>{tuple_delimiter}<claim_start_date>{tuple_delimiter}<claim_end_date>{tuple_delimiter}<claim_description>{tuple_delimiter}<claim_source>)

3. Return output in English as a single list of all the claims identified in steps 1 and 2. Use **{record_delimiter}** as the list delimiter.

4. When finished, output {completion_delimiter}

-Examples-
Example 1:
Entity specification: organization
Claim description: red flags associated with an entity
Text: According to an article on 2022/01/10, Company A was fined for bid rigging while participating in multiple public tenders published by Government Agency B. The company is owned by Person C who was suspected of engaging in corruption activities in 2015.
Output:

(COMPANY A{tuple_delimiter}GOVERNMENT AGENCY B{tuple_delimiter}ANTI-COMPETITIVE PRACTICES{tuple_delimiter}TRUE{tuple_delimiter}2022-01-10T00:00:00{tuple_delimiter}2022-01-10T00:00:00{tuple_delimiter}Company A was found to engage in anti-competitive practices because it was fined for bid rigging in multiple public tenders published by Government Agency B according to an article published on 2022/01/10{tuple_delimiter}According to an article published on 2022/01/10, Company A was fined for bid rigging while participating in multiple public tenders published by Government Agency B.)
{completion_delimiter}

Example 2:
Entity specification: Company A, Person C
Claim description: red flags associated with an entity
Text: According to an article on 2022/01/10, Company A was fined for bid rigging while participating in multiple public tenders published by Government Agency B. The company is owned by Person C who was suspected of engaging in corruption activities in 2015.
Output:

(COMPANY A{tuple_delimiter}GOVERNMENT AGENCY B{tuple_delimiter}ANTI-COMPETITIVE PRACTICES{tuple_delimiter}TRUE{tuple_delimiter}2022-01-10T00:00:00{tuple_delimiter}2022-01-10T00:00:00{tuple_delimiter}Company A was found to engage in anti-competitive practices because it was fined for bid rigging in multiple public tenders published by Government Agency B according to an article published on 2022/01/10{tuple_delimiter}According to an article published on 2022/01/10, Company A was fined for bid rigging while participating in multiple public tenders published by Government Agency B.)
{record_delimiter}
(PERSON C{tuple_delimiter}NONE{tuple_delimiter}CORRUPTION{tuple_delimiter}SUSPECTED{tuple_delimiter}2015-01-01T00:00:00{tuple_delimiter}2015-12-30T00:00:00{tuple_delimiter}Person C was suspected of engaging in corruption activities in 2015{tuple_delimiter}The company is owned by Person C who was suspected of engaging in corruption activities in 2015)
{completion_delimiter}

-Real Data-
Use the following input for your answer.
Entity specification: {entity_specs}
Claim description: {claim_description}
Text: {input_text}
Output:"""

CLAIM_EXTRACTION_CONTINUE_PROMPT = """MANY entities were missed in the last extraction.  Add them below using the same format:
"""

CLAIM_EXTRACTION_LOOP_PROMPT = """It appears some entities may have still been missed. Answer Y if there are still entities that need to be added, or N if there are none. Please answer with a single letter Y or N.
"""


def build_claims_extraction_prompt(
    input_text: str,
    entity_specs: Optional[str] = None,
    claim_description: Optional[str] = None,
    tuple_delimiter: str = "<|>",
    record_delimiter: str = "##",
    completion_delimiter: str = "<|COMPLETE|>",
) -> str:
    """
    Build a GraphRAG-compliant claims extraction prompt

    Args:
        input_text: The text to extract claims from
        entity_specs: Entity specification (names or types)
        claim_description: Description of what claims to extract
        tuple_delimiter: Delimiter between tuple fields
        record_delimiter: Delimiter between records
        completion_delimiter: Completion marker

    Returns:
        Formatted prompt string
    """
    # Default entity specs and claim description
    if not entity_specs:
        entity_specs = "organization, person, event"
    if not claim_description:
        claim_description = "important assertions, facts, or statements made by or about entities"

    return EXTRACT_CLAIMS_PROMPT_TEMPLATE.format(
        entity_specs=entity_specs,
        claim_description=claim_description,
        input_text=input_text,
        tuple_delimiter=tuple_delimiter,
        record_delimiter=record_delimiter,
        completion_delimiter=completion_delimiter,
    )


COMMUNITY_REPORT_PROMPT_TEMPLATE = """
You are an AI assistant that helps a human analyst to perform general information discovery. Information discovery is the process of identifying and assessing relevant information associated with certain entities (e.g., organizations and individuals) within a network.

# Goal
Write a comprehensive report of a community, given a list of entities that belong to the community as well as their relationships and optional associated claims. The report will be used to inform decision-makers about information associated with the community and their potential impact. The content of this report includes an overview of the community's key entities, their legal compliance, technical capabilities, reputation, and noteworthy claims.

# Report Structure

The report should include the following sections:

- TITLE: community's name that represents its key entities - title should be short but specific. When possible, include representative named entities in the title.
- SUMMARY: An executive summary of the community's overall structure, how its entities are related to each other, and significant information associated with its entities.
- IMPACT SEVERITY RATING: a float score between 0-10 that represents the severity of IMPACT posed by entities within the community.  IMPACT is the scored importance of a community.
- RATING EXPLANATION: Give a single sentence explanation of the IMPACT severity rating.
- DETAILED FINDINGS: A list of 5-10 key insights about the community. Each insight should have a short summary followed by multiple paragraphs of explanatory text grounded according to the grounding rules below. Be comprehensive.

Return output as a well-formed JSON-formatted string with the following format:
    {{
        "title": <report_title>,
        "summary": <executive_summary>,
        "rating": <impact_severity_rating>,
        "rating_explanation": <rating_explanation>,
        "findings": [
            {{
                "summary":<insight_1_summary>,
                "explanation": <insight_1_explanation>
            }},
            {{
                "summary":<insight_2_summary>,
                "explanation": <insight_2_explanation>
            }}
        ]
    }}

# Grounding Rules

Points supported by data should list their data references as follows:

"This is an example sentence supported by multiple data references [Data: <dataset name> (record ids); <dataset name> (record ids)]."

Do not list more than 5 record ids in a single reference. Instead, list the top 5 most relevant record ids and add "+more" to indicate that there are more.

For example:
"Person X is the owner of Company Y and subject to many allegations of wrongdoing [Data: Reports (1), Entities (5, 7); Relationships (23); Claims (7, 2, 34, 64, 46, +more)]."

where 1, 5, 7, 23, 2, 34, 46, and 64 represent the id (not the index) of the relevant data record.

Do not include information where the supporting evidence for it is not provided.

Limit the total report length to {max_report_length} words.

# Example Input
-----------
Text:

Entities

id,entity,description
5,VERDANT OASIS PLAZA,Verdant Oasis Plaza is the location of the Unity March
6,HARMONY ASSEMBLY,Harmony Assembly is an organization that is holding a march at Verdant Oasis Plaza

Relationships

id,source,target,description
37,VERDANT OASIS PLAZA,UNITY MARCH,Verdant Oasis Plaza is the location of the Unity March
38,VERDANT OASIS PLAZA,HARMONY ASSEMBLY,Harmony Assembly is holding a march at Verdant Oasis Plaza
39,VERDANT OASIS PLAZA,UNITY MARCH,The Unity March is taking place at Verdant Oasis Plaza
40,VERDANT OASIS PLAZA,TRIBUNE SPOTLIGHT,Tribune Spotlight is reporting on the Unity march taking place at Verdant Oasis Plaza
41,VERDANT OASIS PLAZA,BAILEY ASADI,Bailey Asadi is speaking at Verdant Oasis Plaza about the march
43,HARMONY ASSEMBLY,UNITY MARCH,Harmony Assembly is organizing the Unity March

Output:
{{
    "title": "Verdant Oasis Plaza and Unity March",
    "summary": "The community revolves around the Verdant Oasis Plaza, which is the location of the Unity March. The plaza has relationships with the Harmony Assembly, Unity March, and Tribune Spotlight, all of which are associated with the march event.",
    "rating": 5.0,
    "rating_explanation": "The impact severity rating is moderate due to the potential for unrest or conflict during the Unity March.",
    "findings": [
        {{
            "summary": "Verdant Oasis Plaza as the central location",
            "explanation": "Verdant Oasis Plaza is the central entity in this community, serving as the location for the Unity March. This plaza is the common link between all other entities, suggesting its significance in the community. The plaza's association with the march could potentially lead to issues such as public disorder or conflict, depending on the nature of the march and the reactions it provokes. [Data: Entities (5), Relationships (37, 38, 39, 40, 41,+more)]"
        }},
        {{
            "summary": "Harmony Assembly's role in the community",
            "explanation": "Harmony Assembly is another key entity in this community, being the organizer of the march at Verdant Oasis Plaza. The nature of Harmony Assembly and its march could be a potential source of threat, depending on their objectives and the reactions they provoke. The relationship between Harmony Assembly and the plaza is crucial in understanding the dynamics of this community. [Data: Entities(6), Relationships (38, 43)]"
        }},
        {{
            "summary": "Unity March as a significant event",
            "explanation": "The Unity March is a significant event taking place at Verdant Oasis Plaza. This event is a key factor in the community's dynamics and could be a potential source of threat, depending on the nature of the march and the reactions it provokes. The relationship between the march and the plaza is crucial in understanding the dynamics of this community. [Data: Relationships (39)]"
        }},
        {{
            "summary": "Role of Tribune Spotlight",
            "explanation": "Tribune Spotlight is reporting on the Unity March taking place in Verdant Oasis Plaza. This suggests that the event has attracted media attention, which could amplify its impact on the community. The role of Tribune Spotlight could be significant in shaping public perception of the event and the entities involved. [Data: Relationships (40)]"
        }}
    ]
}}


# Real Data

Use the following text for your answer. Do not make anything up in your answer.

Text:
{input_text}

Output:"""

COMMUNITY_REPORT_TEXT_PROMPT_TEMPLATE = """
You are an AI assistant that helps a human analyst to perform general information discovery.
Information discovery is the process of identifying and assessing relevant information associated with certain entities (e.g., organizations and individuals) within a network.

# Goal
Write a comprehensive report of a community, given a list of entities that belong to the community as well as their relationships and optional associated claims.
The report will be used to inform decision-makers about information associated with the community and their potential impact.
The content of this report includes an overview of the community's key entities, their core attributes or capabilities, their connections, and noteworthy claims.
Retain as much time specific information as possible so your end user can build a timeline of events.

# Report Structure
The report should include the following sections:
- TITLE: community's name that represents its key entities - title should be short but specific. When possible, include representative named entities in the title. Avoid including phrases like 'eligibility assessment' or 'eligibility assessment report' in the title.
- SUMMARY: An executive summary of the community's overall structure, how its entities are related to each other, and significant program-specific or eligibility-related insights.
- IMPORTANCE RATING: A float score between 0-10 that represents the importance of entities within the community..
- RATING EXPLANATION: Give a single sentence explanation of the importance rating.
- DETAILED FINDINGS: A list of 5-10 key insights about the community. Each insight should have a short summary followed by multiple paragraphs of explanatory text grounded according to the grounding rules below. Be comprehensive.
- DATE RANGE: A range of dates (YYYY-MM-DD) with the format [START, END] which corresponds to the date range of text units and intermediate reports used to build the report.

Return output as a well-formed JSON-formatted string with the following format. Don't use any unnecessary escape sequences. The output should be a single JSON object that can be parsed by json.loads.
    {{
        "title": "<report_title>",
        "summary": "<executive_summary>",
        "rating": <importance_rating>,
        "rating_explanation": "<rating_explanation>",
        "findings": [{{"summary":"<insight_1_summary>", "explanation": "<insight_1_explanation"}}, {{"summary":"<insight_2_summary>", "explanation": "<insight_2_explanation"}}],
		"date_range": ["<date range start>", "<date range end>"],

    }}

# Grounding Rules
Points supported by data should list their data references as follows:

"This is an example sentence supported by multiple data references [Data: <dataset name> (record ids), <dataset name> (record ids)]."

Do not list more than 5 record ids in a single reference. Instead, list the top 5 most relevant record ids and add "+more" to indicate that there are more.

For example:
"Person X resolved a major issue with project Y [Data: Sources (1, 5),  Date_Range ((2001, 05, 12), (2001, 05, 14))]. He also made major updates to the database of app Y [Data: Reports (2, 4), Sources (7, 23, 2, 34, 46, +more), Date_Range ((2001, 05, 15), (2001, 05, 18))""

where 1, 2, 4, 5, 7, 23, 2, 34, and 46 represent the id (not the index) of the relevant data record.

Limit the total report length to {max_report_length} words.

# Example Input
-----------
SOURCES
id, text
1, Text: From: compliance.office@enron.com To: management.team@enron.com Cc: legal.team@enron.com, risk@enron.com Date: Wed, 12 Jul 2000 08:30:00 -0600 (CST) Subject: Quick Update on Compliance & Risk Efforts
2, Quick update on what's been cooking in Compliance and Risk Management. Risk Management is stepping up — They've been tightening up on our financial risk assessments and mitigation strategies since early this year.
3, Their efforts are key to keeping us on solid ground financially and in compliance with the latest market regulations as of mid-2000. It's crucial for our strategic planning and helps us stay ahead.
5, Legal's keeping us in check — The Legal Compliance team is on top of ensuring all our operations are up to scratch with legal standards. They're especially focused on improving our corporate governance and contract management as of the second quarter of 2000. This is critical for keeping our operations smooth and legally sound.
9, Working together — Risk Management and Legal Compliance have been syncing up better than ever since the start of Q2 2000. They're making sure our strategies are not just effective but also fully compliant. This coordination is essential for our integrated governance approach.
10, Your thoughts? — How do these updates impact your area? Got ideas on how we can do better? Give your department heads a shout.
11, Thanks for staying engaged. Let's keep pushing for better and smarter ways to work. Cheers, Jane Doe

Output:

{{
    "title": "Enron Compliance and Risk Management Overview as of July 2000",
    "summary": "This report delves into Enron's key departments focusing on compliance and risk management, illustrating how these entities interact within the organizational framework to uphold regulatory standards and manage financial risks effectively. The information is relevant to the company's operations around mid-2000.",
    "rating": 9.2,
    "rating_explanation": "The high importance rating reflects the critical roles that the Risk Management and Legal Compliance Departments play in ensuring Enron's adherence to financial and legal regulations, crucial for maintaining the company's integrity and operational stability.",
    "findings": [
        {{
            "summary": "Risk Management Operational Scope",
            "explanation": "The Risk Management Department at Enron plays a pivotal role in identifying, assessing, and mitigating financial risks. Their proactive approach, highlighted from the beginning of 2000, helps safeguard Enron against potential financial pitfalls and ensures continuous compliance with evolving market regulations. Effective risk management not only prevents financial anomalies but also supports the company's strategic decision-making processes.

[Data: Sources (2, 3), Date_Range ((2000, 01, 01), (2000, 07, 12))]"
        }},
        {{
            "summary": "Legal Compliance and Governance",
            "explanation": "The Legal Compliance Department ensures that all Enron's operations adhere to the legal standards set by regulatory bodies. Their focus on corporate governance and contract management, noted starting Q2 2000, is crucial in maintaining Enron's reputation and operational legality, especially in managing complex contracts and corporate agreements. Their efforts underscore the commitment to upholding high legal standards and ethical practices.

[Data: Source (5), Date_Range ((2000, 04, 01), (2000, 07, 12))]"
        }},
        {{
            "summary": "Interdepartmental Collaboration for Compliance",
            "explanation": "Collaboration between the Risk Management and Legal Compliance Departments, established in Q2 2000, ensures that risk mitigation strategies are legally sound and that compliance measures consider financial risks. This synergy is vital for holistic governance and has been instrumental in integrating risk management with legal compliance strategies at Enron. Enhanced interdepartmental cooperation during this period plays a crucial role in aligning the company's strategies with regulatory requirements.

[Data: Sources (9), Date_Range ((2000, 04, 01), (2000, 07, 12))]"
        }}
    ],
    "date_range": ["2000-01-01", "2000-07-12"]
}}


# Real Data

Use the following text for your answer. Do not make anything up in your answer.

Text:
{input_text}

Output:
"""

SUMMARIZE_DESCRIPTIONS_PROMPT_TEMPLATE = """
You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
Given one or more entities, and a list of descriptions, all related to the same entity or group of entities.
Please concatenate all of these into a single, comprehensive description. Make sure to include information collected from all the descriptions.
If the provided descriptions are contradictory, please resolve the contradictions and provide a single, coherent summary.
Make sure it is written in third person, and include the entity names so we have the full context.
Limit the final description length to {max_length} words.

#######
-Data-
Entities: {entity_name}
Description List: {description_list}
#######
Output:
"""

# ---------------------------------------------------------------------------
# Few-shot examples retained for bespoke advanced extraction flows
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _format_entity_types(entity_types: Optional[Sequence[str]]) -> str:
    """Join entity type list into GraphRAG-friendly comma-separated string."""
    types = entity_types or DEFAULT_ENTITY_TYPES
    return ",".join(t.strip().upper() for t in types)


def _append_relationship_focus(prompt: str, entity_names: Optional[Iterable[str]]) -> str:
    """
    Modify the prompt to ONLY extract relationships (not entities) for the provided entity names.
    This is used when we already have entities and only need relationships between them.
    """
    if not entity_names:
        return prompt
    names = ", ".join(sorted({name.strip() for name in entity_names if name.strip()}))
    if not names:
        return prompt

    # Extract tuple_delimiter from the original prompt (it's in the format instructions)
    # Default to ||| if not found
    tuple_delim = "|||"
    if "{tuple_delimiter}" in prompt or "|||" in prompt:
        tuple_delim = "|||"

    # Add strong instruction to ONLY return relationships
    relationship_only_instruction = f"""

IMPORTANT MODIFICATION:
You have already identified the following entities in a previous step:
{names}

NOW, your task is to ONLY extract relationships between these entities. DO NOT output entity records again.

For each pair of related entities from the list above, output ONLY relationship records in this format:
("relationship"{tuple_delim}<source_entity>{tuple_delim}<target_entity>{tuple_delim}<relationship_description>{tuple_delim}<relationship_strength>)

Skip step 1 (entity identification) completely. Focus ONLY on step 2 (relationship identification) using the entities listed above.

Return ONLY relationship tuples. Do not include any entity tuples in your response.
"""

    return prompt + relationship_only_instruction


# ---------------------------------------------------------------------------
# Graph extraction prompts
# ---------------------------------------------------------------------------


def build_graph_extraction_prompt(
    text: str,
    entity_types: Optional[Sequence[str]] = None,
    tuple_delimiter: str = DEFAULT_TUPLE_DELIMITER,
    record_delimiter: str = DEFAULT_RECORD_DELIMITER,
    completion_delimiter: str = DEFAULT_COMPLETION_DELIMITER,
) -> str:
    """Create a GraphRAG-compliant prompt for joint entity and relationship extraction."""
    return GRAPH_EXTRACTION_PROMPT_TEMPLATE.format(
        entity_types=_format_entity_types(entity_types),
        tuple_delimiter=tuple_delimiter,
        record_delimiter=record_delimiter,
        completion_delimiter=completion_delimiter,
        input_text=text,
    )


def build_graph_extraction_continue_prompt() -> str:
    """Prompt used when looping GraphRAG graph extraction."""
    return GRAPH_EXTRACTION_CONTINUE_PROMPT


def build_graph_extraction_loop_prompt() -> str:
    """Prompt that asks whether to continue a GraphRAG extraction loop."""
    return GRAPH_EXTRACTION_LOOP_PROMPT


def build_claim_extraction_prompt(
    text: str,
    entity_specs: str,
    claim_description: str,
    tuple_delimiter: str = DEFAULT_TUPLE_DELIMITER,
    record_delimiter: str = DEFAULT_RECORD_DELIMITER,
    completion_delimiter: str = DEFAULT_COMPLETION_DELIMITER,
) -> str:
    """Create a GraphRAG-compliant prompt for claim extraction."""
    return EXTRACT_CLAIMS_PROMPT_TEMPLATE.format(
        entity_specs=entity_specs,
        claim_description=claim_description,
        tuple_delimiter=tuple_delimiter,
        record_delimiter=record_delimiter,
        completion_delimiter=completion_delimiter,
        input_text=text,
    )


def build_claim_extraction_continue_prompt() -> str:
    """Prompt used when additional claim extraction passes are required."""
    return CLAIM_EXTRACTION_CONTINUE_PROMPT


def build_claim_extraction_loop_prompt() -> str:
    """Prompt used to determine if further claim extraction loops are needed."""
    return CLAIM_EXTRACTION_LOOP_PROMPT


# ---------------------------------------------------------------------------
# Community reporting prompts
# ---------------------------------------------------------------------------


def build_community_report_prompt(
    input_text: str,
    max_report_length: int = 450,
) -> str:
    """Create a GraphRAG community report prompt from structured Entities/Relationships text."""
    return COMMUNITY_REPORT_PROMPT_TEMPLATE.format(
        input_text=input_text,
        max_report_length=max_report_length,
    )


def build_community_report_from_text_units_prompt(
    input_text: str,
    max_report_length: int = 450,
) -> str:
    """Create a GraphRAG community report prompt when working from aggregated text units."""
    return COMMUNITY_REPORT_TEXT_PROMPT_TEMPLATE.format(
        input_text=input_text,
        max_report_length=max_report_length,
    )


def build_description_summarization_prompt(
    entity_name: str,
    description_list: str,
    max_length: int = 120,
) -> str:
    """Create a GraphRAG summarization prompt for entity description aggregation."""
    return SUMMARIZE_DESCRIPTIONS_PROMPT_TEMPLATE.format(
        entity_name=entity_name,
        description_list=description_list,
        max_length=max_length,
    )


def build_community_summary_prompt(
    entity_names: List[str],
    relationships_desc: str,
    sample_text: str,
    max_report_length: int = 450,
) -> str:
    """Create a community summary prompt compatible with GraphRAG community reports."""
    sample_lines = sample_text.splitlines()
    entity_entries = []
    for idx, name in enumerate(entity_names or []):
        description = sample_lines[idx] if idx < len(sample_lines) else ""
        entity_entries.append(f"{idx + 1},{name},{description}")

    if not entity_entries:
        entity_entries.append("1,UNKNOWN,No description available")

    relationships_section = relationships_desc.strip() or "No relationships provided"
    supporting_text = sample_text.strip() or "No supporting text provided"

    entity_entries_text = "\n".join(entity_entries)

    input_text = f"""Entities

id,entity,description
{entity_entries_text}

Relationships

{relationships_section}

Supporting Text
{supporting_text}"""

    return build_community_report_prompt(input_text=input_text, max_report_length=max_report_length)


def build_graph_community_summary_prompt(context: str, max_report_length: int = 450) -> str:
    """Create prompt for summarizing communities with structured JSON output."""
    return build_community_report_prompt(input_text=context, max_report_length=max_report_length)


def build_detailed_community_summary_prompt(
    community_level: int,
    member_count: int,
    members_text: str,
    relationships_text: str,
    max_report_length: int = 450,
) -> str:
    """Create prompt used by the community summarization service for GraphRAG summaries."""
    members_section = members_text.strip() or "No members provided"
    relationships_section = relationships_text.strip() or "No relationships provided"

    input_text = f"""Community Level: {community_level}
Member Count: {member_count}

Members:
{members_section}

Relationships:
{relationships_section}"""

    return build_community_report_from_text_units_prompt(
        input_text=input_text,
        max_report_length=max_report_length,
    )


# ---------------------------------------------------------------------------
# Legacy helper prompts kept for advanced extraction utilities
# ---------------------------------------------------------------------------


def build_few_shot_entity_prompt(
    text: str,
    entity_types: str,
    few_shot_example: Optional[str] = None,
) -> str:
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
        "perspective_1": {{
            "answer": "...",
            "confidence": "low|medium|high"
        }},
        "perspective_2": {{
            "answer": "...",
            "confidence": "low|medium|high"
        }}
    }},
    "synthesis": "..."
}}

Only return valid JSON.
"""


def build_entity_extraction_prompt(
    text: str,
    entity_types: Optional[Sequence[str]] = None,
    tuple_delimiter: str = DEFAULT_TUPLE_DELIMITER,
    record_delimiter: str = DEFAULT_RECORD_DELIMITER,
    completion_delimiter: str = DEFAULT_COMPLETION_DELIMITER,
) -> str:
    """Backwards-compatible wrapper that now emits the GraphRAG extract graph prompt."""
    return build_graph_extraction_prompt(
        text=text,
        entity_types=entity_types,
        tuple_delimiter=tuple_delimiter,
        record_delimiter=record_delimiter,
        completion_delimiter=completion_delimiter,
    )


def build_relationship_extraction_prompt(
    text: str,
    entity_names: Optional[Iterable[str]] = None,
    entity_types: Optional[Sequence[str]] = None,
    tuple_delimiter: str = DEFAULT_TUPLE_DELIMITER,
    record_delimiter: str = DEFAULT_RECORD_DELIMITER,
    completion_delimiter: str = DEFAULT_COMPLETION_DELIMITER,
) -> str:
    """Create prompt for relationship extraction (GraphRAG style with optional focus)."""
    prompt = build_graph_extraction_prompt(
        text=text,
        entity_types=entity_types,
        tuple_delimiter=tuple_delimiter,
        record_delimiter=record_delimiter,
        completion_delimiter=completion_delimiter,
    )
    return _append_relationship_focus(prompt, entity_names)


# ---------------------------------------------------------------------------#
# Tree of Graphs (ToG) reasoning prompts
# ---------------------------------------------------------------------------#

TOG_TOPIC_ENTITY_EXTRACTION_PROMPT = """
Given a question and a list of available entities from a knowledge graph, identify which entities are mentioned or relevant to answering the question.

Question: {question}

Available Entities: {available_entities}

Return a JSON object with the following format:
{{
    "topic_entities": ["Entity1", "Entity2", "Entity3"]
}}

Instructions:
- Extract entities that are directly mentioned in the question
- Include entities that are likely needed to answer the question
- Return at most 5 entities
- If no relevant entities are found, return an empty array
- Only return valid JSON, no additional text
"""

TOG_RELATION_EXTRACTION_PROMPT = """
Given a question, current entities being explored, and available relation types, select the most relevant relations to explore next.

Question: {question}
Current Entities: {entities}
Available Relations: {relations}
Previously Explored Relations: {previous_relations}

Return a JSON object with the following format:
{{
    "relations": [
        {{
            "relation_type": "relation_name",
            "score": 0.8,
            "reasoning": "Why this relation is relevant to the question"
        }},
        {{
            "relation_type": "another_relation",
            "score": 0.6,
            "reasoning": "Why this relation is also relevant"
        }}
    ]
}}

Instructions:
- Score relations from 0.0 to 1.0 based on relevance to the question
- Higher scores indicate more promising relations to explore
- Avoid relations that have already been explored
- Select at most 3 relations
- Only return valid JSON, no additional text
"""

TOG_ENTITY_SCORING_PROMPT = """
Given a question, a relation type, a source entity, and candidate target entities, score each candidate entity based on how well it helps answer the question through this relation.

Question: {question}
Relation Type: {relation_type}
Source Entity: {source_entity}
Candidate Entities: {candidate_entities}

Return a JSON object with the following format:
{{
    "entity_scores": [
        {{
            "entity_name": "Entity1",
            "score": 0.9,
            "reasoning": "Why this entity is highly relevant"
        }},
        {{
            "entity_name": "Entity2",
            "score": 0.4,
            "reasoning": "Why this entity is less relevant"
        }}
    ]
}}

Instructions:
- Score each candidate entity from 0.0 to 1.0
- Higher scores indicate entities that better help answer the question
- Consider the semantic fit between the source entity, relation, and candidate
- Only return valid JSON, no additional text
"""

TOG_SUFFICIENCY_CHECK_PROMPT = """
Given a question and the relations that have been explored so far, determine if there is sufficient information to answer the question.

Question: {question}
Explored Relations: {relations}

Return a JSON object with the following format:
{{
    "sufficient": true,
    "confidence_score": 0.85,
    "reasoning": "Explanation of why the information is or isn't sufficient"
}}

Instructions:
- Set "sufficient" to true if the explored relations provide enough information to answer the question
- Set "sufficient" to false if more exploration is needed
- Provide a confidence score from 0.0 to 1.0
- Give clear reasoning for your decision
- Only return valid JSON, no additional text
"""

TOG_FINAL_ANSWER_PROMPT = """
Given a question and the reasoning path that was explored through the knowledge graph, generate a final answer.

Question: {question}
Reasoning Path: {reasoning_path}

Return a JSON object with the following format:
{{
    "answer": "Your comprehensive answer here",
    "confidence": 0.8,
    "reasoning_summary": "Brief summary of how the answer was derived"
}}

Instructions:
- Provide a clear, comprehensive answer to the question
- Base your answer on the reasoning path provided
- Include confidence score from 0.0 to 1.0
- If the reasoning path doesn't provide enough information, say so clearly
- Only return valid JSON, no additional text
"""


# ---------------------------------------------------------------------------#
# Query processing and answer generation prompts
# ---------------------------------------------------------------------------#

def build_query_classification_prompt(query: str) -> str:
    """
    Build prompt for classifying query type (local, global, hybrid, ToG).

    Args:
        query: User's question

    Returns:
        Formatted prompt for query classification
    """
    return f"""
Classify the following query to determine the best retrieval strategy.

Query: {query}

Classify this query as one of:
- "local": Question about specific entities, people, or events (narrow scope)
- "global": Question requiring broad understanding across the entire dataset (wide scope)
- "hybrid": Question that needs both specific details and broad context
- "tog": Complex multi-hop question requiring reasoning through relationships

Return ONLY a JSON object in this exact format:
{{
    "query_type": "local|global|hybrid|tog",
    "reasoning": "Brief explanation of why this classification was chosen",
    "confidence": 0.85
}}

Examples:
- "What did John say about the project?" -> local
- "What are the main themes across all documents?" -> global
- "How does John's opinion relate to the overall company strategy?" -> hybrid
- "What connects Person A to Event B through Organization C?" -> tog
"""


def build_contextual_answer_prompt(query: str, context: str, citations: bool = True) -> str:
    """
    Build prompt for generating contextual answer from retrieved information.

    Args:
        query: User's question
        context: Retrieved context information
        citations: Whether to include citation markers

    Returns:
        Formatted prompt for answer generation
    """
    citation_instruction = """
Include citation markers [1], [2], etc. to reference specific sources in your answer.
""" if citations else ""

    return f"""
Answer the following question based on the provided context.

Question: {query}

Context:
{context}

{citation_instruction}

Instructions:
- Provide a clear, comprehensive answer based strictly on the context provided
- Do not make up or infer information not present in the context
- If the context doesn't contain enough information to answer fully, say so
- Be concise but complete
- Use a professional, informative tone

Answer:"""


def build_map_reduce_batch_summary_prompt(query: str, communities_info: str) -> str:
    """
    Build prompt for summarizing batch of community reports (map phase).

    Args:
        query: User's question
        communities_info: Information about community reports to summarize

    Returns:
        Formatted prompt for batch summarization
    """
    return f"""
Summarize the following community information to help answer the user's question.

Question: {query}

Community Information:
{communities_info}

Instructions:
- Extract key information relevant to the question
- Preserve important details, entities, and relationships
- Create a concise summary that captures the essential insights
- Maintain factual accuracy - do not infer beyond what's stated
- Keep the summary under 500 words

Summary:"""


def build_map_reduce_final_synthesis_prompt(query: str, summaries: str) -> str:
    """
    Build prompt for final synthesis of batch summaries (reduce phase).

    Args:
        query: User's question
        summaries: Combined batch summaries to synthesize

    Returns:
        Formatted prompt for final answer synthesis
    """
    return f"""
Synthesize the following summaries to provide a comprehensive answer to the user's question.

Question: {query}

Summaries:
{summaries}

Instructions:
- Combine insights from all summaries into a coherent, comprehensive answer
- Resolve any contradictions or inconsistencies
- Highlight key themes, patterns, and insights
- Structure the answer logically with clear sections if needed
- Ensure the answer directly addresses the user's question
- Be thorough but avoid unnecessary repetition

Final Answer:"""
