from agents.base_agent import BaseAgent
from config import (
    CLARIFICATION_TIMEOUT_NOTE,
    DEFAULT_COMPLEXITY,
    DEFAULT_FRAMEWORK,
    DEFAULT_STYLING,
    DEFAULT_THEME,
)

SYSTEM_PROMPT = """You are the Clarification Agent in a frontend-generation multi-agent \
system. Given a user's natural language app description, produce 3 to 5 targeted \
clarifying questions that resolve real ambiguity (framework preference, styling \
library, color theme, complexity/page count, any specific must-have sections). \
Do not ask about things already stated in the prompt. \
Respond ONLY as a JSON object: {"questions": [{"question": str, "options": [str,...], \
"default": str}]}. Keep each question short and each options list to 2-4 choices."""


class ClarificationAgent(BaseAgent):
    name = "Clarification Agent"

    def generate_questions(self, user_prompt: str) -> list[dict]:
        try:
            data = self.llm.chat_json(SYSTEM_PROMPT, f"App description:\n{user_prompt}")
            questions = data.get("questions", [])
            if questions:
                return questions
        except Exception:
            pass
        # Fallback so the pipeline is never blocked by an LLM hiccup.
        return self._default_questions()

    @staticmethod
    def _default_questions() -> list[dict]:
        return [
            {
                "question": "Which framework should be used?",
                "options": ["React (Vite)", "Next.js"],
                "default": DEFAULT_FRAMEWORK,
            },
            {
                "question": "Which styling approach?",
                "options": ["Tailwind CSS", "Bootstrap", "Material UI"],
                "default": DEFAULT_STYLING,
            },
            {
                "question": "Which starting color theme?",
                "options": ["Ocean Blue", "Sunset", "Forest", "Royal Violet", "Minimal Dark"],
                "default": DEFAULT_THEME,
            },
            {
                "question": "How complex should the generated app be?",
                "options": ["Minimal (2-3 components)", "Standard (5-8 components)", "Rich (9+ components)"],
                "default": DEFAULT_COMPLEXITY,
            },
        ]

    @staticmethod
    def build_spec(user_prompt: str, answers: dict) -> dict:
        return {
            "user_prompt": user_prompt,
            "framework": answers.get("Which framework should be used?", DEFAULT_FRAMEWORK),
            "styling": answers.get("Which styling approach?", DEFAULT_STYLING),
            "theme": answers.get("Which starting color theme?", DEFAULT_THEME),
            "complexity": answers.get("How complex should the generated app be?", DEFAULT_COMPLEXITY),
            "note": CLARIFICATION_TIMEOUT_NOTE,
        }
