-- Preserve invoker RLS; exact invoice queries search only authorized matching documents.
-- Zero full-text matches must not receive an arbitrary reciprocal-rank bonus.
create or replace function public.match_knowledge_chunks(
  query_embedding extensions.vector(1536),
  query_text text,
  match_count integer default 12
)
returns table (
  chunk_id uuid,
  document_id uuid,
  source_type public.source_type,
  source_name text,
  source_id text,
  page_number integer,
  row_id text,
  image_id text,
  ocr_region jsonb,
  content text,
  metadata jsonb,
  semantic_score real,
  keyword_score real
)
language sql
stable
security invoker
set search_path = ''
as $$
  with query_ids as (
    select lower(m[1]) as identifier
    from regexp_matches(query_text, '\m((?:[A-Z0-9]+-)?INV-[0-9]+)\M', 'gi') m
  ), identifier_documents as (
    -- Both this identity lookup and candidate retrieval run under caller RLS.
    select distinct k.document_id
    from public.knowledge_chunks k
    where exists (
      select 1 from query_ids q
      where lower(k.content || ' ' || coalesce(k.row_id, '') || ' ' || k.source_name)
        ~ ('(^|[^a-z0-9-])' || q.identifier || '([^a-z0-9-]|$)')
    )
  ), candidates as (
    select
      k.id, k.document_id, k.source_type, k.source_name, k.source_id,
      k.page_number, k.row_id, k.image_id, k.ocr_region, k.content, k.metadata,
      (1 - (k.embedding operator(extensions.<=>) query_embedding))::real as semantic_score,
      ts_rank_cd(k.search_vector, websearch_to_tsquery('english'::regconfig, query_text))::real as keyword_score
    from public.knowledge_chunks k
    where k.embedding is not null
      and (
        (not exists (select 1 from query_ids) and (
        k.embedding operator(extensions.<=>) query_embedding < 0.75
        or k.search_vector @@ websearch_to_tsquery('english'::regconfig, query_text)
        ))
        or k.document_id in (select document_id from identifier_documents)
      )
  ), ranked as (
    select c.*,
      row_number() over (order by c.semantic_score desc, c.id) as semantic_rank,
      row_number() over (order by c.keyword_score desc, c.id) as keyword_rank
    from candidates c
  )
  select c.id, c.document_id, c.source_type, c.source_name, c.source_id,
    c.page_number, c.row_id, c.image_id, c.ocr_region, c.content, c.metadata,
    c.semantic_score, c.keyword_score
  from ranked c
  order by (1.0 / (60 + c.semantic_rank)) + (case when c.keyword_score > 0 then 1.0 / (60 + c.keyword_rank) else 0 end) desc, c.id
  limit greatest(1, least(match_count, 50));
$$;

