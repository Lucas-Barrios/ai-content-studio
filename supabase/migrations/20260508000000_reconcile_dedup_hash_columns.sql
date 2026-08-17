-- ════════════════════════════════════════════════════════════════════════════
-- Reconcile deployed schema with migration files.
--
-- The base schema migration (20260505120000) was applied to the remote database
-- in an earlier form, then later edited to add the dedup/idempotency hash columns
-- (uploaded_documents.content_hash, document_chunks.chunk_hash) and their unique
-- indexes. Because the remote already marks the base migration as applied, those
-- columns/indexes never landed there, so RAG ingestion failed at the dedup lookup
-- ("column uploaded_documents.content_hash does not exist").
--
-- This forward migration adds them idempotently:
--   * against the drifted remote -> adds the missing columns + indexes
--   * against a fresh db (base migration already creates them) -> all no-ops
--
-- Note: chunk_hash is defined NOT NULL in the base schema; it is added here as
-- nullable to stay safe on any pre-existing rows. The app always populates it,
-- and the unique index below provides the integrity guarantee.
-- ════════════════════════════════════════════════════════════════════════════

alter table public.uploaded_documents add column if not exists content_hash text;
alter table public.document_chunks    add column if not exists chunk_hash   text;

create unique index if not exists uploaded_documents_content_hash_idx
  on public.uploaded_documents (
    client_id,
    coalesce(project_id, '00000000-0000-0000-0000-000000000000'::uuid),
    content_hash
  )
  where content_hash is not null;

create unique index if not exists document_chunks_hash_idx
  on public.document_chunks (document_id, chunk_hash);
