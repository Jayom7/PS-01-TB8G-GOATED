-- Reuse the durable audit boundary; manifest details are server-only. Actor
-- reads retain the existing self/org RLS and public metadata columns.
alter table public.security_events add column details jsonb;
revoke select on public.security_events from authenticated;
grant select (id, organization_id, user_id, active_role, kind, outcome,
              evidence_count, source_id, created_at)
  on public.security_events to authenticated;
comment on column public.security_events.details is
  'Server-only evidence manifest: exact outbound IDs/hash, context, attempt and validation outcomes; no evidence bodies or tokens';
