# T4: Construct Precision (9 notes)

Theme definition: Whether the response targets the theoretically correct M-PAC construct with precise wording.

**Running total after T4: 128/153**

---

## Change 4A: Precise Construct Terminology (3 notes — vague wording)

### Technical Problem
The chatbot uses loose language for M-PAC constructs in a way that diverges from how they are described in the intervention:
- "Mental pathways" used for habit mechanism — should be "cue-behaviour link" or "cue-response connection"
- Habit tracking described as a subjective feeling — should reference automaticity as the defining marker
- Asymptotic curve described as "starts rapidly" — this oversimplifies and doesn't note individual variation

All three are prompt-level fixes: add precise terminology guidance to BASE_PROMPT so the model uses intervention-consistent language when discussing these constructs.

### Code Change

**`coach/prompts.py`** — add to the BEHAVIOR CHANGE FRAMEWORK section (~line 86), after the layer descriptions:

```
CONSTRUCT TERMINOLOGY (use exactly):
- Habit mechanism: "cue-behaviour link" or "cue-response connection" — NOT "mental pathway" or "neural pathway"
- Habit automaticity: "A habit is forming when the behaviour starts in response to the cue without needing a deliberate decision"
- Habit learning curve: "Research suggests the pattern of habit formation often follows an asymptotic curve —
  improvement tends to be faster early on and then levels off — though the timeline varies a lot by person and activity"
  Do NOT state a specific number of days as universal (e.g., "it takes 21 days" or even "18-254 days" as a rule).
- Regulatory phase: the phase that translates reflective intentions into actual behaviour through
  planning, self-monitoring, and emotion regulation — it is NOT just "overcoming barriers"
- Fatigue/tiredness: a physiological state, NOT an emotional or affective state —
  do not treat it as an emotion when discussing emotion regulation
```

### Before (QID 57 — breaking a habit)
> "When you break a habit, the mental pathways in your brain weaken over time, but they can be rebuilt with practice."

### After
> "When a habit is disrupted, the cue-behaviour link can fade — but it can be rebuilt by re-introducing the same cue consistently. Lesson 8 covers this if you'd like to explore it further."

### Before (QID 72 — is something becoming a habit?)
> "You'll know it's becoming a habit when it starts to feel natural and you don't have to think about it as much."

### After
> "A good sign that something is becoming a habit is when you find yourself starting the activity in response to your cue — almost automatically, without needing to decide to do it."

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 57 | CB | "Mental pathways" used instead of "cue-behaviour link" |
| 72 | CB | Habit tracking described as subjective feeling not automaticity |
| 75 | CB | Asymptotic curve — "starts rapidly" overstates and misses individual variation |

---

## Change 4B: Correct Construct Boundaries (2 notes — conflation)

### Technical Problem
Two cases where the chatbot conflates distinct M-PAC constructs:
1. **QID 29**: A breathing exercise response shifts from reactive regulation (emotional coping) into physiological breathing technique (specific counts, step-based breathing). The reactive regulation construct is about managing emotions to maintain activity — not about physical breathing mechanics. The chatbot introduces specific breath-count guidance not grounded in the lessons.
2. **QID 71**: Fatigue is incorrectly treated as an emotion when discussing "emotion regulation interventions having a small but meaningful effect on PA." Fatigue is a physiological state; conflating it with affective states weakens the explanation.

### Code Change

**`coach/prompts.py`** — add to the CONSTRUCT TERMINOLOGY block (from Change 4A):

```
CONSTRUCT BOUNDARIES:
- Reactive regulation (emotion regulation for PA): strategies for managing feelings
  like low mood, guilt, boredom, or dread that get in the way of activity.
  Do NOT include physiological breathing mechanics, oxygen flow, or exercise performance
  in reactive regulation explanations — those are outside the construct scope.
- Breathing exercises in this context = a calming technique for managing pre-activity
  nervousness or low motivation, not a performance technique.
```

### Before (QID 29 — breathing exercise)
> "Diaphragmatic breathing can help manage pre-activity jitters. Try inhaling for 4 counts, holding for 4, exhaling for 6. This also helps with oxygenation during uphill walking by improving your VO2 efficiency."

### After
> "Taking a slow breath before you start can be a good way to settle any nerves or resistance you feel before getting going — it's one of the strategies covered in Lesson 6 on staying motivated."

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 29 | CB | Breathing shifts from emotion regulation to physiological performance — scope drift |
| 71 | CB | Fatigue treated as an emotion in emotion regulation context |

---

## Change 4C: Completeness of M-PAC Explanations (4 notes — missing layers)

### Technical Problem
Several notes flag that M-PAC explanations omit key phases:
- QID 60/SC: M-PAC overview omits the regulatory phase entirely
- QID 66/AW: Regulatory phase described only as "overcoming barriers" — misses its role in translating intention to behaviour
- QID 30/AW: Habit explanation misses the core "consistent cue that triggers a simple automatic response" mechanism
- QID 83/AW: Regulatory phase incorrectly attributed to lessons 1-3 (it's in the second science module, covering lessons 4-6)

### Code Change

**`coach/prompts.py`** — in the BEHAVIOR CHANGE FRAMEWORK section (~line 88), update the layer descriptions:

```python
# Before (layer logic section):
"""Internal layer logic (never stated aloud):
- Layers: unclassified, initiating reflective, ongoing reflective, regulatory, reflexive."""

# After: extend with the full M-PAC structure for use when explaining the framework to users:
"""Internal layer logic (never stated aloud):
- Layers: unclassified, initiating reflective, ongoing reflective, regulatory, reflexive.

When explaining M-PAC to users (if they ask):
- Reflective phase: motivation, reasons, capability beliefs — the WHY (Lessons 1-3, first science module)
- Regulatory phase: translating intentions into action through planning, scheduling, self-monitoring,
  and emotion regulation — the HOW (Lessons 4-6, second science module)
  NOTE: regulatory is NOT just about overcoming barriers — it is the bridge between wanting to act and acting.
- Reflexive phase: habits, automatic cue-response links, and identity — the WHO YOU BECOME (Lessons 7-10, third science module)
- All three science lessons ('The Science Behind the Lessons') together cover the full M-PAC framework."""
```

### Before (QID 60 — "What is the M-PAC?")
> "The M-PAC framework has two main components: the reflective phase, which involves your reasons and motivations, and the reflexive phase, which involves habits and automatic behaviour."

### After
> "The M-PAC framework has three phases: the reflective phase (your reasons and motivations for being active), the regulatory phase (putting those intentions into action through planning and self-monitoring), and the reflexive phase (where activity becomes habitual and part of your identity). All three are covered across The Science Behind the Lessons."

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 26 | CB | Emotion regulation response vague; lacks concrete strategies from Lesson 6 |
| 30 | AW | Habit explanation missing "consistent cue triggers automatic response" mechanism |
| 60 | SC | M-PAC overview omits regulatory phase |
| 66 | AW | Regulatory phase described only as "overcoming barriers" |

---

## T4 Summary

| Change | Notes | Description |
|--------|-------|-------------|
| 4A | 3 | Precise construct terminology in BASE_PROMPT |
| 4B | 2 | Construct boundary rules (reactive regulation vs physiology; fatigue vs emotion) |
| 4C | 4 | Full M-PAC phase structure for explanations; regulatory phase definition |
| **Total** | **9** | |
