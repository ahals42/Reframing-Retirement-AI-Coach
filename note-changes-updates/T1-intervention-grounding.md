# T1: Intervention Grounding (63 notes)

Theme definition: Whether the chatbot links content back to the correct Reframing Retirement lesson with correct terminology.

Notes in this file cover 3 implementation changes, addressed in order below.

**Running total after T1: 63/153**

---

## Change 1A: "Slide" → "Page" Terminology (6 notes)

### Technical Problem
The `reference()` and `label()` methods in `rag/retriever.py` format all lesson citations using the word "Slide" (e.g., "Lesson 6, Slide 8: Talking yourself through it"). The intervention calls these content units "pages" or "cards," not slides. This mismatch surfaces verbatim in generated responses because the LLM echoes the citation format it receives. Additionally, the response mode instructions in `coach/agent.py` use the word "slide" when instructing the model about what to reference.

### Code Change

**`rag/retriever.py`** — 4 lines, same pattern:

```python
# line 106 — label() science branch
# Before:
return f"Science Module {module} Slide {slide}: {title}".strip()
# After:
return f"The Science Behind the Lessons, Page {slide}: {title}".strip()

# line 110 — label() lesson branch
# Before:
return f"Lesson {lesson} Slide {slide}: {title}".strip()
# After:
return f"Lesson {lesson}, Page {slide}: {title}".strip()

# line 139 — reference() science branch
# Before:
return f"Science Module {module}, Slide {slide}: {slide_title}"
# After:
return f"The Science Behind the Lessons, Page {slide}: {slide_title}"

# line 143 — reference() lesson branch
# Before:
return f"Lesson {lesson}, Slide {slide}: {slide_title}"
# After:
return f"Lesson {lesson}, Page {slide}: {slide_title}"
```

**`coach/agent.py`** — 3 response instruction strings:

```python
# lowest_mpac instruction (~line 305):
# Before: "points to at most two slides as lesson support"
# After:  "points to at most two pages as lesson support"

# emotion_education instruction (~line 336):
# Before: "references one slide as optional lesson support"
# After:  "references one page as optional lesson support"

# educational instruction (~line 344):
# Before: "references one slide as optional lesson support"
# After:  "references one page as optional lesson support"

# _build_module_reference_instruction (~line 645):
# Before: "Mention that it's in the lesson (Lesson/Slide)"
# After:  "Mention that it's in the lesson"
```

### Before
> "You can find more on self-talk in Lesson 6, Slide 8: Talking yourself through it."

### After
> "You can find more on this in Lesson 6, page 8: Talking yourself through it."

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 15 | CB | "slide" used for goal-setting reference |
| 28 | CB | "slide" used for self-talk Lesson 6 reference |
| 30 | CB | "slide" used for habit Lesson 7 reference |
| 34 | CB | "slide" used for cues reference |
| 55 | CB | "slide" used for self-talk Lesson 6 (follow-up question) |
| 78 | CB | "slide" used for hedonic motivation reference |

---

## Change 1B: Science Module Naming (24 notes)

### Technical Problem
Science lesson chunks are formatted as `"Science Module {N}, Page {slide}: {title}"` (after Change 1A). The correct name in the app for the science lessons is "The Science Behind the Lessons." This means every science citation the chatbot gives has the wrong module name. The fix is in `rag/retriever.py` `reference()` and `label()` — Change 1A above already replaces the format; this change is achieved in the same 4 lines. No additional code change beyond Change 1A.

Additionally, the phrase "the M-PAC" appears occasionally in generated responses without "framework." Add one sentence to `coach/prompts.py` BASE_PROMPT enforcing "M-PAC framework" as the correct phrasing.

### Code Change

The science module naming fix is included in Change 1A above (`rag/retriever.py` lines 106 and 139).

**`coach/prompts.py`** — M-PAC framework wording, in the BEHAVIOR CHANGE FRAMEWORK section (~line 83):

```python
# Add to the M-PAC description paragraph:
# Before: "Use the Multi-Process Action Control (M-PAC) framework..."
# After:  "Use the Multi-Process Action Control (M-PAC) framework...
#          Always refer to this as 'the M-PAC framework', never as 'the M-PAC' alone."

# Also: when explaining M-PAC to users, note that all three science lessons
# ('The Science Behind the Lessons') together cover the full M-PAC framework.
```

