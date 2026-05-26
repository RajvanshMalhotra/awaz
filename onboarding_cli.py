"""
onboarding_cli.py — Interactive CLI onboarding for Awaaz v2

Run from awaaz/ root:
    python onboarding_cli.py
"""

import sys
from core.user_profile import (
    user_profile_store,
    Personality,
<<<<<<< HEAD
    VALID_VOICE_GENDERS,
=======
>>>>>>> feature/update
)

# ─── Question bank ────────────────────────────────────────────────────────────
# Each question maps a YES or NO answer to a personality dimension + value.
# Dimensions: energy, filter, style, tone, lang_lean
#
# Big Five mapping:
#   Q1  Extraversion        → energy: chaotic(yes) / chill(no)
#   Q2  Neuroticism         → tone: sincere(yes) / sarcastic(no)  [sensitive = sincere]
#   Q3  Conscientiousness   → style: punchy(yes) / dramatic(no)   [planned = punchy/efficient]
#   Q4  Conscientiousness-  → style: dramatic(yes) / punchy(no)   [procrastinates = dramatic]
#   Q5  Openness            → lang_lean: hindi(yes) / english(no) [explores = hindi risk-taker]
#   Q6  Agreeableness-      → filter: unfiltered(yes) / clean(no) [can say no = unfiltered]
#   Q7  Assertiveness       → filter: unfiltered(yes) / clean(no) [speaks up = unfiltered]
#   Q8  Agreeableness       → tone: sincere(yes) / sarcastic(no)  [avoids conflict = sincere]
#   Q9  Openness            → energy: chaotic(yes) / chill(no)    [uncertainty excites = chaotic]
#   Q10 Self-confidence     → lang_lean: hindi(yes) / english(no) [trusts self = hindi-confident]

QUESTIONS = [
    {
        "text":     "Do you feel energized after spending time with people?",
        "yes_maps": ("energy", "chaotic"),
        "no_maps":  ("energy", "chill"),
    },
    {
        "text":     "Do criticism or negative comments stay with you for a long time?",
        "yes_maps": ("tone", "sincere"),
        "no_maps":  ("tone", "sarcastic"),
    },
    {
        "text":     "Do you make plans and usually follow them?",
        "yes_maps": ("style", "punchy"),
        "no_maps":  ("style", "dramatic"),
    },
    {
        "text":     "Do you often procrastinate on important tasks?",
        "yes_maps": ("style", "dramatic"),
        "no_maps":  ("style", "punchy"),
    },
    {
        "text":     "Do you enjoy exploring unfamiliar ideas or perspectives?",
        "yes_maps": ("lang_lean", "hindi"),
        "no_maps":  ("lang_lean", "english"),
    },
    {
        "text":     "Do you find it easy to say no to people?",
        "yes_maps": ("filter", "unfiltered"),
        "no_maps":  ("filter", "clean"),
    },
    {
        "text":     "Do you speak up when you disagree?",
        "yes_maps": ("filter", "unfiltered"),
        "no_maps":  ("filter", "clean"),
    },
    {
        "text":     "Do you avoid conflict to maintain harmony?",
        "yes_maps": ("tone", "sincere"),
        "no_maps":  ("tone", "sarcastic"),
    },
    {
        "text":     "Does uncertainty excite you more than it scares you?",
        "yes_maps": ("energy", "chaotic"),
        "no_maps":  ("energy", "chill"),
    },
    {
        "text":     "Do you trust your judgment more than popular opinion?",
        "yes_maps": ("lang_lean", "hindi"),
        "no_maps":  ("lang_lean", "english"),
    },
]

<<<<<<< HEAD
VOICE_OPTIONS = [
    ("female",     "Female — voice 1  (default female)"),
    ("female_alt", "Female — voice 2  (alternate female timbre)"),
    ("male",       "Male   — voice 1  (default male)"),
    ("male_deep",  "Male   — voice 2  (deeper male)"),
]

