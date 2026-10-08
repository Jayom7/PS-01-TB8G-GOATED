-- Relational origin for structured evidence and identity-scoped conversation history.
-- Additive only. Apply locally with `supabase migration up --local`; never reset.
alter table public.documents add constraint documents_id_organization_unique unique(id, organization_id);
alter table public.knowledge_chunks add constraint chunks_document_organization_fk
  foreign key (document_id, organization_id) references public.documents(id, organization_id) on delete cascade;

create table public.customers (
  organization_id uuid not null references public.organizations(id),
  customer_id text not null,
  document_id uuid not null,
  name text not null, status text not null, contract_id text, payment_terms text,
  primary key (organization_id, customer_id),
  foreign key (document_id, organization_id) references public.documents(id, organization_id) on delete cascade
);
alter table public.customers enable row level security;
create policy "customers_read_authorized" on public.customers for select to authenticated using (
  exists (select 1 from public.documents d where d.id = customers.document_id and d.organization_id = customers.organization_id)
);
revoke all on public.customers from anon, authenticated;
grant select on public.customers to authenticated;
grant all on public.customers to service_role;

create table public.projects (
  organization_id uuid not null references public.organizations(id),
  project_id text not null,
  document_id uuid not null,
  name text not null, release text, status text not null, owner_team text,
  primary key (organization_id, project_id),
  foreign key (document_id, organization_id) references public.documents(id, organization_id) on delete cascade
);
alter table public.projects enable row level security;
create policy "projects_read_authorized" on public.projects for select to authenticated using (
  exists (select 1 from public.documents d where d.id = projects.document_id and d.organization_id = projects.organization_id)
);
revoke all on public.projects from anon, authenticated;
grant select on public.projects to authenticated;
grant all on public.projects to service_role;

create table public.employees (
  organization_id uuid not null references public.organizations(id),
  employee_id text not null,
  document_id uuid not null,
  role text not null, annual_salary_minor_units bigint check (annual_salary_minor_units >= 0), currency text, employment_status text not null,
  primary key (organization_id, employee_id),
  foreign key (document_id, organization_id) references public.documents(id, organization_id) on delete cascade
);
alter table public.employees enable row level security;
create policy "employees_read_authorized" on public.employees for select to authenticated using (
  exists (select 1 from public.documents d where d.id = employees.document_id and d.organization_id = employees.organization_id)
);
revoke all on public.employees from anon, authenticated;
grant select on public.employees to authenticated;
grant all on public.employees to service_role;

create table public.invoices (
  organization_id uuid not null references public.organizations(id),
  invoice_id text not null,
  document_id uuid not null,
  customer_id text not null, customer text not null, currency text not null, total_minor_units bigint not null check (total_minor_units >= 0), invoice_date date not null, due_date date not null, payment_status text not null check (payment_status in ('paid', 'unpaid')), status_as_of date not null, contract_id text, foreign key (organization_id, customer_id) references public.customers(organization_id, customer_id),
  primary key (organization_id, invoice_id),
  foreign key (document_id, organization_id) references public.documents(id, organization_id) on delete cascade
);
alter table public.invoices enable row level security;
create policy "invoices_read_authorized" on public.invoices for select to authenticated using (
  exists (select 1 from public.documents d where d.id = invoices.document_id and d.organization_id = invoices.organization_id)
);
revoke all on public.invoices from anon, authenticated;
grant select on public.invoices to authenticated;
grant all on public.invoices to service_role;

create table public.payments (
  organization_id uuid not null references public.organizations(id),
  payment_id text not null,
  document_id uuid not null,
  invoice_id text not null, customer_id text not null, attempted_on date not null, attempted_minor_units bigint not null check (attempted_minor_units >= 0), settled_minor_units bigint not null check (settled_minor_units >= 0), status text not null, receipt_id text, foreign key (organization_id, invoice_id) references public.invoices(organization_id, invoice_id), foreign key (organization_id, customer_id) references public.customers(organization_id, customer_id),
  primary key (organization_id, payment_id),
  foreign key (document_id, organization_id) references public.documents(id, organization_id) on delete cascade
);
alter table public.payments enable row level security;
create policy "payments_read_authorized" on public.payments for select to authenticated using (
  exists (select 1 from public.documents d where d.id = payments.document_id and d.organization_id = payments.organization_id)
);
revoke all on public.payments from anon, authenticated;
grant select on public.payments to authenticated;
grant all on public.payments to service_role;

