"""Build the knowledge index and persist reproducibility metadata."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from app.config import settings
from .loader import DEFAULT_KNOWLEDGE_PATH
from .vector_store import build_vector_store


def index_knowledge(knowledge_path: str | Path = DEFAULT_KNOWLEDGE_PATH,
                    persist_path: str | Path = settings.vector_store_path) -> dict:
    _, documents, chunks = build_vector_store(knowledge_path, persist_path)
    metadata = {
        "documents_indexed": documents,
        "chunks_indexed": chunks,
        "indexed_at": datetime.now(timezone.utc).isoformat(),
        "embedding_model": settings.embedding_model,
    }
    destination = Path(persist_path)
    (destination / "index_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Index Pushan Markdown and PDF knowledge")
    parser.add_argument("--knowledge-path", default=str(DEFAULT_KNOWLEDGE_PATH))
    parser.add_argument("--persist-path", default=str(settings.vector_store_path))
    arguments = parser.parse_args()
    result = index_knowledge(arguments.knowledge_path, arguments.persist_path)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
