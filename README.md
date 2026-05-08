# StreamVault Analytics Assistant

> A secure, production-grade AI-powered internal analytics assistant for StreamVault Entertainment.
> Combines SQL, PDF, and CSV data sources with real-time reasoning transparency, SSE streaming, and multi-source intelligence.

[![Docker](https://img.shields.io/badge/Docker-ready-blue)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue)](https://reactjs.org/)
[![Groq](https://img.shields.io/badge/Groq-llama--3.3--70b-orange)](https://groq.com/)

---

## Architecture Overview

![StreamVault Architecture](docs/architecture.png)
---

## Key Features

### AI & Reasoning
- **Multi-source answers** — every response combines SQL + PDF + CSV data
- **SSE streaming** — live reasoning trace shows tool calls as they happen
- **Query decomposition** — complex multi-part questions split into sub-queries, answered independently, then synthesized
- **Ambiguity detection** — vague questions trigger clarifying prompts instead of guessing
- **Escalating RAG sensitivity** — PDF retrieval starts at `low`, escalates to `medium` → `high` if needed
- **Hallucination guard** — numbers and proper nouns verified against tool results; confidence downgraded silently
- **Confidence scoring** — rule-based scoring across 6 signals (tool results, RAG chunks, failures, escalations)
- **Tool deduplication** — MD5 hash cache prevents identical tool calls within same request
- **Auto-retry** — Groq tool format errors auto-retry with simplified prompt

### Security
- **JWT authentication** on all protected endpoints (8-hour expiry, auto-logout on 401)
- **Prompt injection detection** — 15 regex patterns block before reaching the LLM
- **Column-level security views** — 6 SQLite views exclude PII and financial columns
- **No raw LLM SQL** — AI calls pre-defined tool functions, never writes raw queries
- **Env-based secrets** — no hardcoded credentials anywhere in source code
- **Audit logging** — every query logged with user, sources accessed, sensitivity level, confidence

### Frontend
- **Live SSE timeline** — tool calls appear one by one as the agent works
- **Source badges** — every response shows exactly which data sources were used
- **Confidence badge** — high/medium shown visually on each response
- **Escalation badge** — warns when sensitive data was accessed
- **Follow-up chips** — clickable suggested questions after every response
- **Conversation persistence** — chat history survives page refresh via localStorage
- **Working filters** — period and genre filters actually re-query the backend
- **4 interactive charts** — genre, trend, regional, marketing with tooltips

---

## Data Sources

| Source | Type | Files | Contents |
|--------|------|-------|----------|
| SQLite | Structured SQL | 6 tables | movies, viewers, watch_activity, reviews, marketing_spend, regional_performance |
| ChromaDB | Vector store | 5 PDFs | quarterly_executive_report, campaign_performance_summary, content_roadmap, policy_guidelines, audience_behavior_report |
| Pandas | In-memory CSV | 6 CSV files | Same datasets for fast aggregation and trend analysis |

---

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Groq API key — free at [console.groq.com](https://console.groq.com)

### 1. Clone and configure

```bash
git clone https://github.com/Bharathwaj7/streamvault-assistant.git
cd streamvault-assistant
cp .env.example .env
```

Edit `.env` and set:
```
GROQ_API_KEY=your_groq_api_key_here
SECRET_KEY=any-random-32-char-string
```

### 2. Run

```bash
docker-compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

Data ingestion (CSV → SQLite, PDF → ChromaDB) runs **automatically on startup**. Takes ~30 seconds.

### 3. Login

| Username | Password | Role |
|----------|----------|------|
| admin | streamvault2025 | Full access |
| analyst | analyst123 | Read-only analytics |

---

## Running Without Docker (Local Dev)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Update .env for local paths:
# SQLITE_DB_PATH=./data/sqlite/streamvault.db
# CHROMA_DB_PATH=./data/chroma
# DATA_DIR=./data

uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev     # → http://localhost:5173
```

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/token` | None | Login, returns JWT |
| POST | `/api/chat` | Bearer | Chat — returns SSE stream |
| GET | `/api/analytics/insights` | Bearer | Dashboard KPIs + chart data (supports `?period=q1_2025&genre=Action`) |
| POST | `/api/feedback` | Bearer | Submit thumbs up/down feedback |
| POST | `/api/ingest` | Admin | Re-run data ingestion |
| GET | `/health` | None | Health check |

### Chat endpoint — SSE events

The `/api/chat` endpoint returns a `text/event-stream`. Events emitted during processing:

```
data: {"type": "tool_call", "tool_name": "query_database", "latency_ms": 45}
data: {"type": "rag_retrieval", "query": "...", "sensitivity_level": "medium", "chunks_found": 4}
data: {"type": "rag_escalation", "from_level": "low", "to_level": "medium"}
data: {"type": "decomposing", "message": "Breaking down complex question..."}
data: {"type": "sub_query_start", "index": 1, "total": 2, "query": "..."}
data: {"type": "synthesizing", "message": "Synthesizing answers..."}
data: {"type": "retry", "tool_name": "groq", "attempt": 1, "error": "tool_format_error"}
data: {"type": "response", "answer": "...", "sources": [...], "confidence": "high", ...}
```

### Example chat request

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/token \
  -d "username=admin&password=streamvault2025" | jq -r .access_token)

# Send message
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Which titles performed best in 2025?", "history": []}' \
  --no-buffer
```

---

## Required Example Questions

All 6 required questions work with multi-source answers:

| # | Question | Tools Used | Sources |
|---|----------|------------|---------|
| 1 | Which titles performed best in 2025? | SQL + CSV | SQL Database + CSV Analytics |
| 2 | Why is Stellar Run trending recently? | PDF + CSV | PDF reports + CSV Analytics |
| 3 | Compare Dark Orbit vs Last Kingdom | SQL + CSV + PDF | All 3 sources |
| 4 | Which city had the strongest engagement? | SQL + CSV | SQL Database + CSV Analytics |
| 5 | What explains weak comedy performance? | CSV + PDF | CSV Analytics + PDF reports |
| 6 | What recommendations for leadership? | PDF + CSV | PDF reports + CSV Analytics |

---

## Project Structure

```
streamvault-assistant/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── main.py                         # FastAPI app + startup ingestion
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py               # Settings from env vars
│   │   │   ├── logging.py              # Structured JSON logging
│   │   │   └── security.py             # JWT + bcrypt auth
│   │   ├── api/routes/
│   │   │   ├── chat.py                 # SSE streaming, injection detection, normalizer
│   │   │   ├── analytics.py            # Dashboard insights with period/genre filters
│   │   │   ├── auth.py                 # Login endpoint
│   │   │   ├── feedback.py             # Thumbs up/down storage
│   │   │   └── ingest.py               # Manual re-ingestion trigger
│   │   ├── services/
│   │   │   ├── orchestrator.py         # Full agentic loop + SSE stream generator
│   │   │   ├── ingestion.py            # CSV → SQLite, PDF → ChromaDB with sensitivity tags
│   │   │   ├── analytics.py            # Dashboard data queries with filters
│   │   │   └── schema.py               # Dynamic schema loader (cached)
│   │   ├── tools/
│   │   │   ├── base.py                 # BaseTool abstract class
│   │   │   ├── sql_tool.py             # SELECT-only parameterized queries
│   │   │   ├── pdf_tool.py             # ChromaDB retrieval with sensitivity filter
│   │   │   ├── csv_tool.py             # 10 pre-defined pandas operations
│   │   │   └── registry.py             # Tool schema registration for Groq
│   │   ├── db/
│   │   │   ├── models.py               # SQLAlchemy table definitions
│   │   │   ├── views.py                # 6 security views (PII/financial columns excluded)
│   │   │   ├── database.py             # Async SQLite connection
│   │   │   └── chroma.py               # ChromaDB client
│   │   └── schemas/
│   │       ├── chat.py                 # ChatRequest, ChatResponse, ToolCallTrace
│   │       └── analytics.py            # InsightResponse, KPIMetric, ChartData
│   └── data/
│       ├── csv/                        # 6 CSV files (movies, viewers, etc.)
│       ├── pdf/                        # 5 PDF reports
│       └── sqlite/                     # Auto-created at runtime
└── frontend/
    ├── nginx.conf                      # Reverse proxy + SSE buffering disabled
    ├── Dockerfile
    ├── src/
    │   ├── pages/
    │   │   ├── Dashboard.jsx           # Root layout + shared handleSend
    │   │   └── Login.jsx
    │   ├── components/
    │   │   ├── chat/
    │   │   │   ├── ChatWindow.jsx      # SSE consumer + live events display
    │   │   │   ├── MessageBubble.jsx   # Confidence badge, escalation badge, follow-ups
    │   │   │   ├── ToolTrace.jsx       # Live SSE timeline + static trace details
    │   │   │   └── ChatInput.jsx
    │   │   ├── charts/
    │   │   │   ├── GenreBarChart.jsx
    │   │   │   ├── ViewsTrendChart.jsx
    │   │   │   ├── RegionalHeatmap.jsx
    │   │   │   └── MarketingROAS.jsx
    │   │   ├── insights/
    │   │   │   ├── InsightsPanel.jsx   # Period + genre filters, skeleton loaders
    │   │   │   ├── KPICard.jsx
    │   │   │   └── TopTitlesTable.jsx  # Sortable columns
    │   │   └── layout/
    │   │       ├── Header.jsx
    │   │       └── Sidebar.jsx         # Suggested questions
    │   ├── store/
    │   │   └── chatStore.js            # Zustand + localStorage persistence
    │   └── api/
    │       └── client.js               # Axios + SSE async generator
    └── package.json
```

---

## Security Design

| Layer | Implementation |
|-------|----------------|
| Authentication | JWT Bearer tokens, 8-hour expiry, auto-logout on 401 |
| Prompt injection | 15 regex patterns checked before LLM call, blocked with log |
| SQL safety | SELECT-only queries, no LLM-generated SQL, parameterized queries |
| Column security | 6 SQLite views exclude: `budget_usd`, `director`, `cast_lead`, `viewer_id` |
| PII protection | System prompt prohibits individual viewer data; aggregated stats only |
| Tool isolation | AI accesses data only through 3 approved tool functions |
| Secret management | All credentials in `.env`, never in source code |
| Audit trail | Every query logged: user, sources, sensitivity level, confidence, duration |
| Input validation | Pydantic schemas with length limits on all endpoints |
| Data sensitivity | PDF chunks tagged `low/medium/high` at ingest; retrieval starts at `medium` |

---

## Advanced Features

### Query Decomposition
Complex multi-part questions are automatically detected and split into independent sub-queries:
```
"Which titles performed best in 2025 and also what explains weak comedy performance?"
→ Sub-query 1: "What are the top performing titles in 2025?"
→ Sub-query 2: "What explains weak comedy performance?"
→ Synthesized into single coherent answer
```

### Escalating RAG Sensitivity
PDF chunks are tagged at ingest time based on content:
- `low` — general trends, public summaries
- `medium` — campaign performance, regional breakdowns, audience segments
- `high` — financial details, executive forecasts, internal cost data

Retrieval starts at `medium`. If insufficient results → escalates to `high` automatically.

### Confidence Scoring
Every response gets a confidence score based on:
- +2 if 3+ tool results returned
- +2 if 3+ RAG chunks found
- -1 if any tool failed
- -1 if RAG had to escalate
- -1 if unverified claims detected
- -2 if iteration cap hit

### Audit Logging
Every completed query emits:
```json
{
  "message": "audit: data_access",
  "query_id": "uuid",
  "user": "admin",
  "sources_accessed": ["SQL Database", "CSV Analytics"],
  "sensitivity_level": "medium",
  "confidence": "high",
  "tokens_used": 4500,
  "duration_s": 2.3
}
```

---

## Assumptions & Tradeoffs

| Decision | Rationale |
|----------|-----------|
| SQLite over PostgreSQL | Zero-setup for evaluation; swap by changing `db_url` in config |
| ChromaDB embedded | No separate vector server needed; suitable for 5 PDFs |
| Groq llama-3.3-70b | Best tool-calling reliability on free tier; ~2s response time |
| Custom agentic loop over LangGraph | More control, easier debugging, no additional dependency risk |
| Keyword sensitivity tagging | Sufficient for this corpus; production would use an LLM classifier |
| SSE over WebSockets | Simpler, stateless, works through nginx without special config |
| JWT without refresh tokens | Acceptable for internal tool with 8-hour session |
| In-memory CSV cache | Avoids repeated disk reads; reloaded on ingest trigger |
| Demo credentials in README | Evaluator convenience; production would use a users table |
| nginx `proxy_buffering off` | Required for SSE to stream in real-time through reverse proxy |

---

## Evaluation Notes

- **Multi-source reasoning** — ToolTrace panel shows every tool called with arguments and latency
- **Source attribution** — coloured badges on every message: 🗄️ SQL Database · 📄 PDF · 📊 CSV Analytics
- **Security thinking** — implemented at architecture level, not just documented
- **Explainability** — live SSE timeline shows the agent's reasoning process in real-time
- **All 6 required questions** answered using real generated data with 2+ sources each
- **Single command deployment** — `docker-compose up --build` is all that's needed
