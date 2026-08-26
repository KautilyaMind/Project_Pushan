"""Build and load Pushan's persistent Chroma knowledge index."""

import argparse
from pathlib import Path
import shutil

from langchain_chroma import Chroma

from .chunking import chunk_documents
from .embeddings import get_embedding_model
from .loader import DEFAULT_KNOWLEDGE_PATH, PROJECT_ROOT, load_knowledge_documents


DEFAULT_VECTOR_STORE_PATH = PROJECT_ROOT / "artifacts" / "vector_store"
COLLECTION_NAME = "pushan_agriculture_v07"


def build_vector_store(
    knowledge_path: str | Path = DEFAULT_KNOWLEDGE_PATH,
    persist_path: str | Path = DEFAULT_VECTOR_STORE_PATH,
) -> tuple[Chroma, int, int]:
    """Replace the persisted index with the current knowledge corpus."""
    documents = load_knowledge_documents(knowledge_path)
    chunks = chunk_documents(documents)
    destination = Path(persist_path)
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    store = Chroma.from_documents(
        chunks,
        get_embedding_model(),
        collection_name=COLLECTION_NAME,
        persist_directory=str(destination),
    )
    return store, len(documents), len(chunks)


def load_vector_store(
    persist_path: str | Path = DEFAULT_VECTOR_STORE_PATH,
) -> Chroma:
    """Open an existing index; never silently rebuild it during a question."""
    path = Path(persist_path)
    if not path.is_dir() or not any(path.iterdir()):
        raise FileNotFoundError(
            "Pushan knowledge index is unavailable. "
            "Run 'python -m app.rag.vector_store' first."
        )
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embedding_model(),
        persist_directory=str(path),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Index Pushan knowledge documents")
    parser.add_argument("--knowledge-path", default=str(DEFAULT_KNOWLEDGE_PATH))
    parser.add_argument("--persist-path", default=str(DEFAULT_VECTOR_STORE_PATH))
    arguments = parser.parse_args()
    _, document_count, chunk_count = build_vector_store(
        arguments.knowledge_path, arguments.persist_path
    )
    print(f"Loaded {document_count} documents")
    print(f"Created {chunk_count} chunks")
    print(f"Vector store created successfully at {arguments.persist_path}")


if __name__ == "__main__":
    main()
