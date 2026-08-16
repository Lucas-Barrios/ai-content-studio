# Supabase Workspace Setup

This project is prepared to connect to Supabase without committing secrets.

## Available Projects

The workspace is being connected to this target project:

| Name | Project URL | Project ref |
| --- | --- | --- |
| Target project | `https://afjfbvmtdukyjcpuudcl.supabase.co` | `afjfbvmtdukyjcpuudcl` |

The Codex Supabase connector currently does not have permission to manage this project. Add access for the connected Supabase account or apply the migration manually through the Supabase dashboard.

The connected Supabase account can also see these active projects:

| Name | Project ref | Region |
| --- | --- | --- |
| New_Kairos | `vjyjunuxefmegudwugax` | `eu-west-3` |
| Kairos Consulting Project | `gsvjhyysohqugkajzkxc` | `eu-west-1` |

Confirm the target project before applying migrations.

## Environment Variables

Backend `.env`:

```bash
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
```

Frontend `frontend/.env.local`:

```bash
PYTHON_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=AI Content Studio
NEXT_PUBLIC_SUPABASE_URL=https://afjfbvmtdukyjcpuudcl.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your_publishable_or_anon_key_here
```

The publishable/anon key can be used in the browser with RLS enabled.
The service role key must stay server-only.

## Migration

The initial schema migration is:

```bash
supabase/migrations/20260505120000_ai_marketing_content_schema.sql
```

It creates the multi-tenant SaaS schema, enables pgvector, adds indexes, row-level security, and the similarity-search RPC.

## Apply Options

Option A: Apply through the Supabase dashboard SQL editor.

1. Open the target Supabase project.
2. Go to SQL Editor.
3. Paste the contents of `supabase/migrations/20260505120000_ai_marketing_content_schema.sql`.
4. Run it.

Option B: Apply through Codex MCP after you confirm the project ref.

Use one of:

```text
vjyjunuxefmegudwugax
gsvjhyysohqugkajzkxc
```

## To Be

- Add Supabase Storage buckets for uploaded knowledge documents and brand assets.
- Add an ingestion worker that parses uploads into `document_chunks`.
- Add an embedding worker that writes `document_embeddings`.
- Replace local JSONL feedback storage with inserts into `feedback_events`.
- Replace browser localStorage history with reads from `generated_outputs`.