=======
>>>>>>> feature/update
# Human-readable labels for personality summary
PERSONALITY_LABELS = {
    "energy":    {"chaotic": "High energy / extroverted",  "chill": "Calm / introverted"},
    "filter":    {"unfiltered": "Direct / unfiltered",     "clean": "Measured / clean"},
    "style":     {"punchy": "Concise / efficient",         "dramatic": "Expressive / dramatic"},
    "tone":      {"sincere": "Warm / sincere",             "sarcastic": "Dry / sarcastic"},
    "lang_lean": {"hindi": "Hindi-leaning Hinglish",       "english": "English-leaning Hinglish"},
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def divider(label=""):
    w = 60
    if label:
        pad = (w - len(label) - 2) // 2
        print("\n" + "─" * pad + f" {label} " + "─" * pad)
    else:
        print("\n" + "─" * w)


def ask_yn(question: str) -> bool:
    while True:
        raw = input(f"  {question}\n  → (y/n): ").strip().lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  Please enter y or n.\n")


def tally(votes: dict[str, list[str]], dim: str, default: str) -> str:
    """Majority vote. Ties go to the default."""
    counts: dict[str, int] = {}
    for val in votes.get(dim, []):
        counts[val] = counts.get(val, 0) + 1
    if not counts:
        return default
    # On tie, return default
    top = max(counts.values())
    winners = [k for k, v in counts.items() if v == top]
    return default if len(winners) > 1 else winners[0]


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_onboarding():
    print("\n" + "═" * 60)
    print("  AWAAZ v2 — Onboarding")
    print("  Answer 10 quick questions so your AI voice matches")
    print("  your personality. Takes about 90 seconds.")
    print("═" * 60)

    # ── Existing profile check ──
    if user_profile_store.exists():
        divider("Existing Profile Found")
        p = user_profile_store.get()
        print(f"  Name    : {p.name}")
<<<<<<< HEAD
        print(f"  Voice   : {p.voice_gender}")
=======
>>>>>>> feature/update
        for dim, val in p.personality.to_dict().items():
            print(f"  {dim:10}: {PERSONALITY_LABELS[dim][val]}")
        redo = input("\n  Redo onboarding? (y/n): ").strip().lower()
        if redo != "y":
            print("\n  Keeping existing profile. Exiting.\n")
            return p

    # ── Name ──
    divider("Your Name")
    while True:
        name = input("  What should we call you? → ").strip()
        if name:
            break
        print("  Name can't be empty.")
    print(f"\n  Hey {name}! Let's figure out your vibe.\n")

    # ── 10 questions ──
    divider("10 Questions")
    print("  No right answers. Just go with your gut.\n")

    votes: dict[str, list[str]] = {
        "energy": [], "filter": [], "style": [], "tone": [], "lang_lean": []
    }

    for i, q in enumerate(QUESTIONS, 1):
        print(f"  [{i}/10]")
        answer = ask_yn(q["text"])
        dim, val = q["yes_maps"] if answer else q["no_maps"]
        votes[dim].append(val)
        print()

    # Tally with sensible defaults
    personality = Personality(
        energy=tally(votes, "energy",    "chill"),
        filter=tally(votes, "filter",    "clean"),
        style=tally(votes,  "style",     "punchy"),
        tone=tally(votes,   "tone",      "sincere"),
        lang_lean=tally(votes, "lang_lean", "hindi"),
    )

    # ── Personality summary ──
    divider("Your Personality Profile")
    for dim, val in personality.to_dict().items():
        label = PERSONALITY_LABELS[dim][val]
        print(f"  {dim:10} → {label}")

<<<<<<< HEAD
    # ── Voice selection ──
    divider("Voice")
    print("  Pick the TTS voice for your Awaaz:\n")
    for i, (_, label) in enumerate(VOICE_OPTIONS, 1):
        print(f"    {i}. {label}")
    while True:
        raw = input("\n  Enter number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(VOICE_OPTIONS):
            voice_gender = VOICE_OPTIONS[int(raw) - 1][0]
            break
        print("  Invalid — try again.")
    print(f"  ✓ Voice: {voice_gender}")

=======
>>>>>>> feature/update
    # ── Save ──
    divider("Saving")
    profile = user_profile_store.save(
        name=name,
<<<<<<< HEAD
        voice_gender=voice_gender,
=======
>>>>>>> feature/update
        personality=personality,
    )
    print("  ✓ Saved to user_profile.json")

    # ── Show what was generated ──
    divider("Your LLM Personality Prompt")
    print(profile.llm_system_prompt)

    divider("Your Mulberry Voice Description")
    print(f"  {profile.mulberry_description}")

    divider()
    print(f"  ✓ All done, {name}!")
    print("  Now run: python test_pipeline.py\n")

    return profile


if __name__ == "__main__":
    try:
        run_onboarding()
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Exiting.")
        sys.exit(0)