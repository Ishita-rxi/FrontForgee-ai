from agents.base_agent import BaseAgent

SYSTEM_PROMPT = """You are the Planner Agent in a frontend-generation multi-agent system. \
Given a structured specification, produce a project plan as JSON:
{
  "app_name": str,
  "pages": [{"name": str, "route": str, "description": str}],
  "components": [{"name": str, "type": "layout|page-section|ui|chart|form", \
"description": str, "used_on_pages": [str]}],
  "dependencies": [str]
}
Rules:
- component "name" must be a valid PascalCase React component name.
- Keep the component count consistent with the requested complexity level.
- Always include a Navbar and Footer layout component if there is more than one page.
- "dependencies" may ONLY contain names from this exact list — nothing else, ever: \
"react-router-dom" (only if there is more than one page), "recharts" (only if a chart \
is genuinely needed), "framer-motion" (only for real animation needs), "lucide-react" \
(only if icons are needed), "clsx" (only for conditional className logic). If none of \
these are needed, return an empty list. \
NEVER include Tailwind, Vite, PostCSS, or any build-tooling package by any name — \
those are already fully configured by the project scaffold and listing them (or any \
plugin for them) will break the build.
Respond with ONLY the JSON object, nothing else."""


class PlannerAgent(BaseAgent):
    name = "Planner Agent"

    def generate_plan(self, spec: dict) -> dict:
        user_prompt = (
            f"Specification:\n"
            f"- App description: {spec['user_prompt']}\n"
            f"- Framework: {spec['framework']}\n"
            f"- Styling: {spec['styling']}\n"
            f"- Theme: {spec['theme']}\n"
            f"- Complexity: {spec['complexity']}\n"
        )
        plan = self.llm.chat_json(SYSTEM_PROMPT, user_prompt)
        plan.setdefault("app_name", "GeneratedApp")
        plan.setdefault("pages", [])
        plan.setdefault("components", [])
        plan.setdefault("dependencies", [])
        return plan
