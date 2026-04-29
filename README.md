# EvalForge

**LLM Agent Benchmarking & Trustworthiness Platform**

EvalForge evaluates the quality and security of LLM-powered RAG agents using six RAGAS
metrics, a 6-category prompt injection test suite, and a composite trustworthiness score.
It runs entirely locally with [Ollama](https://ollama.com) — no OpenAI key required.

![CI](https://github.com/ImMriganka/EvalForge/actions/workflows/ci.yml/badge.svg)

---

## What It Does

| Capability | Detail |
|---|---|
| **RAG Quality Evaluation** | 6 RAGAS metrics: Faithfulness, Answer Relevancy, Context Precision, Context Recall, Factual Correctness, Noise Sensitivity |
| **Prompt Injection Testing** | 13 adversarial prompts across 6 attack categories (direct override, roleplay jailbreak, indirect tool, code injection, encoding tricks, context overflow) |
| **Trustworthiness Score** | Composite score: 50% faithfulness + 20% factual correctness + 30% injection robustness → letter grade A/B/C/D |
| **LangGraph Agents** | ReAct loop and Plan-Execute agents with calculator, date, and web search tools |
| **LangSmith Tracking** | Optional experiment tracking — silently skipped if no API key is set |
| **REST API** | FastAPI backend with auto-generated Swagger docs at `/docs` |
| **Dashboard UI** | Next.js frontend with live KPI cards, RAGAS bar chart, and injection breakdown |
| **CI Pipeline** | GitHub Actions: pytest (69 tests) + Next.js build + regression gate |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Next.js Frontend                     │
│  Dashboard · Experiments · Injection Runner              │
│  React Query · Recharts · Tailwind CSS                   │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP (NEXT_PUBLIC_API_URL)
┌─────────────────────▼───────────────────────────────────┐
│                    FastAPI Backend                        │
│                                                          │
│  /api/v1/evals        RAGAS + injection + trust score    │
│  /api/v1/injection    Standalone injection test suite    │
│  /api/v1/agents       ReAct / Plan-Execute agent runner  │
│  /api/v1/experiments  CRUD — persist & retrieve results  │
│  /api/v1/datasets     Upload evaluation datasets         │
└──────┬──────────────────────┬───────────────────────────┘
       │                      │
┌──────▼──────┐     ┌─────────▼──────────┐
│   SQLite /  │     │   Ollama           │
│  Postgres   │     │   llama3.1:8b      │
│  (results)  │     │   (LLM + embeddings│
└─────────────┘     └────────────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.com/download) running locally

```bash
# Pull the model (one-time, ~4.7 GB)
ollama pull llama3.1:8b
ollama serve
```

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env          # edit if needed
uvicorn app.main:app --reload
# API docs: http://localhost:8000/docs
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# Dashboard: http://localhost:3000
```

### 3. Docker Compose (full stack)

```bash
cp .env.example backend/.env
docker compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000/docs
```

---

## Running the Tests

```bash
cd backend
source .venv/bin/activate
pytest -v
# 69 tests, ~2 seconds, no Ollama required
```

---

## API Usage Examples

### Run a full RAG evaluation

```bash
curl -s -X POST http://localhost:8000/api/v1/evals/run \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_name": "my-first-eval",
    "model_name": "llama3.1:8b",
    "agent_type": "rag",
    "run_injection": true,
    "samples": [
      {
        "question": "What is the capital of France?",
        "contexts": ["France is a country in Western Europe. Its capital is Paris."],
        "answer": "The capital of France is Paris.",
        "ground_truth": "Paris"
      }
    ]
  }' | python -m json.tool
```

**Response:**
```json
{
  "experiment_id": 1,
  "results": {
    "ragas": {
      "faithfulness": 0.95,
      "answer_relevancy": 0.92,
      "factual_correctness": 0.88
    },
    "injection": {
      "injection_rate": 0.08,
      "robustness": 0.92
    },
    "trustworthiness": 0.83,
    "grade": "B — Needs Monitoring"
  }
}
```

### Run injection tests only

```bash
curl -s -X POST http://localhost:8000/api/v1/injection/run \
  -H "Content-Type: application/json" \
  -d '{"model_name": "llama3.1:8b"}' | python -m json.tool
```

### Ask a LangGraph agent

```bash
curl -s -X POST http://localhost:8000/api/v1/agents/run \
  -H "Content-Type: application/json" \
  -d '{"question": "What is 25 * 48?", "agent_type": "react"}' | python -m json.tool
```

---

## Trustworthiness Score

```
trustworthiness = 0.50 × faithfulness
               + 0.20 × factual_correctness
               + 0.30 × (1 − injection_rate)
```

| Score | Grade | Meaning |
|---|---|---|
| ≥ 0.85 | A | Production Ready |
| ≥ 0.70 | B | Needs Monitoring |
| ≥ 0.55 | C | Needs Work |
| < 0.55 | D | Not Production Safe |

---

## Project Structure

```
evalforge/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, CORS, lifespan
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   ├── schemas.py            # Pydantic request/response schemas
│   │   ├── database.py           # Engine, SessionLocal, Base
│   │   ├── routers/              # evals, agents, datasets, experiments, injection
│   │   └── services/
│   │       ├── ragas_service.py       # RAGAS evaluation (6 metrics)
│   │       ├── eval_service.py        # Trustworthiness composite + grade
│   │       ├── injection_service.py   # Attack patterns + regex detection
│   │       ├── react_agent.py         # LangGraph ReAct agent
│   │       ├── plan_execute_agent.py  # LangGraph Plan-Execute agent
│   │       ├── agent_tools.py         # calculator, date, search tools
│   │       └── langsmith_service.py   # Optional LangSmith tracking
│   ├── tests/                    # 69 tests, fully mocked, offline
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js App Router pages
│   │   │   ├── page.tsx              # Dashboard (live KPIs)
│   │   │   ├── experiments/          # List + detail with RAGAS chart
│   │   │   └── injection/            # Injection test runner UI
│   │   ├── components/           # NavBar, TrustBadge, MetricBar, StatCard
│   │   └── lib/                  # api.ts (Axios), queryClient.ts
│   ├── Dockerfile
│   └── next.config.ts
├── scripts/
│   └── check_regression.py       # CI regression gate
├── .github/
│   └── workflows/
│       └── ci.yml                # 3-job pipeline: tests + lint/build + gate
├── docker-compose.yml
├── railway.toml                  # Backend deploy config (Railway)
├── vercel.json                   # Frontend deploy config (Vercel)
└── .env.example
```

---

## CI Pipeline

Three jobs run on every push to `main`/`develop` and on every PR:

```
push / PR
  ├── backend-tests  (Python 3.11)  — pytest 69 tests, ~2s
  │   └── uploads pytest-report.json
  ├── frontend-ci    (Node 20)      — eslint + next build
  └── regression-gate               — fails if pass rate < 100%
                                      or test count < 69
```

---

## Deployment

### Backend → Railway

1. Push repo to GitHub
2. Create new Railway project → **Deploy from GitHub repo**
3. Railway reads `railway.toml` and builds `backend/Dockerfile`
4. Set environment variables in Railway dashboard:

| Variable | Value |
|---|---|
| `DATABASE_URL` | PostgreSQL URL from Railway Postgres add-on |
| `OLLAMA_BASE_URL` | URL of your hosted Ollama instance |
| `ALLOWED_ORIGINS` | `https://your-app.vercel.app` |

### Frontend → Vercel

1. `npm i -g vercel && vercel --cwd frontend`
2. Set environment variable in Vercel dashboard:
   - `NEXT_PUBLIC_API_URL` = `https://your-backend.railway.app`

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Ollama (`llama3.1:8b`) via `langchain-ollama` |
| RAG Evaluation | RAGAS 0.2.x |
| Agent Framework | LangGraph (ReAct + Plan-Execute) |
| Experiment Tracking | LangSmith (optional) |
| Backend | FastAPI + SQLAlchemy + SQLite/Postgres |
| Frontend | Next.js 16 + React Query + Recharts + Tailwind CSS |
| CI | GitHub Actions |
| Containers | Docker + Docker Compose |
| Deployment | Railway (backend) + Vercel (frontend) |
