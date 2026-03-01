# Technical Documentation

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
