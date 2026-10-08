-- Unified retrieval index foundation. The normal query path is user-scoped:
-- match_knowledge_chunks is SECURITY INVOKER and therefore respects RLS.
create extension if not exists vector with schema extensions;
create extension if not exists pgcrypto with schema extensions;

create type public.source_type as enum ('pdf', 'image_ocr', 'structured');
create type public.access_principal_type as enum ('user', 'role', 'organization');

create table public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

create table public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  organization_id uuid not null references public.organizations(id),
  display_name text not null,
  created_at timestamptz not null default now()
);

create table public.roles (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  name text not null,
  unique (organization_id, name),
  unique (id, organization_id)
);

create table public.user_roles (
  user_id uuid not null references auth.users(id) on delete cascade,
  role_id uuid not null references public.roles(id) on delete cascade,
  organization_id uuid not null references public.organizations(id) on delete cascade,
  primary key (user_id, role_id),
  foreign key (role_id, organization_id) references public.roles(id, organization_id) on delete cascade
);

create table public.documents (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  source_type public.source_type not null,
  source_name text not null,
  storage_path text,
  content_hash text,
  metadata jsonb not null default '{}'::jsonb,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  unique (organization_id, content_hash)
);

create table public.knowledge_chunks (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  document_id uuid not null references public.documents(id) on delete cascade,
  source_type public.source_type not null,
  source_name text not null,
  source_id text not null,
  page_number integer,
  row_id text,
  image_id text,
  ocr_region jsonb,
  chunk_index integer not null default 0,
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  search_vector tsvector generated always as (to_tsvector('english'::regconfig, content)) stored,
  embedding extensions.vector(1536),
  created_at timestamptz not null default now(),
  unique (document_id, chunk_index)
);

create table public.access_grants (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  document_id uuid references public.documents(id) on delete cascade,
  chunk_id uuid references public.knowledge_chunks(id) on delete cascade,
  principal_type public.access_principal_type not null,
  principal_id uuid not null,
  can_read boolean not null default true,
  created_at timestamptz not null default now(),
  constraint grant_targets_one_scope check (num_nonnulls(document_id, chunk_id) = 1)
);

create index knowledge_chunks_embedding_hnsw
  on public.knowledge_chunks using hnsw (embedding extensions.vector_cosine_ops)
  with (m = 16, ef_construction = 64);
create index knowledge_chunks_search_gin on public.knowledge_chunks using gin (search_vector);
create index knowledge_chunks_org_type on public.knowledge_chunks (organization_id, source_type);
create index access_grants_principal on public.access_grants (principal_type, principal_id, organization_id)
  where can_read;
create index access_grants_document on public.access_grants (document_id) where can_read;
create index access_grants_chunk on public.access_grants (chunk_id) where can_read;

alter table public.profiles enable row level security;
alter table public.user_roles enable row level security;
alter table public.organizations enable row level security;
alter table public.roles enable row level security;
alter table public.documents enable row level security;
alter table public.knowledge_chunks enable row level security;
alter table public.access_grants enable row level security;

create policy "profiles_read_self" on public.profiles
  for select to authenticated using (user_id = (select auth.uid()));
create policy "user_roles_read_self" on public.user_roles
  for select to authenticated using (user_id = (select auth.uid()));

-- Grant rows are visible only when they apply to the caller. This supports invoker RLS checks
-- without broad grant metadata access.
create policy "access_grants_read_applicable" on public.access_grants
  for select to authenticated using (
    can_read and (
      (principal_type = 'user' and principal_id = (select auth.uid()))
      or (principal_type = 'role' and exists (
        select 1 from public.user_roles ur
        where ur.user_id = (select auth.uid()) and ur.role_id = access_grants.principal_id
      ))
      or (principal_type = 'organization' and exists (
        select 1 from public.profiles p
        where p.user_id = (select auth.uid()) and p.organization_id = access_grants.principal_id
      ))
    )
  );

create policy "documents_read_authorized" on public.documents
  for select to authenticated using (
    organization_id = (select p.organization_id from public.profiles p
      where p.user_id = (select auth.uid()))
    and exists (
      select 1 from public.access_grants g
      where g.document_id = documents.id and g.organization_id = documents.organization_id
    )
  );

create policy "chunks_read_authorized" on public.knowledge_chunks
  for select to authenticated using (
    organization_id = (select p.organization_id from public.profiles p
      where p.user_id = (select auth.uid()))
    and (
      exists (
        select 1 from public.access_grants g
        where g.chunk_id = knowledge_chunks.id and g.organization_id = knowledge_chunks.organization_id
      )
      or exists (
        select 1 from public.access_grants g
        where g.document_id = knowledge_chunks.document_id
          and g.organization_id = knowledge_chunks.organization_id
      )
    )
  );

grant usage on schema public to authenticated;
revoke all on public.organizations, public.roles, public.profiles,
  public.user_roles, public.documents, public.knowledge_chunks,
  public.access_grants from anon, authenticated;
grant select on public.profiles, public.user_roles, public.documents,
  public.knowledge_chunks, public.access_grants to authenticated;

-- RLS applies inside this invoker function before rows can be returned to the API or LLM.
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
  with candidates as (
    select
      k.id, k.document_id, k.source_type, k.source_name, k.source_id,
      k.page_number, k.row_id, k.image_id, k.ocr_region, k.content, k.metadata,
      (1 - (k.embedding operator(extensions.<=>) query_embedding))::real as semantic_score,
      ts_rank_cd(k.search_vector, websearch_to_tsquery('english'::regconfig, query_text))::real as keyword_score
    from public.knowledge_chunks k
    where k.embedding is not null
      and (
        k.embedding operator(extensions.<=>) query_embedding < 0.75
        or k.search_vector @@ websearch_to_tsquery('english'::regconfig, query_text)
      )
  ), ranked as (
    select c.*,
      row_number() over (order by c.semantic_score desc) as semantic_rank,
      row_number() over (order by c.keyword_score desc) as keyword_rank
    from candidates c
  )
  select c.id, c.document_id, c.source_type, c.source_name, c.source_id,
    c.page_number, c.row_id, c.image_id, c.ocr_region, c.content, c.metadata,
    c.semantic_score, c.keyword_score
  from ranked c
  order by (1.0 / (60 + c.semantic_rank)) + (1.0 / (60 + c.keyword_rank)) desc
  limit greatest(1, least(match_count, 50));
$$;

revoke all on function public.match_knowledge_chunks(extensions.vector, text, integer) from public;
revoke all on function public.match_knowledge_chunks(extensions.vector, text, integer) from anon, authenticated;
grant execute on function public.match_knowledge_chunks(extensions.vector, text, integer) to authenticated;
