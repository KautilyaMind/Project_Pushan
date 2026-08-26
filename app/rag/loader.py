"""Load trusted Markdown knowledge documents with traceable metadata."""

from pathlib import Path

from langchain_core.documents import Document


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KNOWLEDGE_PATH = PROJECT_ROOT / "knowledge"


def load_knowledge_documents(
    knowledge_path: str | Path = DEFAULT_KNOWLEDGE_PATH,
) -> list[Document]:
    """Load every Markdown file in a deterministic order."""
    directory = Path(knowledge_path)
    if not directory.is_dir():
        raise FileNotFoundError(f"Knowledge directory not found: {directory}")

    documents = []
    for path in sorted(directory.glob("*.md")):
        documents.append(
            Document(
                page_content=path.read_text(encoding="utf-8"),
                metadata={"source": str(path), "filename": path.name},
            )
        )
    if not documents:
        raise FileNotFoundError(f"No Markdown knowledge documents found in: {directory}")
    return documents
