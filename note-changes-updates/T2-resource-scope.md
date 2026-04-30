# T2: Resource Scope Drift (30 notes)

Theme definition: Whether the chatbot names specific local resources/times instead of directing to the Resources section.

**Running total after T2: 93/153**

---

## Change 2A: Stop Naming Specific Local Programs (15 notes)

### Technical Problem
The default retrieval instruction in `coach/agent.py` `_build_retrieval_instruction()` (~line 547) actively tells the model to name specific activities:

> "If the retrieved context includes local activities, mention at least one concrete option by name (with location or schedule) before any reflective coaching."

This is the direct cause of responses like "Silver Threads has a Qigong class on Tuesdays..." The intention is that users should browse local options in the app's Resources section ("What is going on in your area?"), not have the chatbot pre-select one for them. The fix removes the "by name" instruction and replaces it with a direction to the Resources section. The chatbot can still acknowledge that local options exist, but should not name or describe specific programs.

Additionally, several notes flag that the chatbot directs users to external websites (Meetup, bike shop websites, Saanich rec centre website) rather than the in-app Resources section. A line in BASE_PROMPT should prohibit this.

### Code Change

**`coach/agent.py`** — `_build_retrieval_instruction()` default return (~line 545):

```python
# Before:
return (
    "You have access to retrieved slides/activities below. When relevant, ground your answer in them. "
    "Respond in a conversational tone using a maximum of three sentences total; no bullet lists or numbered lists. "
    "If the retrieved context includes local activities, mention at least one concrete option by name (with location or schedule) before any reflective coaching. "
    "When mentioning a local activity, tell the user they can find local activities in the app under Resources > What is going on in your area?. "
    "If the content is not helpful, briefly say so before proceeding without it."
)

# After:
return (
    "You have access to retrieved slides/activities below. When relevant, ground your answer in them. "
    "Respond in a conversational tone using a maximum of three sentences total; no bullet lists or numbered lists. "
    "If the retrieved context includes local activities, do NOT name specific programs, venues, or schedules. "
    "Instead, let the user know that local options exist and direct them to the Resources section of the app: "
    "'You can browse local activities in the app under Resources > What is going on in your area?'. "
    "If the content is not helpful, briefly say so before proceeding without it."
)
```

**`coach/prompts.py`** — add to HARD SAFETY & SCOPE BOUNDARIES (~line 48):

```
- Do not name specific local programs, venues, classes, or external websites when suggesting activity options.
  Always direct to the in-app Resources section ("What is going on in your area?" or "What Can You Do At Home?").
```

### Before
> "There's a great Qigong class at Silver Threads on Tuesday and Thursday mornings — it's beginner-friendly and free."

> "You could check Meetup.com or your local bike shop for cycling groups near you."

### After
> "There are local group options available near you. You can browse what's on in your area in the Resources section of the app under 'What is going on in your area?'"

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 9 | SC | Should link to resource section rather than specific pools |
| 11 | CB | Selects gender-specific at-home video rather than directing to section |
| 13 | CB | Names Silver Threads specifically instead of Resources section |
| 14 | CB | Specific activity (Qigong at Silver Threads) named instead of Resources |
| 41 | CB | External platforms (Meetup, bike shops) cited instead of Resources |
| 47 | CB | Specific pickleball location (Oaklands Park) given instead of Resources |
| 51 | CB | Specific local programs and schedules instead of Resources section |
| 64 | CB | "Build Better Bones" class named instead of directing to Resources |
| 88 | CB | "Free Easy Walks" named with specific meeting details instead of Resources |
| 89 | CB | Specific classes and venues named instead of Resources section |
| 90 | HZ | At-home resources referenced without establishing location in app |
| 91 | HZ | Same — at-home resources referenced without Resources section context |
| 92 | CB | Specific videos prescribed rather than directing to at-home section |
| 18 | AW | Random neighbourhood suggested without asking user's preferred area first |
| 90 | CB | At-home exercise categories mislabeled; described as written content not videos |

