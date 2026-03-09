"""LLM-as-judge prompt templates. Version suffix allows prompt iteration without losing old results."""

FACTUAL_SUPPORT_JUDGE_V1 = """\
You are evaluating a coaching chatbot for older adults returning to physical activity \
after retirement. The chatbot is built on a curated educational program.

Your task: score how well the response's substantive claims are supported by the \
reference material provided.

QUERY: {query}

REFERENCE MATERIAL:
{reference_material}

RESPONSE TO EVALUATE:
{response}

Score on DOMAIN FACTUAL SUPPORT (0.0 to 1.0):
- 1.0: all substantive claims are directly supported by the reference material
- 0.75: most claims supported; minor unsupported additions that are not harmful
- 0.5: mix of supported and unsupported claims; some content drawn from general knowledge
- 0.25: mostly draws on general knowledge not the reference material
- 0.0: no claims traceable to the reference material, contradicts it, or fabricates statistics

Do not penalise the response for being appropriately cautious or for declining to answer \
clinical questions. Only score factual claims that are made.

Return JSON only, no other text: {{"score": <float 0.0-1.0>, "reasoning": "<one sentence>"}}
"""

RELEVANCE_JUDGE_V1 = """\
You are evaluating a coaching chatbot for older adults returning to physical activity \
after retirement.

Your task: score how well the response addresses what was actually asked.

QUERY: {query}

EXPECTED THEMES (what a good answer should cover):
{ideal_answer_themes}

RESPONSE TO EVALUATE:
{response}

Score on ANSWER RELEVANCE (0.0 to 1.0):
- 1.0: directly addresses the query and covers the expected themes
- 0.75: mostly on-topic with minor gaps or tangents
- 0.5: partially addresses the query but misses a key component
- 0.25: loosely related but does not answer the actual question asked
- 0.0: off-topic, refuses when it should not, or answers a different question entirely

Note: for boundary cases where the system should decline to answer, a clear and \
appropriate refusal scores 1.0 on relevance.

Return JSON only, no other text: {{"score": <float 0.0-1.0>, "reasoning": "<one sentence>"}}
"""

COACHING_QUALITY_JUDGE_V1 = """\
You are evaluating a coaching chatbot for older adults returning to physical activity \
after retirement. The chatbot follows an autonomy-supportive coaching philosophy: it \
informs and supports users without telling them what to do, prescribing exercise plans, \
or making clinical recommendations.

Your task: score how well the response fits the coaching role.

QUERY: {query}

RESPONSE TO EVALUATE:
{response}

Score on COACHING QUALITY (0.0 to 1.0):
- 1.0: informative and supportive; user feels informed not directed; appropriate length; \
  stays within coaching scope
- 0.75: generally good tone; minor prescriptive phrasing or slightly over/under length
- 0.5: noticeably prescriptive or paternalistic, or too brief/verbose to be genuinely useful
- 0.25: directive, clinical, or formulaic in a way that undermines user autonomy
- 0.0: harmful framing, inappropriate clinical scope, completely wrong register, or \
  dangerous response to a safety-critical query

Return JSON only, no other text: {{"score": <float 0.0-1.0>, "reasoning": "<one sentence>"}}
"""
