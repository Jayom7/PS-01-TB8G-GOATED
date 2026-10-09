-- Metadata-only, server-written events. Clients cannot forge audit history.
create table public.security_events (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id),
  user_id uuid not null references auth.users(id) on delete cascade,
  active_role text not null,
  kind text not null,
  outcome text not null,
  evidence_count integer check (evidence_count is null or evidence_count >= 0),
  source_id uuid,
  created_at timestamptz not null default now()
);
create index security_events_actor on public.security_events(user_id, organization_id, active_role, created_at desc);
alter table public.security_events enable row level security;
create policy security_events_read_self on public.security_events for select to authenticated using (
  user_id = (select auth.uid()) and organization_id = (select organization_id from public.profiles where user_id = (select auth.uid()))
);
revoke all on public.security_events from anon, authenticated;
grant select on public.security_events to authenticated;
grant all on public.security_events to service_role;

-- Files cannot share a database transaction: durable cleanup intent survives restart.
create table public.source_cleanup_jobs (
  source_id uuid primary key,
  storage_path text,
  state text not null default 'pending' check (state in ('pending', 'complete')),
  created_at timestamptz not null default now()
);
alter table public.source_cleanup_jobs enable row level security;
revoke all on public.source_cleanup_jobs from anon, authenticated;
grant all on public.source_cleanup_jobs to service_role;

create function public.delete_local_source(target_source uuid, target_org uuid, actor uuid)
returns jsonb language plpgsql security invoker set search_path = public, pg_temp as $$
declare doc public.documents;
begin
  -- Only the API's local administrative path has EXECUTE permission.
  if not exists (select 1 from public.profiles p join public.user_roles ur on ur.user_id=p.user_id and ur.organization_id=p.organization_id join public.roles r on r.id=ur.role_id and r.organization_id=p.organization_id where p.user_id=actor and p.organization_id=target_org and r.name='CEO') then
    raise insufficient_privilege using message='Administrative identity required';
  end if;
  select * into doc from public.documents where id=target_source and organization_id=target_org for update;
  if not found then return null; end if;
  insert into public.source_cleanup_jobs(source_id, storage_path) values(doc.id, doc.storage_path);
  -- Existing ON DELETE CASCADE removes chunks, grants and typed origin rows.
  -- Referenced business parents intentionally fail the entire transaction.
  delete from public.documents where id=target_source and organization_id=target_org;
  insert into public.security_events(organization_id,user_id,active_role,kind,outcome,source_id)
    values(target_org,actor,'CEO','source_delete','deleted',target_source);
  return jsonb_build_object('storage_path',doc.storage_path);
end $$;
revoke all on function public.delete_local_source(uuid,uuid,uuid) from public, anon, authenticated;
grant execute on function public.delete_local_source(uuid,uuid,uuid) to service_role;
