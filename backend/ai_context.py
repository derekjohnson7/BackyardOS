from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

ADVISOR_CONTEXT_PATH = (
    PROJECT_ROOT / "docs" / "advisor_context.md"
)


def load_advisor_context() -> str:
    """Load BackyardOS project knowledge for the AI advisor."""

    if not ADVISOR_CONTEXT_PATH.is_file():
        raise FileNotFoundError(
            f"Advisor context not found: {ADVISOR_CONTEXT_PATH}"
        )

    return ADVISOR_CONTEXT_PATH.read_text(encoding="utf-8")