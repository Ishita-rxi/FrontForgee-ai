"""
Central configuration for FrontForge AI.
Keeping every tunable in one place makes it trivial to swap models
or defaults when moving from local dev to a deployed instance.
"""

import os

# ---------------------------------------------------------------------------
# LLM provider
# ---------------------------------------------------------------------------
# The capstone brief requires local, open-source inference with zero cloud
# dependency, so Ollama is the default provider. Groq remains available
# behind the same LLMClient interface — set LLM_PROVIDER=groq (e.g. for a
# publicly deployed instance, since a deployed server can't reach Ollama
# running on someone's own machine) without touching any calling code.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").strip().lower()

# ---------------------------------------------------------------------------
# Ollama (local inference) configuration
# ---------------------------------------------------------------------------
# Any of the brief's recommended models work here — swap via env var:
# `ollama pull llama3.2` (default), or qwen2.5:7b, gemma2:9b, phi3, etc.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
# CPU-only inference on a full pipeline (several components per app) can
# genuinely take a while per call — generous default so a slow machine
# doesn't get treated as "broken".
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))

# ---------------------------------------------------------------------------
# Groq (optional cloud fallback) configuration
# ---------------------------------------------------------------------------
GROQ_MODEL = os.getenv("FRONTFORGE_MODEL", "llama-3.3-70b-versatile")
GROQ_FALLBACK_MODEL = os.getenv("FRONTFORGE_FALLBACK_MODEL", "llama-3.1-8b-instant")

DEFAULT_TEMPERATURE = 0.4
MAX_TOKENS = 4096

# ---------------------------------------------------------------------------
# Agent pipeline (order matters — this is the sequential pipeline)
# ---------------------------------------------------------------------------
AGENT_PIPELINE = [
    "clarification",
    "planner",
    "architect",
    "component",
    "styling",
    "package",
    "reviewer",
]

AGENT_LABELS = {
    "clarification": "Clarification Agent",
    "planner": "Planner Agent",
    "architect": "UI Architect Agent",
    "component": "Component Agent",
    "styling": "Styling Agent",
    "package": "Package Manager Agent",
    "reviewer": "Reviewer Agent",
}

# ---------------------------------------------------------------------------
# Defaults used when the user skips the human-in-the-loop clarification step
# ---------------------------------------------------------------------------
DEFAULT_FRAMEWORK = "React (Vite)"
DEFAULT_STYLING = "Tailwind CSS"
DEFAULT_THEME = "Ocean Blue"
DEFAULT_COMPLEXITY = "Standard (5-8 components)"

CLARIFICATION_TIMEOUT_NOTE = (
    "If no answer is given, sensible defaults are assumed automatically so "
    "generation is never blocked indefinitely."
)
