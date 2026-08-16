# AI Content Studio

A production-oriented AI marketing content workspace for generating brand-conditioned content across channels. The system combines a Next.js frontend, a FastAPI backend, OpenAI generation, optional Supabase persistence, RAG ingestion, brand profiles, campaign generation, content repurposing, feedback capture, and a feature-flagged TypeScript prompt framework.

## Start Here

- **Project scope:** [`docs/project_scope_delivery_plan.md`](docs/project_scope_delivery_plan.md)
- **Supabase setup:** [`docs/supabase_setup.md`](docs/supabase_setup.md)

## Architecture

```txt
Next.js frontend
  -> Next.js API routes
  -> FastAPI Python backend
  -> generation, RAG, campaign, repurpose, brand, feedback services
  -> OpenAI + Supabase Postgres/pgvector
```

| Area | Key Files |
|---|---|
| Frontend app | `frontend/app/*`, `frontend/components/*` |
| Frontend API proxy | `frontend/app/api/*` |
| TS prompt framework | `frontend/lib/ai/*`, `frontend/lib/generation/*` |
| Python API | `api_server.py` |
| Core generation | `src/generation_service.py`, `src/content_pipeline.py`, `src/prompt_templates.py` |
| OpenAI wrapper | `src/llm_integration.py` |
| RAG ingestion | `src/rag_ingestion.py` |
| Campaigns | `src/campaign_service.py`, `src/campaign_prompt_templates.py` |
| Repurposing | `src/repurpose_service.py`, `src/repurpose_prompt_templates.py` |
| Supabase schema | `supabase/migrations/*` |

## Prerequisites

- Python 3.10+
- Node.js 20+
- npm
- OpenAI API key
- Optional: Supabase project with the migrations in `supabase/migrations/`

## 1. Backend Setup

From the project root:

```bash
cd /Users/lucas/Desktop/Ironhack_labs/AI_content_creator_system/ai-content-creator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# Optional but needed for Supabase-backed RAG, campaigns, assets, and saved outputs
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Optional local API protection. If set, frontend PYTHON_API_KEY must match.
BACKEND_API_KEY=
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

For local development, you may leave `BACKEND_API_KEY` empty. For production, set a long random value.

Start the backend:

```bash
uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
```

Backend health check:

```bash
curl http://127.0.0.1:8000/health
```

## 2. Frontend Setup

Open a second terminal:

```bash
cd /Users/lucas/Desktop/Ironhack_labs/AI_content_creator_system/ai-content-creator/frontend
npm install
cp .env.example .env.local
```

Edit `frontend/.env.local`:

```env
PYTHON_API_BASE_URL=http://localhost:8000

# Only set this if BACKEND_API_KEY is set in backend .env
PYTHON_API_KEY=

ENABLE_TS_PROMPT_FRAMEWORK=false
TS_PROMPT_FRAMEWORK_MODE=social_only
TS_PROMPT_AB_TEST=false

# Optional browser-safe Supabase values
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your_publishable_or_anon_key_here
```

Start the frontend:

```bash
npm run dev
```

Open:

```txt
http://localhost:3000
```

Useful pages:

```txt
http://localhost:3000/generator
http://localhost:3000/dashboard
http://localhost:3000/campaigns
http://localhost:3000/knowledge-base
http://localhost:3000/repurpose
http://localhost:3000/assets
http://localhost:3000/settings
```

## TypeScript Prompt Framework

The new prompt framework is wired into real generation behind feature flags. It is rollback-safe and falls back to the Python backend if unsupported or if the framework fails.

Enable it in `frontend/.env.local`:

```env
ENABLE_TS_PROMPT_FRAMEWORK=true
TS_PROMPT_FRAMEWORK_MODE=social_only
TS_PROMPT_AB_TEST=false
```

Modes:

- `social_only`: routes `social` / `social_post` through the TS prompt framework.
- `supported`: routes social, email/newsletter, and ad/ad_copy.
- `all`: reserved for future expansion.

See:

- `docs/prompt_engineering_framework.md`
- `docs/ts_prompt_framework_migration.md`
- `docs/uniqueness_evidence_demo.md`

## Supabase Setup

The database schema is in:

```txt
supabase/migrations/
```

Core capabilities covered by the schema:

- organizations, clients, projects
- brand profiles
- uploaded documents and chunks
- pgvector embeddings
- content briefs
- generated outputs
- campaigns and calendar items
- feedback and output versions

Setup notes:

- Apply migrations in timestamp order.
- Use the service role key only in backend `.env`.
- Use only publishable/browser-safe keys in `frontend/.env.local`.
- Never commit real `.env` files.

More detail:

- `docs/project_scope_delivery_plan.md`
- `docs/supabase_setup.md`
- `docs/database_schema.md`
- `docs/rag_ingestion.md`

## Common Commands

Backend checks:

```bash
PYTHONPYCACHEPREFIX=/private/tmp python3 -m py_compile api_server.py src/*.py
python3 test_security.py
python3 test_openai_wrapper.py
python3 test_rag_ingestion.py
```

Frontend checks:

```bash
cd frontend
npm run typecheck
npm run lint
npm run build
```

CLI generation:

```bash
python main.py --type blog --topic "Evidence-based investing"
python main.py --type social --topic "Open Day June 2026" --extra "Join us 14 June in Berlin"
python main.py --type program --topic "MSc Applied Data Science and AI"
python main.py --type newsletter --topic "April Campus Updates"
```

## API Overview

Backend endpoints include:

- `GET /health`
- `POST /generate`
- `POST /llm/generate`
- `POST /upload`
- `POST /knowledge/ingest-text`
- `POST /knowledge/ingest-file`
- `POST /knowledge/search`
- `GET /brand-profile`
- `POST /brand-profile`
- `POST /campaigns/generate`
- `POST /repurpose`
- `GET /generated-outputs`
- `POST /generated-outputs`
- `POST /feedback`
- `POST /chat`
- `POST /chat/stream`
- `POST /compare`
- `POST /export/docx`

Frontend API routes proxy to the backend through `PYTHON_API_BASE_URL`.

## Troubleshooting

### Port 8000 is already in use

```bash
lsof -ti tcp:8000
kill <PID>
```

Then restart:

```bash
uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
```

### Port 3000 is already in use

```bash
lsof -ti tcp:3000
kill <PID>
```

Then restart:

```bash
cd frontend
npm run dev
```

### Frontend cannot reach backend

Check `frontend/.env.local`:

```env
PYTHON_API_BASE_URL=http://localhost:8000
```

Restart the frontend after changing env vars.

### API key errors

If `BACKEND_API_KEY` is set in `.env`, then `PYTHON_API_KEY` in `frontend/.env.local` must match it.

### Supabase errors

Confirm backend `.env` has:

```env
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```

Confirm frontend `.env.local` has only browser-safe values:

```env
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=...
```

## Project Structure

```txt
ai-content-creator/
├── README.md
├── api_server.py
├── frontend/
│   ├── app/
│   ├── components/
│   └── lib/
│       ├── ai/
│       ├── generation/
│       └── api-client.ts
├── src/
├── docs/
├── knowledge_base/
│   ├── primary/
│   └── secondary/
├── supabase/
│   └── migrations/
├── examples/
├── requirements.txt
└── .env.example
```

This structure keeps the repository entry points at the root, product/technical documentation in `docs/`, frontend code in `frontend/`, backend code in `src/` plus `api_server.py`, and database migrations in `supabase/migrations/`.
