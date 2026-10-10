-- Private originals persist across free-service restarts. No client object
-- policies are added: the API checks the current document grant under caller
-- RLS before its server-only storage read. Never make this bucket public.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('clearframe-originals', 'clearframe-originals', false, 26214400,
        array['application/pdf', 'image/png', 'image/jpeg'])
on conflict (id) do nothing;

-- Fail safely if an existing bucket with this name is public or misconfigured.
do $$ begin
  if exists (select 1 from storage.buckets where id = 'clearframe-originals'
             and (public or file_size_limit is distinct from 26214400
                  or allowed_mime_types is distinct from
                     array['application/pdf', 'image/png', 'image/jpeg'])) then
    raise exception 'Review the existing clearframe-originals bucket configuration';
  end if;
end $$;
