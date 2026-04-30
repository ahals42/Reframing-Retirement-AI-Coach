# T5: Personalisation (10 notes)

Theme definition: Whether examples and framing are appropriate for a 60-70-year-old recently-retired user of any gender.

**Running total after T5: 138/153**

---

## Change 5A: Gender-Neutral Resource Examples (3 notes)

### Technical Problem
The at-home resource retriever sometimes returns a resource whose title contains gendered language (e.g., "stretching for women over 50"). When this gets cited in a response, male participants receive a resource that explicitly excludes them. The issue is in how the `home_resources` response instruction handles resource naming — it tells the model to state the resource name, but doesn't filter for gendered titles.

The fix is two-part: add a prompt instruction to always describe at-home resources using gender-neutral language (paraphrase the title if needed), and ensure the at-home data set preferentially surfaces gender-neutral resources when no specific gender context exists.

### Code Change

**`coach/agent.py`** — `home_resources` response instruction (~line 322):

```python
# Add to the existing instruction:
"If a resource title contains gendered language (e.g., 'for women', 'for men'), "
"describe it in gender-neutral terms instead: e.g., 'a stretching routine for older adults' "
"rather than repeating the gendered title verbatim."
```

### Before (QID 11 — beginner stretching at home)
> "Individual Video #4: Flexibility for Women Over 50 is a gentle beginner routine you can follow at home."

### After
> "Individual Video #4 is a gentle beginner flexibility routine suitable for any older adult — you can find it in the app under Resources > What Can You Do At Home?"

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 11 | AW | Stretching video has women-specific title — male users excluded |
| 91 | AW | Same — stretching resource title gendered |
| 91 | CB | Blog mislabeled AND gender-specific example ("for women over 50") |

---

## Change 5B: Affirming Age Framing (2 notes)

### Technical Problem
Two notes flag that responses subtly frame older adults as requiring extra caution or being inherently limited. QID 10 notes that strength training is described conservatively rather than affirmingly. QID 11/HZ notes that mirroring "65" back to the user in a response anchors on the age rather than affirming capability. The Lesson 3 framing emphasizes that capability is built over time — not that it's limited by age.

### Code Change

**`coach/prompts.py`** — COACH PERSONALITY section (~line 22), strengthen existing "Assumptions" line:

```python
# Before:
"- Assumptions: the user is capable, resilient, and has handled hard things before."

# After:
"- Assumptions: the user is capable, resilient, and has handled hard things before.
   Do not frame aging as a limitation. Older adults can and do engage in full ranges
   of physical activity. Lead with affirmation ('Absolutely, older adults can...') rather
   than caution ('It's important to start gently...'). Do not echo a user's age back to
   them as a framing device (e.g., avoid 'At 65, you might want to...')."
```

### Before (QID 10 — can older adults lift heavy weights?)
> "Older adults can benefit from strength training, but it's important to start very gently and progress slowly to avoid injury."

### After
> "Older adults can absolutely strength train — the key is starting at a level that feels right for you and building from there. Lesson 3 covers how confidence and capability develop over time."

### Before (QID 11 — is 65 too old to start stretching?)
> "At 65, it's completely fine to start stretching — just listen to your body."

### After
> "It's never too late to start stretching — flexibility work benefits people at any stage of life."

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 10 | CB | Strength training framed conservatively; should affirm capability per Lesson 3 |
| 11 | HZ | Response echoes "65" back — should affirm without anchoring on age |

---

## Change 5C: Diversify Activity Examples (4 notes)

### Technical Problem
Pilot feedback and reviewer notes confirm that pickleball is overused as a default example activity in coaching responses. This is because pickleball appears prominently in the local activity dataset and the model gravitates to it. Participants who are not interested in pickleball may feel alienated. The fix is to add an explicit instruction to rotate through a variety of example activities and limit unprompted pickleball mentions.

### Code Change

**`coach/prompts.py`** — COACHING PRINCIPLES section (~line 151), add:

```
EXAMPLE ACTIVITIES:
When giving examples of physical activities, rotate through a variety:
brisk walking, cycling, swimming, yoga, tai chi, light strength work, stretching, gardening, or dancing.
Do NOT default to pickleball unless the user has mentioned it or asked about it specifically.
Pickleball is available in the app but is only one option among many.

For research study evidence (e.g., ACT), do NOT cite studies using university students
as the example population — this does not resonate with 60-70 year old retirees.
Refer to findings more generically ("research on older adults shows..." or
"studies have found...") unless the study specifically involved older adults.
```

### Before
> "A great way to stay social and active is pickleball — it's popular with retirees and beginner-friendly!"

### After
> "There are lots of ways to stay active with others — walking groups, swimming, yoga classes, or cycling clubs are all great options. You can browse what's available locally in the Resources section."

### Before (QID 80 — ACT evidence)
> "Research on ACT shows it's effective — for example, studies with university students found it improved exercise adherence."

### After
> "Research suggests ACT-based approaches can help people stay committed to healthy behaviours, including physical activity — there's growing evidence for it in health behaviour change contexts."

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 21 | HZ | Pickleball used as example in activity tracking — too repetitive |
| 22 | HZ | Pickleball used again in social monitoring example |
| 80 | AW | ACT evidence cites university students — doesn't fit 60-70yo retiree profile |
| 80 | HZ | Same — university student example doesn't fit |

---

## Change 5D: Don't Assume Skill Level (1 note)

### Technical Problem
QID 87/CB: when a user asks about pickleball drop-ins, the chatbot assumes they're a beginner and structures the entire response around beginner-friendly aspects. The user had only said they were in the Saanich area — nothing about their skill level.

### Code Change

**`coach/prompts.py`** — COACHING PRINCIPLES section, add to the autonomy support line:

```
Do not assume a user's skill level for an activity unless they tell you.
If skill level is relevant (e.g., beginner vs. experienced), ask first:
"Are you familiar with [activity], or would you be starting fresh?"
```

### Before (QID 87 — pickleball in Saanich)
> "Commonwealth Place has a beginner-friendly drop-in — it's very welcoming to people who have never played before."

### After
> "There are local pickleball options in your area — you can find them in the Resources section. Are you already familiar with the game, or would you be starting fresh?"

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 87 | CB | Assumes user is a beginner without asking |

---

## T5 Summary

| Change | Notes | Description |
|--------|-------|-------------|
| 5A | 3 | Gender-neutral at-home resource descriptions |
| 5B | 2 | Affirming capability framing; don't mirror age back |
| 5C | 4 | Diversify activity examples; limit pickleball; age-appropriate research citations |
| 5D | 1 | Ask about skill level before assuming |
| **Total** | **10** | |
