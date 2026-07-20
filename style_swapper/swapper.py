"""
The Style Swapper is the project's headline feature: instead of asking an
agent to regenerate a component every time a user dislikes its colors or
shape, we do a deterministic text transform on the already-generated code.
This is what makes it "one click" and "instant" rather than "wait for a
regeneration pass".

How it works
------------
1. Every generated component is tagged (in session state) with the color
   preset it was originally styled with, e.g. "Ocean Blue" ->
   {primary: blue, secondary: sky, accent: cyan, neutral: slate}.
2. To swap themes, we replace each of those four color *names* with the
   corresponding color name from the target preset, using word-boundary
   regex so shade numbers (the "-500", "-600" suffixes) are untouched and
   the contrast relationships baked into the original design survive.
3. To swap shape/elevation ("Sharp" vs "Rounded" vs "Pill"), we replace
   rounded-* and shadow-* utility classes with the target variant's values.

Both operations are pure string transforms — no network call, no LLM,
sub-millisecond, which is the whole point of the feature.
"""

import re

from style_swapper.presets import COLOR_PRESETS, STYLE_VARIANTS


def swap_color_preset(code: str, from_preset: str, to_preset: str) -> str:
    if from_preset == to_preset:
        return code
    old = COLOR_PRESETS.get(from_preset)
    new = COLOR_PRESETS.get(to_preset)
    if not old or not new:
        return code

    new_code = code
    # Replace each role's color name independently. Doing all four in one
    # pass over the *original* string (not the progressively-mutated one)
    # would risk double-swaps if two roles happen to share a color name,
    # so we build a single combined regex with named alternation instead.
    roles = ["primary", "secondary", "accent", "neutral"]
    old_to_new = {old[role]: new[role] for role in roles if old[role] != new[role]}

    if not old_to_new:
        return code

    pattern = re.compile(
        r"\b(" + "|".join(re.escape(c) for c in old_to_new.keys()) + r")(?=-\d{2,3}\b)"
    )

    def _replace(match):
        return old_to_new[match.group(1)]

    new_code = pattern.sub(_replace, new_code)
    return new_code


def swap_style_variant(code: str, to_variant: str) -> str:
    variant = STYLE_VARIANTS.get(to_variant)
    if not variant:
        return code

    new_code = code
    new_code = re.sub(r"\brounded-(none|sm|md|lg|xl|2xl|3xl|full)\b", variant["radius"], new_code)
    new_code = re.sub(r"\bshadow-(none|sm|md|lg|xl|2xl)\b", variant["shadow"], new_code)
    return new_code


def detect_preset(code: str) -> str:
    """Best-effort guess of which preset a code snippet currently uses,
    based on which primary color name appears most often. Falls back to
    Ocean Blue if nothing recognizable is found (e.g. hand-edited code)."""
    counts = {}
    for name, roles in COLOR_PRESETS.items():
        primary = roles["primary"]
        counts[name] = len(re.findall(rf"\b{re.escape(primary)}-\d{{2,3}}\b", code))
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else "Ocean Blue"
