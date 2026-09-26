"""
Central configuration for FrontForge AI.
Keeping every tunable in one place makes it trivial to swap models
or defaults when moving from local dev to a deployed instance.
"""

import os
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))

# Groq (primary cloud provider) configuration
GROQ_MODEL = os.getenv("FRONTFORGE_MODEL", "llama-3.3-70b-versatile")
GROQ_FALLBACK_MODEL = os.getenv("FRONTFORGE_FALLBACK_MODEL", "openai/gpt-oss-20b")

# Gemini (optional cloud provider) configuration
GEMINI_MODEL = os.getenv("FRONTFORGE_GEMINI_MODEL", "gemini-flash-latest")
GEMINI_FALLBACK_MODEL = os.getenv("FRONTFORGE_GEMINI_FALLBACK_MODEL", "gemini-2.5-flash")

DEFAULT_TEMPERATURE = 0.4
MAX_TOKENS = 4096

# Agent pipeline (order matters — this is the sequential pipeline)
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

# Defaults used when the user skips the human-in-the-loop clarification step
DEFAULT_FRAMEWORK = "React (Vite)"
DEFAULT_STYLING = "Tailwind CSS"
DEFAULT_THEME = "Ocean Blue"
DEFAULT_COMPLEXITY = "Standard (5-8 components)"

CLARIFICATION_TIMEOUT_NOTE = (
    "If no answer is given, sensible defaults are assumed automatically so "
    "generation is never blocked indefinitely."
)
