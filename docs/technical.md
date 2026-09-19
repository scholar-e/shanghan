# Technical Documentation

## Current AI implementation

The running application uses Flask, SQLite keyword/pinyin retrieval, and a
bounded DeepSeek or Claude tool loop. The ChromaDB/embedding diagrams below are
historical design notes, not the current implementation.

- `src/retrieval.py` shares reference parsing, formula matching, textbook lookup,
  and source formatting between `/api/search`, initial chat context, and AI
  tools. Bare line numbers use Fuling numbering; explicit Songben requests use
  its alignment. Decimal references such as `26.9` and `chapter 26 line 9` are
  resolved as one Zabing reference. Explicit `金匮 10.9` selects the comparison
  edition, while bare `10.9` selects the Fuling reference. Formula and lecture
  numbers do not become article numbers.
- Public search remains textbook-only. Chat can search lecture passages or
  retrieve a specific lecture, including keyword-centered excerpts from later
  in the lecture. Lecture text is available to the model and admin conversation
  review, but is excluded from public citation metadata and popups.
- `src/evidence.py` owns an evidence registry for each chat request. Source
  identities (`type:key`) are stable; display citation numbers are append-only
  within that answer. Initial evidence and tool results share this registry.
  Both provider protocols return tool records with `citation` and `source_id`.
  Duplicate retrieval preserves the citation number and can add fuller text.
- Chat returns and persists the final registry, including evidence discovered
  through tools. Evidence is bounded before prompt assembly so citation labels
  and instructions remain intact. Unknown numeric citations are visibly marked
  as unavailable; this checks source identity, not claim-level support.
- Each rendered answer and reference list retains its own sources, so clicking
  an older citation cannot open a newer answer's evidence.

Offline regression tests (temporary, seeded databases; mocked provider calls):

```bash
.venv/bin/python -m pytest -q src/tests/test_evidence_retrieval.py
node src/tests/test_citations.cjs
```

The `deploy/src` copies of these modules and templates must be synchronized
when preparing a deployment. Updating those local copies does not deploy the
running service.

### Fourth textbook part: Yiji guide

`textbook4thpart_ReEdited_SHLYiJiGuide.docx` contains 113 entries in 15 sections
of 辨伤寒宜忌脉症篇第十五. Its identifiers run from `YJ.1` through `YJ.114`,
with `YJ.31` absent from the supplied document. The importer preserves that gap
and the five explicit Songben alignments. The guide mentions existing formulas
but contains no additional formula-definition blocks.

```bash
.venv/bin/python tools/ingest_yiji_textbook.py --txt --db
.venv/bin/python tools/ingest_yiji_textbook.py --db --database deploy/src/data/shanghan.db
```

With no flags, the importer validates and reports the source without writing
text or database records. `--txt` generates `textbook_yiji.txt`; `--db` upserts
only the guide entries. They share the supplementary `zabing_articles` table
with parts 2–3, using separate `yiji_YJ.N` keys. Search and citations identify
them as `yiji` / `yiji_article`; they are never resolved as ordinary integer
article numbers. Supported queries include `YJ.2`, `宜忌第2条`, and
`宜忌 咽喉干燥`. Reimporting Zabing with `--clear` preserves the guide rows.

`prod_deploy.sh` packages the source DOCX files for parts 2–4 and both derived
text files. After installing dependencies, it upserts the supplementary corpus
into the installed and mirror databases, even on a code-only deployment.
Conversations, feedback, prescriptions, and lectures are preserved. Database
WAL/SHM runtime files are excluded from release archives and Git.

Regression coverage: `src/tests/test_yiji_ingestion.py` checks the document's
numbering and alignments, repeat imports, existing-data preservation, exact and
keyword retrieval, public search, and AI citation identity.

---

## v0.5: Local Development Version

A fully local version that runs on a developer's machine with their own AI API key.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                         │
│  Browser-based UI (HTML/CSS/JS)                             │
│  - Home page, Login, Chat interface                         │
│  - Runs via file:// or local server                         │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP (localhost)
┌────────────────────────▼────────────────────────────────────┐
│                     APPLICATION LAYER                       │
│  FastAPI Server (Python)                                    │
│  - Serves UI templates                                     │
│  - Handles authentication                                   │
│  - Routes API requests                                     │
│  - Runs on localhost:8000                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      RAG LAYER                             │
│  Retrieval-Augmented Generation                            │
│  - Query expansion via terminology glossary                │
│  - Vector search in ChromaDB                               │
│  - Context retrieval (LINEs, Formulas, Cases)              │
│  - Prompt construction                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      MODEL LAYER                           │
│  LLM for response generation                               │
│  - DeepSeek API (user provides key)                │
│  - Uses DEEPSEEK_API_KEY env var                          │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      DATA LAYER                             │
│  Local file storage                                        │
│  - data/parsed/ - JSON knowledge base                      │
│  - data/vector_db/ - ChromaDB vector store                │
│  - data/feedback/ - JSON feedback files                    │
│  - data/conversations/ - JSON conversation logs            │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Description |
|-------|------------|-------------|
| Client | HTML/CSS/JavaScript | Browser-based, no build step |
| Server | FastAPI | Python web framework, async |
| Database | ChromaDB | Vector database for semantic search |
| Embeddings | OpenAI or local | Text embedding generation |
| LLM | DeepSeek | AI response generation |
| Storage | Local JSON files | Feedback, conversations |

### Running v0.5

```bash
# 1. Set your API key
export DEEPSEEK_API_KEY="sk-ant-..."

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the API server
cd src && uvicorn api:app --reload

# 4. Open browser to http://localhost:8000
```

### Data Flow (v0.5)

