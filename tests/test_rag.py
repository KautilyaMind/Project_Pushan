"""Offline tests for Pushan V0.7 loading, indexing, retrieval, and grounding."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from chromadb.api.client import SharedSystemClient
from langchain_core.messages import AIMessage

from app.main_api import create_app
from app.rag.chunking import chunk_documents
from app.rag.loader import DEFAULT_KNOWLEDGE_PATH, load_knowledge_documents
from app.rag.qa_service import (
    LLMNotConfiguredError,
    _response_text,
    answer_question,
    get_llm,
)
from app.rag.retriever import retrieve_context
from app.rag.vector_store import build_vector_store, load_vector_store


class FakeGroundedLLM:
    def invoke(self, messages):
        text = "\n".join(message.content for message in messages)
        self.last_prompt = text
        return AIMessage(content="Check the pump, filter, valves, pressure, and leaks.")


class RAGTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Chroma may release its Windows memory-mapped index just after teardown.
        cls.temporary_directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.vector_path = Path(cls.temporary_directory.name) / "vectors"
        cls.store, cls.document_count, cls.chunk_count = build_vector_store(
            DEFAULT_KNOWLEDGE_PATH, cls.vector_path
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.store = None
        SharedSystemClient.clear_system_cache()
        cls.temporary_directory.cleanup()

    def test_loads_all_five_knowledge_files(self):
        self.assertEqual(len(load_knowledge_documents()), 5)

    def test_loader_preserves_filename_and_source(self):
        metadata = load_knowledge_documents()[0].metadata
        self.assertIn("filename", metadata)
        self.assertTrue(metadata["source"].endswith(metadata["filename"]))

    def test_chunker_creates_multiple_chunks(self):
        self.assertGreater(len(chunk_documents(load_knowledge_documents())), 5)

    def test_chunks_preserve_source_metadata(self):
        chunk = chunk_documents(load_knowledge_documents())[0]
        self.assertIn("filename", chunk.metadata)
        self.assertIn("chunk_id", chunk.metadata)

    def test_vector_store_build_counts(self):
        self.assertEqual(self.document_count, 5)
        self.assertGreater(self.chunk_count, self.document_count)

    def test_vector_store_can_be_reloaded(self):
        self.assertIsNotNone(load_vector_store(self.vector_path))

    def test_tomato_query_retrieves_tomato_document(self):
        chunks = retrieve_context("tomato flowering soil moisture", 3, self.vector_path)
        self.assertIn("tomato_irrigation.md", {c.metadata["filename"] for c in chunks})

    def test_rice_query_retrieves_rice_document(self):
        chunks = retrieve_context("rice alternate wetting drying field water tube", 3, self.vector_path)
        self.assertIn("rice_irrigation.md", {c.metadata["filename"] for c in chunks})

    def test_drip_query_retrieves_sop(self):
        chunks = retrieve_context("low pressure filter leak drip line", 3, self.vector_path)
        self.assertIn("drip_irrigation_sop.md", {c.metadata["filename"] for c in chunks})

    def test_k_limit_is_respected(self):
        self.assertEqual(len(retrieve_context("irrigation", 2, self.vector_path)), 2)

    def test_empty_question_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            retrieve_context("  ", persist_path=self.vector_path)

    def test_missing_store_has_clear_message(self):
        with self.assertRaisesRegex(FileNotFoundError, "vector_store"):
            load_vector_store(Path(self.temporary_directory.name) / "missing")

    def test_missing_llm_is_controlled(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(LLMNotConfiguredError):
                get_llm()

    def test_answer_contains_sources_and_deduplicates(self):
        llm = FakeGroundedLLM()
        result = answer_question(
            "What should I check if drip pressure is low?",
            persist_path=self.vector_path,
            llm=llm,
        )
        self.assertIn("drip_irrigation_sop.md", result.sources)
        self.assertEqual(len(result.sources), len(set(result.sources)))
        self.assertIn("Context:", llm.last_prompt)

    def test_structured_gemini_content_becomes_plain_text(self):
        result = type(
            "GeminiResult",
            (),
            {"content": [{"type": "text", "text": "Grounded Gemini answer"}]},
        )()
        self.assertEqual(_response_text(result), "Grounded Gemini answer")

    def test_api_rejects_blank_question(self):
        with TestClient(create_app(vector_store_path=self.vector_path)) as client:
            self.assertEqual(client.post("/knowledge/ask", json={"question": " "}).status_code, 422)

    def test_api_returns_mocked_grounded_answer(self):
        fake = type("Result", (), {"answer": "Grounded answer", "sources": ["rice_irrigation.md"]})()
        with patch("app.api.routes.answer_question", return_value=fake):
            with TestClient(create_app(vector_store_path=self.vector_path)) as client:
                response = client.post("/knowledge/ask", json={"question": "How is rice irrigated?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sources"], ["rice_irrigation.md"])


if __name__ == "__main__":
    unittest.main()
