import re

from agents.base_agent import BaseAgent

SYSTEM_PROMPT = """You are the Reviewer Agent in a frontend-generation multi-agent \
system. You receive a list of generated React component files (name + code) and a \
list of static-check issues already found by a linter pass. Write a concise review \
covering: overall consistency across components, any correctness or logic concerns \
you can spot, and whether the code looks production-reasonable for a hackathon demo. \
Be specific and reference file names. Keep it under 200 words. Respond with plain text, \
not JSON."""


class ReviewerAgent(BaseAgent):
    name = "Reviewer Agent"

    ENTRY_FILES = {"src/main.jsx", "src/main.tsx"}

    def static_checks(self, files: dict) -> list:
        """Cheap, deterministic checks that don't need an LLM call at all —
        these run on every file and catch the most common generation
        failure modes (missing export, unbalanced JSX tags, stray fences)."""
        issues = []
        for path, code in files.items():
            if not path.endswith((".jsx", ".tsx")):
                continue
            # Entry files (main.jsx) only ever call ReactDOM.render — they
            # are never imported by anything else, so they legitimately
            # have no default export. Flagging them was a false positive.
            if path not in self.ENTRY_FILES and "export default" not in code:
                issues.append(f"{path}: missing a default export.")
            if code.count("{") != code.count("}"):
                issues.append(f"{path}: unbalanced curly braces.")
            if "```" in code:
                issues.append(f"{path}: leftover markdown code fence in output.")
            if re.search(r"<[A-Za-z]+[^>]*[^/]>\s*$", code.strip()) is False and "<" not in code:
                issues.append(f"{path}: no JSX markup detected.")
        return issues

    def review(self, files: dict, static_issues: list) -> str:
        component_files = {k: v for k, v in files.items() if k.endswith((".jsx", ".tsx"))}
        summary = "\n\n".join(
            f"--- {name} ---\n{code[:800]}" for name, code in component_files.items()
        )
        issues_text = "\n".join(f"- {i}" for i in static_issues) or "None found."

        user_prompt = (
            f"Static-check issues:\n{issues_text}\n\n"
            f"Generated files (truncated for review):\n{summary}"
        )
        try:
            return self.llm.chat(SYSTEM_PROMPT, user_prompt, temperature=0.3)
        except Exception as exc:  # noqa: BLE001
            return (
                "LLM review unavailable (" + str(exc) + "). "
                "Static checks only:\n" + issues_text
            )
