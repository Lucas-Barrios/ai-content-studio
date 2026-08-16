-- ════════════════════════════════════════════════════════════════════════════
-- Demo workspace seed — two contrasting regulated tenants under one agency org.
--
-- Northlight Studio (demo AI-content agency)
--   ├── Meridian Wealth      (fintech / wealth advisory — financial-promotion rules)
--   └── Lumen Aesthetics     (aesthetics clinic — medical-advertising rules)
--
-- The two tenants have different regulatory regimes and opposite banned-term
-- sets, which is what demonstrates per-client brand isolation and the guardrail
-- layer generalising across compliance contexts.
--
-- UUIDs for Meridian (client/project 0002/0003) match defaultWorkspace in
-- frontend/lib/workspace.ts so the demo loads Meridian by default.
-- Knowledge-base documents are ingested via the RAG pipeline at demo setup
-- (embeddings require the OpenAI key at ingest time); this seed provisions the
-- tenant structure and brand profiles only.
-- ════════════════════════════════════════════════════════════════════════════

-- ── 1. Agency organisation ──────────────────────────────────────────────────
insert into public.organizations (id, name, slug, plan)
values ('00000000-0000-0000-0000-000000000001', 'Northlight Studio', 'northlight-studio', 'pro')
on conflict (id) do nothing;

-- ── 2. Clients ──────────────────────────────────────────────────────────────
insert into public.clients (id, organization_id, name, slug, industry)
values
  ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001',
   'Meridian Wealth', 'meridian-wealth', 'Financial Services'),
  ('00000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000001',
   'Lumen Aesthetics', 'lumen-aesthetics', 'Health & Aesthetics')
on conflict (id) do nothing;

-- ── 3. Projects ─────────────────────────────────────────────────────────────
insert into public.projects (id, organization_id, client_id, name, slug, objective, default_language)
values
  ('00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000001',
   '00000000-0000-0000-0000-000000000002', 'Meridian Wealth — Marketing', 'meridian-marketing',
   'Compliant client-facing content for a DACH wealth advisory', 'english'),
  ('00000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000001',
   '00000000-0000-0000-0000-000000000004', 'Lumen Aesthetics — Marketing', 'lumen-marketing',
   'Compliant, consent-first content for a Berlin aesthetics clinic', 'english')
on conflict (id) do nothing;

-- ── 4. Brand profiles ───────────────────────────────────────────────────────
insert into public.brand_profiles (
  id, organization_id, client_id, project_id, name, positioning, voice,
  tone_guidelines, audience_summary, approved_terms, banned_terms,
  compliance_notes, brand_values, is_default
)
values
  (
    '00000000-0000-0000-0000-0000000000a1',
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000003',
    'Meridian Wealth — Default',
    'Boutique DACH wealth advisory competing on rigor and transparency, not performance claims. The promise is clarity: clients always understand what they own and why.',
    'Precise, sober, evidence-led, candid about risk. Confident without being promotional.',
    'Every claim backed by a mechanism or source. Downside stated plainly. No hype adjectives.',
    'Private clients (EUR 500k–5m), family offices, and professionals near retirement — financially literate, time-poor, skeptical of hype.',
    array['diversified','evidence-based','disciplined','long-term','risk-adjusted','capital preservation','suitability','time horizon','rebalancing','historically','may'],
    array['guaranteed','guarantee','risk-free','no risk','safe returns','beat the market','outperform the market','sure thing','can''t lose','double your money','get rich','high returns'],
    'Financial promotion. Past performance is not a reliable indicator of future results. Value can fall as well as rise; investors may get back less than invested. Marketing only, not personal advice — suitability requires a documented assessment. No unqualified return promises; no comparative superiority without a dated cited source.',
    array['transparency','discipline','candor','client alignment'],
    true
  ),
  (
    '00000000-0000-0000-0000-0000000000a2',
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005',
    'Lumen Aesthetics — Default',
    'Physician-led Berlin aesthetics clinic competing on clinical credibility and honesty, not dramatic transformation promises. The promise is confidence through care, not perfection.',
    'Warm, reassuring, consent-first, plain-language. Honest about limits; never salesy or clinical-cold.',
    'State what a treatment cannot do as clearly as what it can. Every treatment reference routes to a consultation, not a booking impulse.',
    'Adults 30–55 considering their first non-surgical treatment, often anxious about looking overdone, plus maintenance clients and referrals.',
    array['qualified practitioner','consultation','individual assessment','natural-looking','may help','temporary','results vary','aftercare','suitability','realistic expectations','medically supervised'],
    array['cure','cures','permanent','permanent results','100% safe','no side effects','risk-free','completely painless','guaranteed results','flawless','perfect','miracle','instant'],
    'Health-adjacent marketing under German medical-advertising principles (HWG). No misleading or guaranteed outcome claims; results are temporary and vary. Never deny or trivialize side effects. Never present an aesthetic treatment as curing or treating a diagnosed condition. Suitability determined only at an individual medical consultation. No fear- or shame-based framing.',
    array['clinical credibility','honesty','patient care','consent'],
    true
  )
on conflict (id) do nothing;


-- ── 5. Preserve service-role access for match_document_chunks ────────────────
-- Carried forward from the previous seed. The base WHERE clause calls
-- is_organization_member(org_id), which checks auth.uid(). When the Python
-- backend uses the service-role key, auth.uid() is NULL and the function
-- returns zero rows. Allow the query when the caller holds the service_role
-- JWT claim so the backend RAG pipeline can retrieve chunks server-side.

create or replace function public.match_document_chunks(
  query_embedding extensions.vector(1536),
  match_count integer default 8,
  match_threshold double precision default 0.72,
  filter_client_id uuid default null,
  filter_project_id uuid default null,
  filter_content_type public.content_type default null,
  filter_language text default null,
  filter_channel public.content_channel default null
)
returns table (
  chunk_id uuid,
  document_id uuid,
  client_id uuid,
  project_id uuid,
  title text,
  content text,
  source_kind public.source_kind,
  content_type public.content_type,
  language text,
  channel public.content_channel,
  tags text[],
  similarity double precision
)
language sql
stable
as $fn$
  select
    dc.id as chunk_id,
    dc.document_id,
    dc.client_id,
    dc.project_id,
    ud.title,
    dc.content,
    dc.source_kind,
    dc.content_type,
    dc.language,
    dc.channel,
    dc.tags,
    1 - (de.embedding <=> query_embedding) as similarity
  from public.document_embeddings de
  join public.document_chunks dc on dc.id = de.chunk_id
  join public.uploaded_documents ud on ud.id = dc.document_id
  where
    (
      coalesce(current_setting('request.jwt.claims', true)::jsonb->>'role', '') = 'service_role'
      or public.is_organization_member(dc.organization_id)
    )
    and (filter_client_id  is null or dc.client_id     = filter_client_id)
    and (filter_project_id is null or dc.project_id    = filter_project_id)
    and (filter_content_type is null or dc.content_type = filter_content_type)
    and (filter_language   is null or dc.language      = filter_language)
    and (filter_channel    is null or dc.channel       = filter_channel)
    and 1 - (de.embedding <=> query_embedding) >= match_threshold
  order by de.embedding <=> query_embedding
  limit least(match_count, 30)
$fn$;
