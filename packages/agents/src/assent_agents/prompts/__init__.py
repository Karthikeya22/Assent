from pathlib import Path

DIR = Path(__file__).parent


def load(name: str) -> str:
    """Prompts are versioned files (`<name>_v<N>.md`); runs record the name they used."""
    return (DIR / f"{name}.md").read_text("utf-8")
