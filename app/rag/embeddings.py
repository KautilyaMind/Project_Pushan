"""Deterministic local embeddings for offline, testable retrieval."""

import hashlib
import math
import re

from langchain_core.embeddings import Embeddings


class LocalHashEmbeddings(Embeddings):
    """Map words into a fixed vector without an API key or paid call.

    This lightweight prototype keeps retrieval available offline. A production
    deployment can replace only this module with a provider embedding model.
    """

    def __init__(self, dimensions: int = 1024) -> None:
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        words = re.findall(r"[a-z0-9]+", text.lower())
        tokens = words + [f"{left}_{right}" for left, right in zip(words, words[1:])]
        for token in tokens:
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            vector[value % self.dimensions] += 1.0 if value & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def get_embedding_model() -> Embeddings:
    """Return Pushan's isolated embedding implementation."""
    return LocalHashEmbeddings()