### Before
> "This is covered in Science Module 2, Slide 12: The regulatory phase."

> "The M-PAC has three key phases..."

### After
> "This is covered in The Science Behind the Lessons, page 12: The regulatory phase."

> "The M-PAC framework has three key phases..."

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 32 | CB | Science module incorrectly named; should be "The Science Behind the Lessons" |
| 56 | CB | Science module named incorrectly; should also reference Lesson 7 |
| 60 | AW | "The M-PAC" without "framework"; lesson name wrong |
| 60 | CB | Should reference "The Science Behind the Lessons" |
| 61 | CB | Should reference "The Science Behind the Lessons" for instrumental beliefs |
| 62 | CB | Science module named incorrectly for exercise/mortality research |
| 63 | CB | Science module named incorrectly; should also cite Lesson 3 |
| 65 | CB | Science module named incorrectly; wrong page (should be page 27) |
| 66 | CB | Should reference "The Science Behind the Lessons, Lesson 2" |
| 67 | AW | Regulatory phase should reference second science lesson |
| 67 | CB | Should reference second science module |
| 70 | CB | Science module named incorrectly for social monitoring |
| 74 | CB | Self-reported habit index — science module incorrectly named |
| 76 | AW | Affect definition — science module naming inconsistency |
| 76 | CB | Should reference science module and Lesson 6 for affect |
| 77 | CB | Science module named incorrectly; wrong page (should be page 12) |
| 79 | CB | Identity/exercise page ref off (should be pages 5 and 6) |
| 80 | CB | ACT evidence — wrong module name; should also cite Lesson 10 |
| 81 | AW | M-PAC covered across all science modules, not just one |
| 82 | CB | Perceived capability — should reference first science module |
| 83 | CB | Regulatory phase — should reference second science module |
| 84 | CB | Intention-behaviour gap — science module named incorrectly |
| 85 | CB | Affect — science module named incorrectly; should also reference Lesson 6 |
| 86 | CB | ACT research — wrong module name and page (should be page 24) |

---

## Change 1C: Lesson-to-Construct Citation Mapping (31 notes)

### Technical Problem
The most common T1 issue: the chatbot gives accurate content but fails to cite the relevant lesson. The root cause is that the `allow_module_references` flag in `_prepare_prompt()` (coach/agent.py) is only `True` for specific response modes (`lowest_mpac`, `mpac_question`, `home_resources`, `emotion_education`, `educational`, `source_request`). In `default` mode (most coaching conversations), lesson citations are only appended if the model happens to include them, which it inconsistently does.

The fix has two parts:
1. Add a topic-to-lesson mapping block to `coach/prompts.py` BASE_PROMPT so the model knows which lesson maps to which construct and proactively references it.
2. Set `allow_module_references = True` for all response modes and pass the relevant lesson reference to `_build_module_reference_instruction` — the instruction already handles capping at max_refs.

Additionally, several notes (QID 4, 26, 36/AW) flag a style issue: the chatbot says "you can learn more in Lesson X" before giving any actual content, making it feel like a redirect rather than a coaching response. The instruction should state the substance first, then point to the lesson.

### Code Change

**`coach/prompts.py`** — add a LESSON REFERENCE GUIDE section to BASE_PROMPT:

```
==================================================
LESSON REFERENCE GUIDE
==================================================
When your response touches on the following topics, always end with a natural reference
to the relevant lesson. State the substance of your answer first, then mention the lesson.
Never lead with the lesson reference before giving your answer.

- Physical activity benefits, 150 min/week guideline, why be active → Lesson 1
- Mood, cognitive, and emotional benefits of PA → Lesson 2
- Confidence, perceived capability, social enjoyment of PA → Lesson 3
- Goal setting, planning activity, intention-behaviour gap → Lesson 4
- Self-monitoring, staying on track, tracking activity → Lesson 5
- Motivation dips, emotion regulation, self-talk, reactive strategies → Lesson 6
- Habit formation, cues, cue-response links, habit timelines → Lesson 7
- Habit maintenance, disruption, getting back on track → Lesson 8
- Identity, seeing yourself as an active person → Lesson 9
- Values, staying connected to what matters, ACT → Lesson 10
- M-PAC framework theory, science behind the phases → The Science Behind the Lessons

Phrasing examples:
- "You can explore this more in Lesson 4 on goal setting."
- "Lesson 6 covers this in more detail — it's worth a look."
Do not say "Slide X" — reference the lesson or page number if known.
```

