# T7: Style & Delivery (7 notes)

Theme definition: Surface-level language choices: spelling, tone, disclaimer suggestions, affirmations.

**Running total after T7: 153/153 (1 dismissed)**

---

## Dismissed: QID 23/AW — No Change Needed

Reviewer AW wrote "I like this" about QID 23 (the response to "what can I do when I'm not in the mood to be active?"). This is a positive note — the response is working as intended. No code change required.

---

## Change 7A: Canadian Spelling Enforcement (2 notes)

### Technical Problem
QID 72/AW: The word "behavior" appears with American spelling in a response instead of the Canadian "behaviour." QID 25/SC (T6): "favourite" also flagged.

The existing `_replace_em_dash()` method in `coach/agent.py` only replaces em dashes. Extending it (or adding a parallel post-processing step) to also enforce Canadian spelling would catch these systematically. Alternatively, adding an explicit instruction to the BASE_PROMPT is simpler since the LLM can apply it during generation.

### Code Change

**`coach/prompts.py`** — OUTPUT RULES section (~line 159), add:

```
- Use Canadian English spelling throughout: behaviour (not behavior), favourite (not favorite),
  colour (not color), honour (not honor), centre (not center), recognise (not recognize).
```

**`coach/agent.py`** — optionally extend `_replace_em_dash()` to `_postprocess_text()` that also does a dict-based string replace for common American spellings:

```python
@staticmethod
def _replace_em_dash(text: str) -> str:
    text = text.replace("—", "-")
    # Canadian spelling corrections
    replacements = {
        "behavior": "behaviour",
        "behaviors": "behaviours",
        "favorite": "favourite",
        "favorites": "favourites",
        "color": "colour",
        "colors": "colours",
        "honor": "honour",
        "honors": "honours",
        "center": "centre",
        "centers": "centres",
        "recognize": "recognise",
        "recognizes": "recognises",
    }
    for american, canadian in replacements.items():
        text = text.replace(american, canadian)
        text = text.replace(american.capitalize(), canadian.capitalize())
    return text
```

### Before
> "Building a consistent behavior pattern takes time — what matters is returning to it after a lapse."

### After
> "Building a consistent behaviour pattern takes time — what matters is returning to it after a lapse."

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 72 | AW | "behavior" used instead of "behaviour" |
| 25 | SC | "favourite" Canadian spelling (primary issue in T6, spelling aspect here) |

---

## Change 7B: Don't Re-Define Acronyms Mid-Conversation (1 note)

### Technical Problem
QID 44/AW: When a user asks a follow-up about ACT (Acceptance and Commitment Therapy), the chatbot defines and expands the acronym a second time in the same conversation, even though it was already defined earlier in that session. This is redundant and makes the response feel scripted.

### Code Change

**`coach/prompts.py`** — OUTPUT RULES section (~line 159), add:

```
- Define and expand acronyms only on first use within a conversation session.
  Do not re-define or re-explain a term the user has already been introduced to in this session.
  If an acronym has been used in a previous turn, use it directly without re-expanding it.
```

### Before (second turn after ACT was already introduced)
> "ACT, which stands for Acceptance and Commitment Therapy, is a psychological approach that helps people..."

### After
> "ACT helps people act in line with their values even when difficult thoughts or feelings get in the way..."

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 44 | AW | ACT defined and expanded twice in the same conversation |

---

## Change 7C: Minor Enrichments (2 notes — suggested additions)

### Technical Problem
Two notes suggest small additions to existing responses that would improve accuracy or relatability:
- QID 2/HZ: When citing the 150 min/week guideline, no concrete example of what "moderate intensity" looks like is given. The reviewer suggests adding 1-2 examples.
- QID 7/HZ: When comparing outdoor vs. indoor walking, no weather acknowledgment is made. The reviewer suggests adding "if the weather cooperates."

These are small additions to what the model should include, addressable via prompt.

### Code Change

**`coach/prompts.py`** — LESSON REFERENCE GUIDE section (added in T1 Change 1C), append:

```
Additional content guidance:
- When citing the 150 min/week guideline, give 1-2 concrete examples of what moderate intensity
  looks like: "like brisk walking or easy cycling."
- When discussing outdoor activity benefits, acknowledge weather as a real factor:
  "on days when the weather cooperates" or "when it's nice out."
```

### Before (QID 2 — 150 min/week)
> "The general guideline is 150 minutes of moderate activity per week."

### After
> "The general guideline is 150 minutes of moderate activity per week — things like brisk walking or easy cycling count. Lesson 1 goes into this in more detail."

### Before (QID 7 — outdoor vs. indoor walking)
> "Walking outside tends to provide more mood benefits than walking indoors."

### After
> "Walking outside, when the weather cooperates, tends to provide more mood benefits than staying indoors — the change of scenery and fresh air both play a role."

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 2 | HZ | 150 min/week guideline — no examples of moderate intensity PA |
| 7 | HZ | Outdoor vs. indoor walking — no weather acknowledgment |

---

## Change 7D: Misspelled Technical Terms (1 note — edge case)

### Technical Problem
QID 75/AW: "What if the user spells 'asymptotic' wrong?" The chatbot would likely fail to recognise a misspelling like "asymetric curve" or "asymtotic" and wouldn't retrieve the relevant content.

This is a keyword matching / query router issue. The query router in `rag/router.py` detects science keywords by exact match or regex. Adding common misspellings of "asymptotic" to the keyword list ensures the right content is retrieved.

This is a low-risk, minor addition — the asymptotic curve is a specific concept that only appears in one science module.

### Code Change

**`rag/router.py`** — wherever science/educational keywords are defined, add misspelling variants:

```python
# Find the list of science detection keywords (e.g., "asymptotic")
# Add variants:
"asymtotic", "asymetric", "asymptopic", "assymptotic"
# These map to the same science module retrieval as "asymptotic curve"
```

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 75 | AW | Misspelled "asymptotic" may not retrieve correct content |

---

## Change 7E: Schedule Disclaimer (1 note)

QID 88/AW: Schedule disclaimer for activity meeting details — this is covered in T2 Change 2B. No additional action needed here; noted for tracking purposes.

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 88 | AW | Disclaimer about verifying schedule before attending — addressed in T2 |

---

## T7 Summary

| Change | Notes | Description |
|--------|-------|-------------|
| Dismissed | 1 | QID 23/AW — positive approval, no change |
| 7A | 2 | Canadian spelling enforcement in prompt and post-processing |
| 7B | 1 | No acronym re-definition mid-conversation |
| 7C | 2 | Concrete PA examples with 150 min/week; weather qualifier for outdoor activity |
| 7D | 1 | Add misspelling variants for "asymptotic" to science keyword list |
| 7E | 1 | Schedule disclaimer — addressed in T2 |
| **Total** | **7** | |

---

## All 153 Notes: Final Status

| Theme | Notes | Status |
|-------|-------|--------|
| T1 | 63 | All addressed (3 changes) |
| T2 | 30 | All addressed (3 changes) |
| T3 | 26 | All addressed (3 changes) |
| T4 | 9 | All addressed (3 changes) |
| T5 | 10 | All addressed (4 changes) |
| T6 | 8 | All addressed (2 changes) |
| T7 | 7 | 6 addressed, 1 dismissed (positive note) |
| **Total** | **153** | **152 addressed, 1 dismissed** |
