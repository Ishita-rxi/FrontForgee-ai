from agents.base_agent import BaseAgent


class ArchitectAgent(BaseAgent):
    """
    Unlike the other agents, folder/file layout for a React project is
    fairly mechanical once a plan exists, so this agent is deterministic
    rather than LLM-driven — faster, cheaper, and 100% consistent, which
    matters for the Reviewer Agent that checks structure later.
    """

    name = "UI Architect Agent"

    def generate_structure(self, plan: dict) -> dict:
        files = {
            "src/main.jsx": "entry",
            "src/App.jsx": "root",
            "src/index.css": "global-styles",
        }
        for page in plan.get("pages", []):
            slug = page["name"].replace(" ", "")
            files[f"src/pages/{slug}.jsx"] = "page"
        for comp in plan.get("components", []):
            files[f"src/components/{comp['name']}.jsx"] = "component"

        files["package.json"] = "manifest"
        files["index.html"] = "html-shell"
        files["vite.config.js"] = "build-config"
        files["tailwind.config.js"] = "style-config"
        files["postcss.config.js"] = "style-config"
        files["README.md"] = "docs"

        return {
            "layout": files,
            "folders": sorted({f.rsplit("/", 1)[0] for f in files if "/" in f}),
        }