**`coach/agent.py`** — in `_prepare_prompt()`, change default mode so lesson references are permitted:

```python
# Around line 380 — add elif for default mode:
elif response_mode == "default":
    allow_module_references = True
    max_refs = 1
```

This lets the module reference instruction include one lesson reference in default mode responses, using the best-matching retrieved chunk.

### Before
> "Planning your week around activity is a great idea. One approach is to pick the same time each day — your brain starts to link the time of day with movement and it becomes easier. What time of day usually works best for you?"
> *(No lesson reference — Lesson 4 not cited)*

> "Did you know there are pages in your lessons about building habits with cues? You might want to check those out."
> *(Lesson referenced before content given, "did you know" framing)*

### After
> "Planning your week around activity is a great idea. Picking the same time each day helps your brain link that moment to movement, making it feel more automatic over time. You can explore this more in Lesson 4 on planning."

> "Habits form when a consistent cue — like your morning coffee — reliably triggers the same behaviour. Over time, that link becomes automatic. Lesson 7 goes into this in detail if you'd like to explore it further."

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 2 | CB | 150 min/week guidance — no Lesson 1 reference |
| 4 | AW | "Did you know?" framing — state fact then reference lesson |
| 5 | CB | Cognitive benefits — no Lesson 2 reference |
| 7 | CB | Mood/affective attitude — no Lesson 2 reference |
| 8 | CB | Mood benefit — no Lesson 2 reference |
| 9 | CB | Perceived capability — no Lessons 1-3 reference |
| 12 | CB | Confidence/capability — no Lesson 3 reference |
| 18 | CB | Planning/goal-setting — no Lesson 4 reference |
| 19 | CB | Self-monitoring — no Lesson 5 reference |
| 21 | CB | Social monitoring — no Lesson 5 reference |
| 22 | CB | Social monitoring (follow-up) — no Lesson 5 reference |
| 24 | CB | Distraction management — no Lesson 5 or 6 reference |
| 25 | CB | "Don't feel like it" — no Lesson 6 reference |
| 26 | AW | State strategies first, then reference lesson |
| 27 | CB | Positive self-talk — no Lesson 6 reference |
| 33 | CB | Cue-response — wrong page number for Lesson 7 |
| 35 | CB | Habit formation — no Lesson 7/8 reference; timeline stated as universal |
| 36 | AW | Habit timeline discussed in two app locations — cite both |
| 37 | CB | Breaking/recovering habits — no Lesson 8 reference |
| 38 | CB | Habit longevity — no Lesson 8 reference |
| 39 | CB | Identity — no Lesson 9 reference; follow-up too broad |
| 42 | CB | Values — wrong lesson cited (should be Lesson 10) |
| 43 | CB | Values and activity — no Lesson 10 reference |
| 50 | CB | Weight training safety — no Lesson 1 reference |
| 52 | CB | Goal reminders — no Lesson 4 reference |
| 53 | CB | Staying on track — no Lesson 5 reference |
| 54 | CB | Emotion regulation — Lesson 10 cited instead of Lesson 6 |
| 58 | CB | Identity — no Lesson 9 reference |
| 68 | CB | Intention-behaviour gap — no Lesson 4 reference |
| 73 | CB | Habit persistence — no Lesson 7/8 reference |
| 103 | CB | Goal-setting follow-up — no Lesson 4 reference |

---

## T1 Summary

| Change | Notes | Description |
|--------|-------|-------------|
| 1A | 6 | "slide" → "page" in retriever.py and agent.py instructions |
| 1B | 24 | Science module naming in retriever.py + "M-PAC framework" in prompts.py |
| 1C | 31 | Topic-to-lesson mapping in BASE_PROMPT + allow_module_references in default mode |
| **Total** | **63** | |
