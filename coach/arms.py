"""Experiment arm configuration. Defaults reproduce the deployed companion exactly (the `final` arm)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArmConfig:
    name: str = "final"
    cite: bool = True                    # append lesson, slide and page citations; keep slide labels in retrieved chunks
    mpac_and_lesson_guide: bool = True   # keep the M-PAC and LESSON REFERENCE GUIDE sections in the system prompt
    generic_retrieval: bool = False      # lesson and science retrieval from the generic collection, no metadata filters or ordering
    generic_collection: str = "exp2_generic"
    generic_top_k: int = 7


ARMS = {
    "final": ArmConfig(),
    "comp1_nocite": ArmConfig(name="comp1_nocite", cite=False),
    "comp2_noprompt": ArmConfig(name="comp2_noprompt", mpac_and_lesson_guide=False),
    "comp3_generic": ArmConfig(name="comp3_generic", cite=False, generic_retrieval=True),
}
