# StreamVault Analytics Assistant

A secure, AI-powered internal analytics assistant for StreamVault Entertainment. Answers business questions by combining structured SQL data, PDF internal reports, and CSV analytics — with full source attribution and tool call tracing.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                          │
│   ┌──────────────┐  ┌───────────────┐  ┌────────────────────┐  │
│   │  Chat UI      │  │ Insights Panel│  │  Tool Trace Panel  │  │
│   │  + History    │  │ + 4 Charts    │  │  (collapsible)     │  │
│   └──────┬───────┘  └───────────────┘  └────────────────────┘  │
└──────────┼──────────────────────────────────────────────────────┘
           │  JWT-authenticated REST (POST /api/chat)
┌──────────▼──────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │               AI Orchestrator (orchestrator.py)           │   │
│  │  1. Build prompt + tool schemas                           │   │
│  │  2. Send to Groq (llama-3.3-70b-versatile)               │   │
│  │  3. Receive tool_call → execute tool                      │   │
│  │  4. Feed result back → loop until final answer            │   │
│  │  5. Return answer + sources + tool_traces                 │   │
│  └────────┬────────────────────┬──────────────┬─────────────┘   │
│           │                    │              │                  │
│  ┌────────▼──────┐  ┌──────────▼───┐  ┌──────▼──────────────┐  │
│  │  SQL Tool     │  │   PDF Tool   │  │    CSV Tool          │  │
│  │  (aiosqlite)  │  │  (ChromaDB)  │  │    (pandas)          │  │
│  └────────┬──────┘  └──────────┬───┘  └──────┬──────────────┘  │
│           │                    │              │                  │
│  ┌────────▼──────┐  ┌──────────▼───┐  ┌──────▼──────────────┐  │
│  │  SQLite DB    │  │  Chroma Vec. │  │  In-Memory Cache     │  │
│  │  (6 tables)   │  │  Store       │  │  (6 CSV DataFrames)  │  │
│  └───────────────┘  └──────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Sources

| Source | Type | Contents |
|--------|------|----------|
| SQLite DB | Structured | movies, viewers, watch_activity, reviews, marketing_spend, regional_performance |
| ChromaDB | Vector | quarterly_executive_report, campaign_performance_summary, content_roadmap, policy_guidelines, audience_behavior_report |
| Pandas CSV | Analytics | Same 6 CSV files for aggregations and trend analysis |

---

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Groq API key (free at [console.groq.com](https://console.groq.com))

### 1. Clone & configure

```bash
git clone https://github.com/your-username/streamvault-assistant.git
cd streamvault-assistant
cp .env.example .env
```

Edit `.env` and set:
```
GROQ_API_KEY=your_groq_api_key_here
SECRET_KEY=any-random-32-char-string
```

### 2. Run with Docker

```bash
docker-compose up --build
```

- Frontend → http://localhost:3000
- Backend API → http://localhost:8000
- API Docs → http://localhost:8000/docs

### 3. Login

| Username | Password | Role |
|----------|----------|------|
| admin | streamvault2025 | Admin |
| analyst | analyst123 | Analyst |

Data ingestion (CSVs → SQLite, PDFs → ChromaDB) runs **automatically on startup**.

---

## Running Without Docker (Local Dev)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env      # fill in GROQ_API_KEY and SECRET_KEY

# Update paths in .env for local:
# SQLITE_DB_PATH=./data/sqlite/streamvault.db
# CHROMA_DB_PATH=./data/chroma
# DATA_DIR=./data

uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev         # → http://localhost:5173
```

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/token` | None | Get JWT token |
| POST | `/api/chat` | Bearer | Send a message, get AI response |
| GET | `/api/analytics/insights` | Bearer | Dashboard KPIs + chart data |
| POST | `/api/ingest` | Admin only | Re-run data ingestion |
| GET | `/health` | None | Health check |

### Example chat request

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Which titles performed best in 2025?",
    "history": []
  }'
```

---

## Project Structure

```
streamvault-assistant/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── app/
│   │   ├── core/                  # Config, logging, JWT
│   │   ├── api/routes/            # chat, analytics, ingest, auth
│   │   ├── services/              # orchestrator, ingestion, analytics
│   │   ├── tools/                 # sql_tool, pdf_tool, csv_tool, registry
│   │   ├── db/                    # SQLAlchemy models, ChromaDB client
│   │   └── schemas/               # Pydantic request/response models
│   └── data/
│       ├── csv/                   # 6 CSV files
│       ├── pdf/                   # 5 PDF reports
│       └── sqlite/                # Auto-created at runtime
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── chat/              # ChatWindow, MessageBubble, ToolTrace
    │   │   ├── charts/            # 4 Recharts components
    │   │   ├── insights/          # KPICard, TopTitlesTable, InsightsPanel
    │   │   └── layout/            # Header, Sidebar
    │   ├── pages/                 # Dashboard, Login
    │   ├── store/                 # Zustand state
    │   └── api/                   # Axios client
    └── Dockerfile
```

---

## Security Design

- **API keys never exposed to frontend** — Groq key lives only in backend `.env`
- **JWT authentication** on all protected endpoints
- **SQL injection prevention** — only SELECT queries allowed, validated before execution
- **No PII in responses** — system prompt explicitly prohibits individual viewer data
- **Tool-based access** — AI never touches raw DB directly, only through approved tool functions
- **Input validation** — Pydantic schemas on every request with length limits
- **Data classification** — policy_guidelines.pdf documents Level 1–4 data handling rules

---

## Example Questions

The system can answer all 6 required questions:

1. **"Which titles performed best in 2025?"**  
   → SQL tool queries watch_activity grouped by movie, cross-references movies table

2. **"Why is Stellar Run trending recently?"**  
   → SQL tool (monthly view spike) + PDF tool (campaign_performance_summary for marketing context)

3. **"Compare Dark Orbit vs Last Kingdom"**  
   → CSV tool (views, completion rates) + SQL tool (review scores)

4. **"Which city had the strongest engagement last month?"**  
   → SQL tool on regional_performance filtered by latest month

5. **"What explains weak comedy performance?"**  
   → CSV tool (low scores, low completion) + PDF tool (audience_behavior_report analysis)

6. **"What recommendations would you give for leadership?"**  
   → PDF tool (quarterly_executive_report) + SQL tool (supporting metrics)

---

## Assumptions & Tradeoffs

| Decision | Rationale |
|----------|-----------|
| SQLite over PostgreSQL | Zero-setup for evaluation; trivial to swap by changing `db_url` in config |
| ChromaDB for vectors | Embedded, no separate server needed; good enough for 5 PDFs |
| Groq llama-3.3-70b | Best tool-calling reliability on free tier; fast enough for demo |
| Simple keyword chunking for PDFs | Sufficient for this corpus size; production would use semantic chunking |
| JWT without refresh tokens | Acceptable for internal tool; 8-hour expiry |
| In-memory CSV cache | Avoids repeated disk reads; reloaded on ingest |
| Demo users hardcoded | Out of scope for this assignment; production would use a users table |
| Docker healthcheck starts after 60s | Ingestion on startup takes 20-40s; prevents frontend connecting too early |

---

## Evaluation Notes

- **Multi-source reasoning** is demonstrated by the ToolTrace panel in the UI — every response shows exactly which tools were called and with what arguments
- **Source attribution** appears as coloured badges on every assistant message: 🗄️ SQL, 📄 PDF, 📊 CSV
- **Security** is implemented at architecture level (tool-based access, JWT, no PII leakage) not just as a note
- **All 6 required example questions** are answered using real data from the generated datasets
