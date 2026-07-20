from agents.base_agent import BaseAgent
from rag.knowledge_base import get_context

SYSTEM_PROMPT = """You are the Component Agent in a frontend-generation multi-agent \
system. Generate a single complete React functional component as JSX, styled with \
Tailwind CSS utility classes, using hardcoded/mock data where dynamic backend data \
would otherwise be required (per project scope, there is no backend). \
Use the provided documentation context to follow correct, idiomatic patterns. \
CRITICAL: only import from 'react' and from the exact list of "available npm \
packages" given to you in the user message — never import react-router-dom, \
recharts, framer-motion, lucide-react, clsx, or anything else unless it is \
explicitly listed as available, since importing anything not installed will break \
the build. If you need something like a link, a chart, an icon, or an animation but \
the relevant package isn't available, implement a plain HTML/CSS/inline-SVG \
equivalent instead (e.g. a plain <a> tag instead of react-router's Link, a simple \
CSS bar chart instead of Recharts, an inline SVG instead of an icon package). \
Output ONLY the raw code for the file — no markdown fences, no explanation, no \
commentary before or after the code."""


class ComponentAgent(BaseAgent):
    name = "Component Agent"

    def generate_component(self, component_spec: dict, theme_colors: dict,
                             available_dependencies: list | None = None) -> tuple[str, list]:
        context, rag_hits = get_context(component_spec["type"], component_spec["description"])
        available = ", ".join(available_dependencies) if available_dependencies else "(none beyond react itself)"

        user_prompt = (
            f"Component name: {component_spec['name']}\n"
            f"Type: {component_spec['type']}\n"
            f"Description: {component_spec['description']}\n"
            f"Pages it appears on: {', '.join(component_spec.get('used_on_pages', [])) or 'N/A'}\n\n"
            f"Available npm packages (besides react/react-dom) — do not import anything "
            f"outside this list: {available}\n\n"
            f"Relevant documentation context (retrieved via RAG):\n{context}\n\n"
            f"Color palette to build the component around (use these Tailwind color "
            f"names with whatever shade numbers fit — e.g. primary-500, primary-600 "
            f"for hover):\n"
            f"- primary: {theme_colors['primary']}\n"
            f"- secondary: {theme_colors['secondary']}\n"
            f"- accent: {theme_colors['accent']}\n"
            f"- neutral (text/background/borders): {theme_colors['neutral']}\n\n"
            f"Export the component as the default export named {component_spec['name']}."
        )

        code = self.llm.chat(SYSTEM_PROMPT, user_prompt, temperature=0.5)
        code = self._strip_fences(code)
        return code, rag_hits

    @staticmethod
    def _strip_fences(code: str) -> str:
        text = code.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines)
        return text.strip()