create table public.purchase_orders (
  organization_id uuid not null references public.organizations(id),
  order_id text not null,
  document_id uuid not null,
  supplier_id text not null, supplier text not null, project_id text not null, total_minor_units bigint not null check (total_minor_units >= 0), currency text not null, approved_on date not null, status text not null, foreign key (organization_id, project_id) references public.projects(organization_id, project_id),
  primary key (organization_id, order_id),
  foreign key (document_id, organization_id) references public.documents(id, organization_id) on delete cascade
);
alter table public.purchase_orders enable row level security;
create policy "purchase_orders_read_authorized" on public.purchase_orders for select to authenticated using (
  exists (select 1 from public.documents d where d.id = purchase_orders.document_id and d.organization_id = purchase_orders.organization_id)
);
revoke all on public.purchase_orders from anon, authenticated;
grant select on public.purchase_orders to authenticated;
grant all on public.purchase_orders to service_role;

create table public.opportunities (
  organization_id uuid not null references public.organizations(id),
  opportunity_id text not null,
  document_id uuid not null,
  customer text not null, stage text not null, annual_value_minor_units bigint not null check (annual_value_minor_units >= 0), contract_id text,
  primary key (organization_id, opportunity_id),
  foreign key (document_id, organization_id) references public.documents(id, organization_id) on delete cascade
);
alter table public.opportunities enable row level security;
create policy "opportunities_read_authorized" on public.opportunities for select to authenticated using (
  exists (select 1 from public.documents d where d.id = opportunities.document_id and d.organization_id = opportunities.organization_id)
);
revoke all on public.opportunities from anon, authenticated;
grant select on public.opportunities to authenticated;
grant all on public.opportunities to service_role;

-- Invoker view preserves each table's RLS. Normal retrieval never reads fixtures.
create view public.structured_records with (security_invoker = true) as
select 'customers'::text as table_name, r.customer_id as row_id, r.organization_id, r.document_id, to_jsonb(r) - 'organization_id' - 'document_id' as fields from public.customers r
union all
select 'projects'::text as table_name, r.project_id as row_id, r.organization_id, r.document_id, to_jsonb(r) - 'organization_id' - 'document_id' as fields from public.projects r
union all
select 'employees'::text as table_name, r.employee_id as row_id, r.organization_id, r.document_id, to_jsonb(r) - 'organization_id' - 'document_id' as fields from public.employees r
union all
select 'invoices'::text as table_name, r.invoice_id as row_id, r.organization_id, r.document_id, to_jsonb(r) - 'organization_id' - 'document_id' as fields from public.invoices r
union all
select 'payments'::text as table_name, r.payment_id as row_id, r.organization_id, r.document_id, to_jsonb(r) - 'organization_id' - 'document_id' as fields from public.payments r
union all
select 'purchase_orders'::text as table_name, r.order_id as row_id, r.organization_id, r.document_id, to_jsonb(r) - 'organization_id' - 'document_id' as fields from public.purchase_orders r
union all
select 'opportunities'::text as table_name, r.opportunity_id as row_id, r.organization_id, r.document_id, to_jsonb(r) - 'organization_id' - 'document_id' as fields from public.opportunities r;
revoke all on public.structured_records from anon;
grant select on public.structured_records to authenticated, service_role;

create policy "structured_chunks_require_live_row" on public.knowledge_chunks as restrictive
for select to authenticated using (
  source_type <> 'structured' or exists (
    select 1 from public.structured_records r
    where r.organization_id = knowledge_chunks.organization_id
      and r.document_id = knowledge_chunks.document_id
      and r.row_id = knowledge_chunks.row_id
      and r.table_name = knowledge_chunks.metadata->>'table'
      and r.fields = knowledge_chunks.metadata->'fields'
  )
);
-- Row edits fail closed until explicitly reindexed: stale vectors cannot answer.

create table public.query_history (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  organization_id uuid not null references public.organizations(id),
  active_role text not null check (active_role in ('CEO', 'Finance Manager', 'HR Manager', 'Sales Manager', 'Engineer')),
  query text not null check (length(query) between 1 and 2000),
  response jsonb not null,
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);
create index query_history_owner_context on public.query_history(user_id, organization_id, active_role, created_at desc) where deleted_at is null;
alter table public.query_history enable row level security;
create policy "history_read_self" on public.query_history for select to authenticated using (
  user_id = (select auth.uid()) and organization_id = (select organization_id from public.profiles where user_id = (select auth.uid()))
);
-- Writes come from the authenticated API, preserving the actual actor identity.
create policy "history_insert_self" on public.query_history for insert to authenticated with check (
  user_id = (select auth.uid()) and organization_id = (select organization_id from public.profiles where user_id = (select auth.uid()))
);
create policy "history_hide_self" on public.query_history for update to authenticated using (
  user_id = (select auth.uid()) and organization_id = (select organization_id from public.profiles where user_id = (select auth.uid()))
) with check (user_id = (select auth.uid()));
revoke all on public.query_history from anon, authenticated;
grant select, insert on public.query_history to authenticated;
grant update(deleted_at) on public.query_history to authenticated;