---

## Change 2B: Schedule Disclaimer (12 notes)

### Technical Problem
Even after Change 2A, if the chatbot does cite a specific activity (e.g., in a direct follow-up like "what time does that class run?"), it presents schedule information as current fact. Activity data is static in the database and schedules change. Multiple reviewers asked for a disclaimer telling users to verify before going.

### Code Change

**`coach/agent.py`** — `_build_retrieval_instruction()` — add disclaimer to the activity mention template line:

```python
# Add to the activity-related retrieval instruction text (the line that mentions Resources section):
"If you do mention any specific schedule detail from the retrieved data, always add: "
"'Please check the Resources section or contact the centre directly to confirm current times, as schedules may change.'"
```

**`coach/prompts.py`** — add the same as a general rule near the scope section:

```
When discussing specific local activity schedules or times, always note:
"Please check the Resources section or contact the venue to confirm current times, as schedules may change."
```

### Before
> "The drop-in pickleball sessions at Commonwealth Place run Mondays, Wednesdays, and Fridays from 9-11am."

### After
> "The Resources section has details on local pickleball options in your area. If you do find a session that works, it's worth calling ahead or checking the centre's website to confirm current times, as schedules can change."

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 13 | SC | Specific days/times provided that may change |
| 14 | SC | Specific days provided that may change |
| 47 | SC | Specific schedule for pickleball that may change |
| 51 | AW | Schedule information without disclaimer |
| 51 | HZ | Times provided without verification disclaimer |
| 51 | SC | Days/times may change over time |
| 87 | AW | Pickleball schedule presented without disclaimer |
| 87 | HZ | Same — asks to add "please check website/call to confirm" |
| 88 | SC | Specific day (Monday) for walking club that may change |
| 89 | AW | Class days without confirmation disclaimer |
| 89 | SC | Specific days for strength training that may change |
| 88 | HZ | Asks for website disclaimer on walking club details |

---

## Change 2C: At-Home Resource Labels (3 notes)

### Technical Problem
The chatbot mislabels the at-home resource categories (e.g., calling video #2 something it isn't, calling the blog section a name users don't see in the app). The "Blog section" label used internally does not match what users see in the app. The at-home resource response instruction in `_build_retrieval_instruction()` for `home_resources` mode already templates the correct section names ("Individual Video", "Video Playlist", "Blog") — the issue is that the model still sometimes invents its own labels.

### Code Change

**`coach/agent.py`** — `home_resources` response instruction (~line 320):

```python
# Add a stricter instruction about not inventing category names:
# Before: (no explicit prohibition on inventing labels)
# After: add to existing home_resources instruction:
"Never invent your own category names or labels. Use exactly: 'Individual Video', 'Video Playlist', or 'Blog' "
"as they appear in the Resources section of the app."
```

Also: in the same instruction, reinforce that the section is found under "Resources > What Can You Do At Home?" so users know where to navigate.

### Before
> "In the fitness section, number 3 is a great beginner workout. There's also a blog on stretching for women over 50 in the wellness section."

### After
> "In the individual video section, number 3 is a chair-based exercise video. You can find it in the app under Resources > What Can You Do At Home?"

### Notes Addressed
| QID | Reviewer | Issue |
|-----|----------|-------|
| 90 | AW | "Blog section" label not recognizable to users |
| 90 | CB | Exercise categories mislabeled; described as written not video |
| 91 | CB | Blog mislabeled (#4); gender-specific example ("for women over 50") |

---

## T2 Summary

| Change | Notes | Description |
|--------|-------|-------------|
| 2A | 15 | Remove "name by name" instruction from retrieval; prohibit external websites |
| 2B | 12 | Add schedule disclaimer to all activity mention templates |
| 2C | 3 | Fix at-home resource category labelling |
| **Total** | **30** | |
