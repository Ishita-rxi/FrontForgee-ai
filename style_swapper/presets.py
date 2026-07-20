"""
Preset definitions for the one-click Style Swapper.

The core idea: a Tailwind-styled component's *color identity* is almost
entirely expressed through a handful of utility-class prefixes
(bg-, text-, border-, from-, via-, to-, ring-) combined with a color name
and a shade number. If we know which color name a component is currently
built around, we can swap every occurrence of that color name for a new
one with a single regex pass — instantly, deterministically, and without
sending anything back to the LLM. That is what makes this "instant"
rather than "regenerate and wait".
"""

# Each preset maps a semantic role to a Tailwind color name.
# Shade numbers are preserved from the original class, only the color
# name is swapped, which keeps contrast/hover relationships intact.
COLOR_PRESETS = {
    "Ocean Blue": {"primary": "blue", "secondary": "sky", "accent": "cyan", "neutral": "slate"},
    "Sunset": {"primary": "orange", "secondary": "rose", "accent": "amber", "neutral": "stone"},
    "Forest": {"primary": "emerald", "secondary": "green", "accent": "lime", "neutral": "stone"},
    "Royal Violet": {"primary": "violet", "secondary": "purple", "accent": "fuchsia", "neutral": "zinc"},
    "Minimal Dark": {"primary": "zinc", "secondary": "neutral", "accent": "gray", "neutral": "slate"},
    "Corporate": {"primary": "indigo", "secondary": "blue", "accent": "sky", "neutral": "gray"},
    "Candy Pop": {"primary": "pink", "secondary": "fuchsia", "accent": "yellow", "neutral": "gray"},
    "Crimson": {"primary": "red", "secondary": "rose", "accent": "orange", "neutral": "stone"},
}

# Style variants beyond color: shape and elevation language.
STYLE_VARIANTS = {
    "Rounded": {"radius": "rounded-2xl", "shadow": "shadow-lg"},
    "Sharp": {"radius": "rounded-none", "shadow": "shadow-sm"},
    "Soft": {"radius": "rounded-xl", "shadow": "shadow-md"},
    "Pill": {"radius": "rounded-full", "shadow": "shadow-lg"},
}

ALL_TAILWIND_COLOR_NAMES = [
    "slate", "gray", "zinc", "neutral", "stone",
    "red", "orange", "amber", "yellow", "lime", "green", "emerald", "teal",
    "cyan", "sky", "blue", "indigo", "violet", "purple", "fuchsia", "pink", "rose",
]

DEFAULT_PRESET = "Ocean Blue"
DEFAULT_VARIANT = "Soft"
