# ShanghanTCM Evidence

AI-powered Traditional Chinese Medicine assistant based on the Shang Han Lun (伤寒论 - Treatise on Cold Damage).

## Overview

This system uses **RAG (Retrieval Augmented Generation)** to provide accurate, evidence-based responses grounded in:
- Classical Shang Han Lun text (396 LINEs, 126 formulas)
- Expert commentaries (施注 - Shi's annotations)
- Dr. Ma's lecture notes (马注 - modern clinical insights)
- Clinical case studies

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the demo
python demo.py

# 3. Or start the API server
cd src && uvicorn api:app --reload
```

## Project Structure

```
shanghan/
├── src/                           # Flask application (v1)
│   ├── server.py                  # Main Flask application
│   ├── chat_engine.py             # Chat engine with DeepSeek API
│   ├── knowledge_base.py          # TCM knowledge base
│   ├── logger.py                  # Logging configuration
│   ├── requirements.txt           # Python dependencies
│   ├── templates/                 # HTML templates
│   │   ├── home.html
│   │   ├── login.html
│   │   ├── chat.html
│   │   └── admin.html
│   ├── data/                      # Application data
│   │   ├── feedback/              # User feedback
│   │   └── conversations/         # Saved conversations
│   ├── logs/                      # Application logs
│   ├── tests/                     # Test suite
│   └── static/                    # Static files (CSS, JS)
│
├── nginx/                         # Nginx configuration for SSL
│   ├── nginx.conf                 # Main nginx configuration
│   ├── generate-ssl.sh            # SSL certificate generator
│   └── README.md                  # Nginx setup instructions
│
├── lessons/                       # Lesson documents
│   ├── labeled/                   # Labeled lesson files
│   └── original/                  # Original lesson files
│
├── docs/                          # Project documentation
│   ├── technical.md               # Technical specifications
│   ├── business_requirements.md   # Business requirements
│   ├── versions.md                # Version history
│   └── templates/                 # Documentation templates
│
├── logs/                          # System logs (legacy)
└── server.py                      # Legacy root server (simple version)
```

## Data Model

### LINE Structure
Each LINE from the Shang Han Lun contains:
- **Original text** (原文): Classical Chinese text
- **Song reference** (宋本): Reference to Song dynasty edition
- **Commentaries**: Multiple expert interpretations
  - 施注 (Shi's commentary) - from textbook
  - 马注 (Ma's commentary) - from lectures
- **Clinical cases**: Real-world applications from Dr. Ma
- **Formula reference**: Link to associated formula

### Formula Structure
- Number (方号): Unique identifier
- Name (方名): Chinese name with pinyin and English
- Ingredients (组成): Herb composition with dosages
- Preparation (用法): How to prepare and administer
- Analyses (方解): Expert explanations of the formula

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check and stats |
| `/chat` | POST | Main chat with RAG |
| `/search` | POST | Semantic search |
| `/formula/{n}` | GET | Get formula details |
| `/line/{n}` | GET | Get LINE details |
| `/formulas` | GET | List all formulas |
| `/lines` | GET | List LINEs with pagination |

### Example Chat Request
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "眩晕应该用什么方", "language": "zh"}'
```

## Adding New Lectures

1. Place the lecture `.docx` file in `docs/`
2. Run the ingestion pipeline:
   ```bash
   python src/ingest_lecture.py docs/lesson_XXX.docx
   ```
3. The tool will:
   - Parse the lecture
   - Prompt for LINE signature mappings (if needed)
   - Merge into the knowledge base
   - Regenerate RAG chunks

## Bilingual Support

The system supports both Chinese and English queries:
- Terminology glossary maps terms across languages
- Query expansion finds synonyms automatically
- Responses can be in either language

## Architecture

```
User Query
    ↓
[Query Expansion] ← Terminology Glossary
    ↓
[Vector Search] ← ChromaDB + Embeddings
    ↓
[Context Retrieval] → Relevant LINEs, Formulas, Cases
    ↓
[Prompt Construction]
    ↓
[LLM (Claude)] → Response
    ↓
User
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Required for AI-generated responses |

## Safety Notes

⚠️ **Important Disclaimers**:
- This system is for **education and professional support only**
- Not intended for self-diagnosis or emergency situations
- Clinical decisions should be made by licensed practitioners
- Always verify information with authoritative sources

## Development

```bash
# Run tests
pytest

# Start dev server with auto-reload
cd src && uvicorn api:app --reload

# Regenerate RAG chunks after data changes
python src/merge.py
```

## Updating Textbook And Lecture
After updating data/raw/textbook.txt, or any lecture_xxx.txt, run this command to generate parsed textbook
```bash
python src/parse_textbook.py

python src/parse_lecture.py
```

## Production Deployment with Nginx

For production deployment with SSL termination, use the nginx configuration provided in the `nginx/` directory.

### Setup Steps

1. **Install nginx** on your server
2. **Generate SSL certificates** (use Let's Encrypt for production or `nginx/generate-ssl.sh` for testing)
3. **Configure nginx**:
   ```bash
   sudo cp nginx/nginx.conf /etc/nginx/nginx.conf
   sudo nginx -t  # Test configuration
   sudo systemctl restart nginx
   ```
4. **Start Flask application**:
   ```bash
   cd src
   PORT=5000 FLASK_HOST=127.0.0.1 .venv/bin/python server.py
   ```
   For production, use a process manager like systemd or supervisor.

### Architecture

```
Browser → HTTPS (443) → nginx → HTTP (5000) → Flask
```

- Nginx handles SSL termination and static files
- Flask runs on localhost:5000 for security
- HTTP traffic is automatically redirected to HTTPS

### Testing

Run the nginx configuration tests:
```bash
cd src
pytest tests/test_nginx.py -v
```

See `nginx/README.md` for detailed setup instructions.

## License

This project is developed for WASFS (Washington Acupuncture & Shenfu Studies).

## Acknowledgments

- Classical text: 重编施注涪陵古本伤寒杂病论
- Lectures: Dr. Ma Shouchun (马寿椿老师)
- Built with: ChromaDB, FastAPI, Claude
