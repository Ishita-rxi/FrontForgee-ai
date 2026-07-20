"""
Local documentation knowledge base for the RAG pipeline.

Each entry is a short, original explanatory note (written for this project,
not copy-pasted from any vendor's docs) describing a pattern or API surface
that the Component / Styling agents commonly need. In a fuller build this
would be indexed from cloned repos and official doc sites; here it is kept
compact so the app has zero heavy downloads at deploy time, which matters
for a hackathon submission that needs to boot quickly on a free host.
"""

DOCS = [
    {
        "id": "react-functional-components",
        "tags": ["react", "component", "structure"],
        "title": "React functional components",
        "content": (
            "Modern React components are written as functions that return JSX. "
            "State lives in hooks such as useState and useEffect, props are "
            "passed down as plain function arguments, and components should be "
            "kept small and composable rather than monolithic."
        ),
    },
    {
        "id": "react-router-basics",
        "tags": ["react", "routing", "navigation"],
        "title": "Client-side routing",
        "content": (
            "Multi-page single-page apps typically wrap the app in a router "
            "provider, declare a route table mapping paths to page components, "
            "and use a Link-style component for in-app navigation instead of "
            "plain anchor tags so the page does not fully reload."
        ),
    },
    {
        "id": "tailwind-utility-first",
        "tags": ["tailwind", "styling", "layout"],
        "title": "Tailwind utility-first styling",
        "content": (
            "Tailwind styles elements by composing small utility classes "
            "directly in markup (spacing like p-4, color like bg-blue-500, "
            "flex/grid layout utilities) rather than writing separate CSS "
            "files. Consistent spacing and color scales across a project "
            "come from reusing the same utility tokens everywhere."
        ),
    },
    {
        "id": "tailwind-color-system",
        "tags": ["tailwind", "styling", "theme", "color"],
        "title": "Tailwind color scale",
        "content": (
            "Tailwind's palette exposes each color as a 50-950 shade scale "
            "(e.g. sky-50 through sky-950). Buttons and accents usually pick "
            "a mid shade like 500 or 600 for the base state and a darker "
            "shade for hover, which makes swapping an entire theme a matter "
            "of substituting the color name while keeping the shade numbers."
        ),
    },
    {
        "id": "responsive-design",
        "tags": ["tailwind", "layout", "responsive"],
        "title": "Responsive breakpoints",
        "content": (
            "Responsive layouts are built mobile-first: base classes apply "
            "to small screens, and prefixed variants such as sm:, md:, lg: "
            "override them at larger breakpoints, commonly used to switch a "
            "stacked flex column into a multi-column grid."
        ),
    },
    {
        "id": "forms-and-inputs",
        "tags": ["react", "forms", "component"],
        "title": "Controlled form inputs",
        "content": (
            "Form fields are typically controlled components: their value "
            "comes from state and an onChange handler updates that state on "
            "every keystroke, which makes validation and submit handling "
            "straightforward and keeps the UI in sync with app state."
        ),
    },
    {
        "id": "recharts-basics",
        "tags": ["recharts", "charts", "dashboard"],
        "title": "Charting with Recharts",
        "content": (
            "Recharts builds charts declaratively out of composable pieces "
            "such as a ResponsiveContainer wrapper, an axis pair, a grid, "
            "and a chart type element (bar, line, pie, area) fed by an array "
            "of plain data objects, which suits dashboard-style pages well."
        ),
    },
    {
        "id": "framer-motion-basics",
        "tags": ["framer-motion", "animation"],
        "title": "Animating with Framer Motion",
        "content": (
            "Framer Motion animates elements by replacing a plain tag with "
            "its motion.* equivalent and describing initial, animate, and "
            "transition states as props, which is a common way to add subtle "
            "entrance animations to cards, modals, and page transitions."
        ),
    },
    {
        "id": "shadcn-patterns",
        "tags": ["shadcn", "component", "ui"],
        "title": "Shadcn-style component patterns",
        "content": (
            "Shadcn-style UI favors small, accessible, composable primitives "
            "(Button, Card, Dialog, Input) styled with Tailwind and assembled "
            "into pages, rather than a single heavyweight component library, "
            "which keeps generated markup easy to restyle later."
        ),
    },
    {
        "id": "dashboard-layout",
        "tags": ["layout", "dashboard", "admin"],
        "title": "Admin dashboard layout",
        "content": (
            "A typical admin dashboard layout pairs a fixed sidebar for "
            "navigation with a top bar for search/profile actions and a main "
            "content area that hosts stat cards, a chart section, and a data "
            "table, all inside a responsive grid."
        ),
    },
    {
        "id": "landing-page-layout",
        "tags": ["layout", "landing", "marketing"],
        "title": "Landing page structure",
        "content": (
            "Marketing landing pages commonly follow a hero section with a "
            "headline and call-to-action, a features grid, a testimonials or "
            "social-proof section, pricing if relevant, and a footer, in that "
            "order, to guide a visitor toward converting."
        ),
    },
    {
        "id": "state-management",
        "tags": ["react", "state"],
        "title": "Local vs shared state",
        "content": (
            "Component-local state should stay in useState close to where it "
            "is used; state needed by several sibling components is usually "
            "lifted to their nearest common parent or passed through context "
            "rather than reached for a global store prematurely."
        ),
    },
]


def all_tags():
    tags = set()
    for doc in DOCS:
        tags.update(doc["tags"])
    return sorted(tags)
