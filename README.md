# Pushan — The Next-Gen AI Agriculture Engine (V0.7)

Pushan is a prototype smart-irrigation process-intelligence platform. V0.7 adds a retrieval-augmented generation (RAG) knowledge assistant while preserving the existing sensor, rule, ML, operational, SQLite, API, and dashboard layers.

## Project evolution

```text
V0.1  Rule-Based Irrigation Engine
V0.2  Sensor Simulation + Operational Feasibility
V0.3  SQLite Persistence + Historical Records
V0.4  Machine-Learning Irrigation Prediction
V0.5  FastAPI Backend
V0.6  Streamlit Dashboard
V0.7  RAG Agriculture Knowledge System
```

RAG allows Pushan to search its own agriculture documents before asking an LLM to generate an answer. This reduces reliance on model memory and makes answers traceable to the project's knowledge base.

## Architecture and responsibilities

```text
User Question → Streamlit → FastAPI → RAG Service → Retriever
     → Chroma Vector Store → Relevant Chunks → LLM
     → Grounded Answer + Source Filenames
```

The RAG path complements—never replaces—the operational path:

- **RAG:** knowledge and explanation only.
- **ML:** predictive advisory only.
- **Rule engine:** deterministic irrigation recommendation.
- **Operational engine:** execution feasibility and safety state.

The knowledge assistant cannot switch a pump or override operational rules. Streamlit calls FastAPI; it never imports backend RAG or irrigation logic directly.

## RAG concepts in plain English

- **Chunking:** breaking documents into small overlapping passages. V0.7 uses 800 characters with 100 overlap and preserves source metadata.
- **Embeddings:** numerical text representations used to find related wording. V0.7 uses deterministic local hash embeddings, so retrieval needs no paid API.
- **Vector database:** Chroma stores chunk vectors and metadata for similarity search.
- **Retrieval:** selecting the chunks most relevant to the question before generation.
- **Generation:** a Google Gemini model turns only the retrieved passages into a readable answer.
- **Grounding:** requiring the model to use supplied context, admit insufficient information, and return source filenames.

The local embedding is lightweight and test-friendly. A production semantic embedding provider can later replace only `app/rag/embeddings.py`.

## Install and configure

Python 3.11 or newer is required.

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` locally:

```text
GOOGLE_API_KEY=your_key_here
PUSHAN_LLM_MODEL=gemini-3.1-flash-lite
PUSHAN_API_URL=http://127.0.0.1:8000
```

`.env` is ignored by Git. Never commit or paste real keys into source, tests, logs, screenshots, issues, or chat. Retrieval and tests work without a key; only live generation needs one. Pushan uses Gemini 3.1 Flash-Lite for high-volume, cost-efficient generation while keeping embeddings local so indexing and retrieval consume no Gemini quota. Google's free-tier terms currently state that submitted content may be used to improve its products; do not submit sensitive farm or personal data without reviewing the applicable terms.

## Build the knowledge index

Run after installation and whenever a knowledge document changes:

```powershell
python -m app.rag.vector_store
```

This loads `knowledge/*.md`, chunks and embeds them locally, and persists Chroma under `artifacts/vector_store/`. Questions never silently rebuild the index.

## Train and run

Train the advisory model once:

```powershell
python -m app.ml.train
```

Then use two terminals:

```powershell
# Terminal 1
python -m uvicorn app.main_api:app --reload

# Terminal 2
python -m streamlit run frontend/streamlit_app.py
```

Open `http://localhost:8501`. API health is at `http://127.0.0.1:8000/health`, Swagger at `/docs`, and the knowledge route is `POST /knowledge/ask`.

## Project structure

```text
Project_Pushan/
├── app/
│   ├── api/  database/  ml/  services/
│   └── rag/
│       ├── loader.py  chunking.py  embeddings.py
│       └── vector_store.py  retriever.py  qa_service.py
├── knowledge/
│   ├── irrigation_basics.md  tomato_irrigation.md
│   ├── rice_irrigation.md  cotton_irrigation.md
│   └── drip_irrigation_sop.md
├── artifacts/vector_store/       # generated, ignored
├── frontend/  tests/
├── .env.example  README.md  requirements.txt
```

Every knowledge document is labeled as a prototype and ends with authoritative sources. It is educational and requires local agronomic validation.

## Tests

```powershell
python -m unittest discover -s tests
```

The suite uses local embeddings and a mocked LLM, so it makes no live paid model call. It verifies loading, metadata, chunking, persistence, retrieval, source deduplication, controlled failures, API/UI integration, and V0.1–V0.6 behaviour.

## V0.7 boundary

V0.7 remains local and prototype-grade. It has no LangGraph, multi-agent orchestration, Power Automate, Docker, cloud deployment, or real IoT control. Its modular retrieval pipeline prepares a clean knowledge capability for future orchestration without implementing V0.8.
