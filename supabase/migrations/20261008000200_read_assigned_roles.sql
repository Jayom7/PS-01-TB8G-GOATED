-- Let authenticated callers resolve their own role names for the workspace UI.
-- The policy reveals no role unless the caller has a matching assignment.
create policy "roles_read_assigned" on public.roles
  for select to authenticated using (
    exists (
      select 1 from public.user_roles ur
      where ur.user_id = (select auth.uid()) and ur.role_id = roles.id
    )
  );

grant select on public.roles to authenticated;
