# Reviewer Note Fixes: Master Plan

Branch: `reviewer-note-fixes`
Total reviewer notes: 153 across 7 themes (T1-T7)
Goal: smooth and refine responses before participant launch. No changes to core architecture or logic.

---

## File Index

| File | Theme | Notes | Cumulative |
|------|-------|-------|------------|
| [T1-intervention-grounding.md](T1-intervention-grounding.md) | Lesson linking, terminology, citation | 63 | 63/153 |
| [T2-resource-scope.md](T2-resource-scope.md) | Resource section direction, schedule disclaimers | 30 | 93/153 |
| [T3-safety-boundary.md](T3-safety-boundary.md) | Healthcare referral, out-of-scope redirect, MH language | 26 | 119/153 |
| [T4-construct-precision.md](T4-construct-precision.md) | M-PAC construct accuracy | 9 | 128/153 |
| [T5-personalisation.md](T5-personalisation.md) | Gender, age framing, example diversity | 10 | 138/153 |
| [T6-source-traceability.md](T6-source-traceability.md) | Fabricated content, out-of-scope knowledge | 8 | 146/153 |
| [T7-style-delivery.md](T7-style-delivery.md) | Spelling, redundancy, minor enrichments | 7 | 153/153 |

**Dismissed (no change):** 1 note — QID 23/AW (T7): reviewer approved the response, nothing to fix.

---

## Key Files Changed

| File | What Changes |
|------|-------------|
| `rag/retriever.py` lines 106, 110, 139, 143 | "Science Module X, Slide Y" → "The Science Behind the Lessons, Page Y"; "Lesson X, Slide Y" → "Lesson X, Page Y" |
| `coach/agent.py` lines ~305, ~336, ~344 | "slide" → "page" in response mode instructions |
| `coach/agent.py` line ~645 | Remove "Lesson/Slide" hint from module reference instruction |
| `coach/agent.py` lines ~545-551 | Change default retrieval instruction to stop naming specific activities |
| `coach/agent.py` lines ~547-548 | Add schedule disclaimer to activity mention template |
| `coach/prompts.py` lines ~41-64 | Add healthcare referral instruction, soften out-of-scope redirect |
| `coach/prompts.py` lines ~83-86 | Add "M-PAC framework" enforcement, construct precision notes |
| `coach/prompts.py` new section | Add topic-to-lesson citation guidance |
| `coach/agent.py` `_replace_em_dash` | Extend to also enforce Canadian spelling |
