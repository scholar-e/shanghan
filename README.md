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
edwin/
├── docs/                          # Original source documents
│   ├── Requirements_SHTCM_v1.docx
│   ├── SHLonly_ReEdited_forAIproject.docx
│   └── lesson105_lecturebyDrMa.docx
│
├── data/
│   ├── raw/                       # Converted text files
│   ├── parsed/                    # Structured JSON data
│   │   ├── textbook.json          # Parsed textbook
│   │   ├── lecture_105.json       # Parsed lecture
│   │   ├── knowledge_base.json    # Merged data
│   │   └── rag_chunks.json        # Chunks for vector DB
│   ├── vector_db/                 # ChromaDB storage
│   ├── terminology.json           # Bilingual glossary
│   └── line_signatures.json       # LINE number mappings
│
├── src/
│   ├── schema.py                  # Data models
│   ├── parse_textbook.py          # Textbook parser
│   ├── parse_lecture.py           # Lecture parser
│   ├── merge.py                   # Combines textbook + lectures
│   ├── vector_db.py               # ChromaDB setup
│   ├── terminology.py             # Bilingual support
│   ├── api.py                     # FastAPI server
│   └── ingest_lecture.py          # CLI for adding lectures
│
├── demo.py                        # End-to-end demo
├── requirements.txt               # Python dependencies
└── README.md                      # This file
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

## License

This project is developed for WASFS (Washington Acupuncture & Shenfu Studies).

## Acknowledgments

- Classical text: 重编施注涪陵古本伤寒杂病论
- Lectures: Dr. Ma Shouchun (马寿椿老师)
- Built with: ChromaDB, FastAPI, Claude
