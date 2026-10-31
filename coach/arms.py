"""Experiment arm configuration. Defaults reproduce the deployed companion exactly (the `final` arm)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional


@dataclass(frozen=True)
class ArmConfig:
    name: str = "final"
    # Experiment 2 switches
    cite: bool = True                    # append lesson, slide and page citations; keep slide labels in retrieved chunks
    mpac_and_lesson_guide: bool = True   # keep the M-PAC and LESSON REFERENCE GUIDE sections in the system prompt
    generic_retrieval: bool = False      # lesson and science retrieval from the generic collection, no metadata filters or ordering
    generic_collection: str = "exp2_generic"
    generic_top_k: int = 7
    # Experiment 4 switches
    safety_section: bool = True          # keep the HARD SAFETY & SCOPE BOUNDARIES prompt section
    coaching_sections: bool = True       # keep the DEFAULT RESPONSE STRUCTURE and COACHING PRINCIPLES prompt sections
    postprocess: bool = True             # response post-processing (sentence filters, caps, module sentence) and the appended mental-health referral
    master_top_k: Optional[int] = None   # override the number of lesson and science passages retrieved (deployed: 7)
    neighbor_stitching: bool = True      # append the neighbouring slide to each retrieved slide
    context_char_limit: int = 1200       # characters kept per retrieved passage in the prompt
    similarity_floor: Optional[float] = None   # drop passages scoring below this; abstain when no lesson passage survives
    query_rewrite: bool = False          # rewrite the participant's wording into a short search query before retrieval
    grounding_mode: str = "strict"       # how strictly retrieved content is used: strict, permissive or gap


_FINAL = ArmConfig()

ARMS = {
    "final": _FINAL,
    "comp1_nocite": ArmConfig(name="comp1_nocite", cite=False),
    "comp2_noprompt": ArmConfig(name="comp2_noprompt", mpac_and_lesson_guide=False),
    "comp3_generic": ArmConfig(name="comp3_generic", cite=False, generic_retrieval=True),
    # Experiment 4: each arm differs from `final` in exactly one switch
    "a1_nosafety": replace(_FINAL, name="a1_nosafety", safety_section=False),
    "a2_nocoaching": replace(_FINAL, name="a2_nocoaching", coaching_sections=False),
    "a4b_nopost": replace(_FINAL, name="a4b_nopost", postprocess=False),
    "r1_floor": replace(_FINAL, name="r1_floor", similarity_floor=0.0),      # floor value is set after calibration
    "r3_k1": replace(_FINAL, name="r3_k1", master_top_k=1),
    "r3_k3": replace(_FINAL, name="r3_k3", master_top_k=3),
    "r3_k12": replace(_FINAL, name="r3_k12", master_top_k=12),
    "r4_nostitch": replace(_FINAL, name="r4_nostitch", neighbor_stitching=False),
    "r4_long": replace(_FINAL, name="r4_long", context_char_limit=2400),
    "r2_rewrite": replace(_FINAL, name="r2_rewrite", query_rewrite=True),
    "f1_permissive": replace(_FINAL, name="f1_permissive", grounding_mode="permissive"),
    "f2_gap": replace(_FINAL, name="f2_gap", grounding_mode="gap"),
}