1. User sends message via chat UI
2. FastAPI receives request at `/chat` endpoint
3. Query expansion uses terminology glossary
4. ChromaDB performs vector similarity search
5. Relevant context retrieved (LINEs, Formulas, Cases)
6. Prompt constructed with context
7. Claude API generates response
8. Response returned to client
9. Feedback saved to local JSON file

---

## v1: Server-Client Production Version

A deployed version with separate server and client, professional authentication, and centralized data.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                         │
│  Browser-based UI (HTML/CSS/JS)                             │
│  - Static files served by CDN or web server                │
│  - Home page, Login, Chat interface                        │
│  - Accessed via HTTPS                                      │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS (production)
┌────────────────────────▼────────────────────────────────────┐
│                      REVERSE PROXY                          │
│  Nginx                                                       │
│  - SSL/TLS termination                                     │
│  - Request routing                                         │
│  - Load balancing (if needed)                              │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     APPLICATION LAYER                      │
│  Flask Server (Python)                                      │
│  - Session-based authentication                            │
│  - Serves templates                                        │
│  - Routes API requests                                     │
│  - Runs on localhost:8000                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      RAG LAYER                             │
│  Retrieval-Augmented Generation                            │
│  - Query expansion via terminology glossary                │
│  - Vector search in ChromaDB                               │
│  - Context retrieval (LINEs, Formulas, Cases)              │
│  - Prompt construction                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      MODEL LAYER                           │
│  LLM for response generation                               │
│  - DeepSeek API (server-side)                      │
│  - Uses DEEPSEEK_API_KEY env var                         │
│  - Single key for all users                                │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      DATA LAYER                             │
│  Server-side storage                                        │
│  - data/parsed/ - JSON knowledge base (read-only)         │
│  - data/vector_db/ - ChromaDB vector store (read-only)    │
│  - /data/feedback/ - JSON feedback files (per user)         │
│  - /data/conversations/ - JSON conversation logs            │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Description |
|-------|------------|-------------|
| Client | HTML/CSS/JavaScript | Browser-based, static files |
| Reverse Proxy | Nginx | SSL, routing |
| Server | Flask | Python web framework |
| Database | ChromaDB | Vector database |
| Embeddings | OpenAI | Text embedding generation |
| LLM | DeepSeek | AI response generation |
| Storage | Server filesystem | JSON files for feedback/conversations |
| Auth | Session-based | Professional users only |

### Pages (v1)

| Page | Route | Description |
|------|-------|-------------|
| Home | `/` | Overview, capabilities, sign-in CTA |
| Login | `/login` | Email/password authentication |
| Chat | `/chat` | Main chatbot interface |

### API Endpoints (v1)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Home page |
| `/login` | GET | Login page |
| `/chat` | GET | Chat page (auth required) |
| `/api/login` | POST | Authenticate user |
| `/api/logout` | POST | End session |
| `/api/chat` | POST | Send message, get AI response |
| `/api/feedback` | POST | Submit feedback on response |

### Authentication (v1)

- Professional-only access (no guest)
- Email/password stored server-side
- Session-based authentication (Flask sessions)
- User email displayed in header
- Logout clears session

### Data Storage (v1)

All data stored on server filesystem:

```
/data/
├── feedback/
│   └── feedback_{timestamp}_{user_hash}.json
└── conversations/
    └── conversation_{session_id}_{date}.json
```

Admin access via SSH to read JSON files.

### Running v1 (Development)

```bash
# 1. Set API key
export DEEPSEEK_API_KEY="sk-ant-..."

# 2. Run Flask server
python server.py

# 3. Open http://localhost:8000
```

### Running v1 (Production)

```bash
# 1. Deploy to server
# 2. Configure Nginx with SSL certificate
# 3. Set environment variables
# 4. Start Flask with gunicorn or systemd
```

### Key Differences: v0.5 vs v1

| Aspect | v0.5 | v1 |
|--------|------|-----|
| Run location | Local machine | Server + Client |
| API key | User provides own | Server-side |
| Authentication | None | Session-based |
| Data access | Local files | Server via SSH |
| Client access | localhost | HTTPS anywhere |
| Use case | Development | Production |
| Server | FastAPI | Flask |
| Reverse proxy | None | Nginx |

---

## RAG Implementation Details

Based on the Shang Han Lun RAG system from the project README.

### Retrieval Process

```
User Query (Chinese or English)
         ↓
    [Query Expansion]
    ← Terminology Glossary →
         ↓
    [Vector Search]
    ← ChromaDB + Embeddings →
         ↓
    [Context Retrieval]
    → Relevant LINEs, Formulas, Cases
         ↓
    [Prompt Construction]
         ↓
    [LLM (Claude)]
         ↓
       Response
         ↓
    [Source Citations]
```

### Data Models

**LINE Structure:**
- Original text (原文): Classical Chinese
- Song reference (宋本): Song dynasty edition
- Commentaries: 施注 (Shi), 马注 (Ma)
- Clinical cases
- Formula reference

**Formula Structure:**
- Number (方号): Unique ID
- Name (方名): Chinese, pinyin, English
- Ingredients (组成): Herbs and dosages
- Preparation (用法)
- Analyses (方解): Expert explanations

### Knowledge Base Files

| File | Description |
|------|-------------|
| `data/parsed/textbook.json` | Parsed classical text |
| `data/parsed/knowledge_base.json` | Merged textbook + lectures |
| `data/parsed/rag_chunks.json` | Chunks for vector search |
| `data/vector_db/` | ChromaDB persistent storage |
| `data/terminology.json` | Bilingual glossary |
| `data/line_signatures.json` | LINE number mappings |
