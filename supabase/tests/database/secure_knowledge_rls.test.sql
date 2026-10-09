begin;

create extension if not exists pgtap with schema extensions;
select plan(43);

select ok(
  (select count(*) = 7 and bool_and(relrowsecurity)
   from pg_class c
   join pg_namespace n on n.oid = c.relnamespace
   where n.nspname = 'public'
     and c.relname in (
       'organizations', 'profiles', 'roles', 'user_roles', 'documents',
       'knowledge_chunks', 'access_grants'
     )),
  'RLS is enabled on all seven application tables'
);
select ok(
  (select a.atttypmod = 1536
   from pg_attribute a
   join pg_class c on c.oid = a.attrelid
   join pg_namespace n on n.oid = c.relnamespace
   where n.nspname = 'public' and c.relname = 'knowledge_chunks'
     and a.attname = 'embedding'),
  'embedding dimension matches Gemini Embedding 2 at 1536'
);
select has_index('public', 'knowledge_chunks', 'knowledge_chunks_embedding_hnsw',
  'HNSW vector index exists');
select has_index('public', 'knowledge_chunks', 'knowledge_chunks_search_gin',
  'full-text GIN index exists');
select ok(not has_table_privilege('anon', 'public.knowledge_chunks', 'select'),
  'anon cannot read knowledge chunks');
select ok(not has_table_privilege('authenticated', 'public.user_roles', 'insert'),
  'authenticated users cannot assign themselves roles');
select ok(not has_table_privilege('authenticated', 'public.profiles', 'update'),
  'authenticated users cannot change their organization profile');
select ok(not has_function_privilege(
  'anon', 'public.match_knowledge_chunks(extensions.vector,text,integer)', 'execute'
), 'anon cannot execute authorized retrieval');
select ok(has_function_privilege(
  'authenticated', 'public.match_knowledge_chunks(extensions.vector,text,integer)', 'execute'
), 'authenticated users can execute authorized retrieval');

insert into public.organizations (id, name) values
  ('10000000-0000-4000-8000-000000000001', 'NovaCore Org A'),
  ('10000000-0000-4000-8000-000000000002', 'NovaCore Org B');

insert into auth.users (id, aud, role, email) values
  ('20000000-0000-4000-8000-000000000001', 'authenticated', 'authenticated', 'finance-test@novacore.invalid'),
  ('20000000-0000-4000-8000-000000000002', 'authenticated', 'authenticated', 'hr-test@novacore.invalid'),
  ('20000000-0000-4000-8000-000000000003', 'authenticated', 'authenticated', 'other-org-test@novacore.invalid'),
  ('20000000-0000-4000-8000-000000000004', 'authenticated', 'authenticated', 'ceo-test@novacore.invalid'),
  ('20000000-0000-4000-8000-000000000005', 'authenticated', 'authenticated', 'sales-test@novacore.invalid'),
  ('20000000-0000-4000-8000-000000000006', 'authenticated', 'authenticated', 'engineer-test@novacore.invalid');

insert into public.profiles (user_id, organization_id, display_name) values
  ('20000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001', 'Finance Test'),
  ('20000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000001', 'HR Test'),
  ('20000000-0000-4000-8000-000000000003', '10000000-0000-4000-8000-000000000002', 'Other Org Test'),
  ('20000000-0000-4000-8000-000000000004', '10000000-0000-4000-8000-000000000001', 'CEO Test'),
  ('20000000-0000-4000-8000-000000000005', '10000000-0000-4000-8000-000000000001', 'Sales Test'),
  ('20000000-0000-4000-8000-000000000006', '10000000-0000-4000-8000-000000000001', 'Engineer Test');

insert into public.roles (id, organization_id, name) values
  ('30000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001', 'Finance Manager'),
  ('30000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000001', 'HR Manager'),
  ('30000000-0000-4000-8000-000000000003', '10000000-0000-4000-8000-000000000002', 'Finance Manager'),
  ('30000000-0000-4000-8000-000000000004', '10000000-0000-4000-8000-000000000001', 'CEO'),
  ('30000000-0000-4000-8000-000000000005', '10000000-0000-4000-8000-000000000001', 'Sales Manager'),
  ('30000000-0000-4000-8000-000000000006', '10000000-0000-4000-8000-000000000001', 'Engineer');

insert into public.user_roles (user_id, role_id, organization_id) values
  ('20000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001'),
  ('20000000-0000-4000-8000-000000000002', '30000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000001'),
  ('20000000-0000-4000-8000-000000000003', '30000000-0000-4000-8000-000000000003', '10000000-0000-4000-8000-000000000002'),
  ('20000000-0000-4000-8000-000000000004', '30000000-0000-4000-8000-000000000004', '10000000-0000-4000-8000-000000000001'),
  ('20000000-0000-4000-8000-000000000005', '30000000-0000-4000-8000-000000000005', '10000000-0000-4000-8000-000000000001'),
  ('20000000-0000-4000-8000-000000000006', '30000000-0000-4000-8000-000000000006', '10000000-0000-4000-8000-000000000001');

insert into public.documents (id, organization_id, source_type, source_name, content_hash) values
  ('40000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001', 'structured', 'Finance invoice INV-2048', 'test-finance-a'),
  ('40000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000001', 'structured', 'HR compensation records', 'test-hr-a'),
  ('40000000-0000-4000-8000-000000000003', '10000000-0000-4000-8000-000000000002', 'structured', 'Other organization invoice', 'test-finance-b'),
  ('40000000-0000-4000-8000-000000000004', '10000000-0000-4000-8000-000000000001', 'structured', 'Sales opportunity records', 'test-sales-a'),
  ('40000000-0000-4000-8000-000000000005', '10000000-0000-4000-8000-000000000001', 'structured', 'Engineering project records', 'test-engineering-a');

insert into public.knowledge_chunks (
  id, organization_id, document_id, source_type, source_name, source_id,
  row_id, chunk_index, content, embedding
) values
  ('50000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000001', 'structured', 'Finance invoice INV-2048', 'invoices', 'INV-2048', 0, 'Acme invoice INV-2048 total USD 48,000 unpaid', ('[1,0,' || repeat('0,', 1533) || '0]')::extensions.vector),
  ('50000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000002', 'structured', 'HR compensation records', 'employees', 'EMP-002', 0, 'Employee salary payroll confidential', ('[0,1,' || repeat('0,', 1533) || '0]')::extensions.vector),
  ('50000000-0000-4000-8000-000000000003', '10000000-0000-4000-8000-000000000002', '40000000-0000-4000-8000-000000000003', 'structured', 'Other organization invoice', 'invoices', 'INV-9999', 0, 'Acme invoice INV-9999 total USD 99,000', ('[1,0,' || repeat('0,', 1533) || '0]')::extensions.vector),
  ('50000000-0000-4000-8000-000000000004', '10000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000004', 'structured', 'Sales opportunity records', 'opportunities', 'OPP-2048', 0, 'Acme opportunity renewal forecast USD 72,000', ('[0,0,1,' || repeat('0,', 1532) || '0]')::extensions.vector),
  ('50000000-0000-4000-8000-000000000005', '10000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000005', 'structured', 'Engineering project records', 'projects', 'PRJ-ATLAS', 0, 'Atlas Gateway engineering delivery milestone 2026-11-15', ('[0,0,0,1,' || repeat('0,', 1531) || '0]')::extensions.vector);

-- The structured index is valid only while the actual typed row exists and matches.
insert into public.customers (organization_id, customer_id, document_id, name, status) values
('10000000-0000-4000-8000-000000000001','ACME','40000000-0000-4000-8000-000000000001','Acme','active'),
('10000000-0000-4000-8000-000000000002','ACME','40000000-0000-4000-8000-000000000003','Acme','active');
insert into public.invoices (organization_id,invoice_id,document_id,customer_id,customer,currency,total_minor_units,invoice_date,due_date,payment_status,status_as_of) values
('10000000-0000-4000-8000-000000000001','INV-2048','40000000-0000-4000-8000-000000000001','ACME','Acme','USD',4800000,'2026-09-01','2026-10-01','unpaid','2026-10-08'),
('10000000-0000-4000-8000-000000000002','INV-9999','40000000-0000-4000-8000-000000000003','ACME','Acme','USD',9900000,'2026-09-01','2026-10-01','unpaid','2026-10-08');
insert into public.employees (organization_id,employee_id,document_id,role,employment_status) values
('10000000-0000-4000-8000-000000000001','EMP-002','40000000-0000-4000-8000-000000000002','Engineer','active');
insert into public.projects (organization_id,project_id,document_id,name,status) values
('10000000-0000-4000-8000-000000000001','PRJ-ATLAS','40000000-0000-4000-8000-000000000005','Atlas Gateway','active');
insert into public.opportunities (organization_id,opportunity_id,document_id,customer,stage,annual_value_minor_units) values
('10000000-0000-4000-8000-000000000001','OPP-2048','40000000-0000-4000-8000-000000000004','Acme','renewal',7200000);
update public.knowledge_chunks k set metadata = jsonb_build_object('table',r.table_name,'fields',r.fields)
from public.structured_records r where r.document_id=k.document_id and r.row_id=k.row_id;

select ok((select count(*)=8 and bool_and(relrowsecurity) from pg_class where relnamespace='public'::regnamespace and relname in ('customers','projects','employees','invoices','payments','purchase_orders','opportunities','query_history')), 'RLS covers all new tables');
select ok((select 'security_invoker=true'=any(reloptions) from pg_class where oid='public.structured_records'::regclass), 'Structured origin view invokes caller policies');
select ok(not has_table_privilege('authenticated','public.invoices','insert'), 'Users cannot insert typed rows directly');
select ok(not has_table_privilege('anon','public.invoices','select'), 'Anonymous users cannot inspect typed rows');
select ok(not has_column_privilege('authenticated','public.query_history','response','update'), 'Stored responses are immutable to authenticated users');
select ok(has_column_privilege('authenticated','public.query_history','deleted_at','update'), 'Owners can hide history');
-- Use a distinct chunk index so the tenant FK, rather than a duplicate index,
-- is the constraint this assertion exercises.
select throws_ok($$insert into public.knowledge_chunks (organization_id,document_id,source_type,source_name,source_id,chunk_index,content) values ('10000000-0000-4000-8000-000000000002','40000000-0000-4000-8000-000000000001','pdf','forged','forged',99,'forged')$$, '23503', null, 'Cross-organization chunk/document relationship fails');
insert into public.query_history (conversation_id,user_id,organization_id,active_role,query,response) values
('60000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000001','10000000-0000-4000-8000-000000000001','Finance Manager','Terms?','{}');

insert into public.access_grants (organization_id, document_id, principal_type, principal_id)
values
  ('10000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000001', 'role', '30000000-0000-4000-8000-000000000001'),
  ('10000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000002', 'role', '30000000-0000-4000-8000-000000000002'),
  ('10000000-0000-4000-8000-000000000002', '40000000-0000-4000-8000-000000000003', 'role', '30000000-0000-4000-8000-000000000003'),
  ('10000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000001', 'role', '30000000-0000-4000-8000-000000000004'),
  ('10000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000002', 'role', '30000000-0000-4000-8000-000000000004'),
  ('10000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000004', 'role', '30000000-0000-4000-8000-000000000004'),
  ('10000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000005', 'role', '30000000-0000-4000-8000-000000000004'),
  ('10000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000004', 'role', '30000000-0000-4000-8000-000000000005'),
  ('10000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000005', 'role', '30000000-0000-4000-8000-000000000006');

set local role authenticated;
set local "request.jwt.claim.role" = 'authenticated';
set local "request.jwt.claims" = '{"role":"authenticated","sub":"20000000-0000-4000-8000-000000000001"}';
set local "request.jwt.claim.sub" = '20000000-0000-4000-8000-000000000001';
select is((select count(*) from public.knowledge_chunks), 1::bigint,
  'finance user sees only finance chunks in their organization');
select is((select count(*) from public.invoices),1::bigint,'Finance can inspect its authorized typed invoice');
select is((select count(*) from public.query_history),1::bigint,'Owner can read saved history');
select is((select count(*) from public.match_knowledge_chunks(
  ('[1,0,' || repeat('0,', 1533) || '0]')::extensions.vector, 'Acme invoice', 12
)), 1::bigint, 'finance retrieval returns its authorized invoice');
select is((select count(*) from public.documents
  where id = '40000000-0000-4000-8000-000000000002'), 0::bigint,
  'finance user cannot discover the HR document by ID');

set local "request.jwt.claims" = '{"role":"authenticated","sub":"20000000-0000-4000-8000-000000000002"}';
set local "request.jwt.claim.sub" = '20000000-0000-4000-8000-000000000002';
select is((select count(*) from public.match_knowledge_chunks(
  ('[1,0,' || repeat('0,', 1533) || '0]')::extensions.vector, 'Acme invoice', 12
)), 0::bigint, 'HR retrieval returns zero finance evidence for the LLM context');
select is((select count(*) from public.knowledge_chunks
  where id = '50000000-0000-4000-8000-000000000001'), 0::bigint,
  'HR cannot look up the finance citation by ID');
select is((select count(*) from public.documents
  where id = '40000000-0000-4000-8000-000000000001'), 0::bigint,
  'HR cannot discover the finance filename by ID');
select is((select count(*) from public.invoices),0::bigint,'HR cannot read typed finance rows');
select is((select count(*) from public.query_history),0::bigint,'Another identity cannot read history');
select throws_ok($$insert into public.query_history(conversation_id,user_id,organization_id,active_role,query,response) values ('60000000-0000-4000-8000-000000000002','20000000-0000-4000-8000-000000000001','10000000-0000-4000-8000-000000000001','CEO','forged','{}')$$,'42501',null,'User cannot forge another history owner');

set local "request.jwt.claims" = '{"role":"authenticated","sub":"20000000-0000-4000-8000-000000000003"}';
set local "request.jwt.claim.sub" = '20000000-0000-4000-8000-000000000003';
select is((select count(*) from public.match_knowledge_chunks(
  ('[1,0,' || repeat('0,', 1533) || '0]')::extensions.vector, 'Acme invoice', 12
)), 1::bigint, 'user can retrieve a matching row in their own other organization');
select is((select count(*) from public.knowledge_chunks
  where id = '50000000-0000-4000-8000-000000000001'), 0::bigint,
  'same-role user in another organization cannot see the finance citation');

set local "request.jwt.claims" = '{"role":"authenticated","sub":"20000000-0000-4000-8000-000000000004"}';
set local "request.jwt.claim.sub" = '20000000-0000-4000-8000-000000000004';
select is((select count(*) from public.documents), 4::bigint,
  'CEO role can read all four explicitly granted organization sources');
select is((select count(*) from public.match_knowledge_chunks(
  ('[1,0,' || repeat('0,', 1533) || '0]')::extensions.vector, 'Acme invoice', 12
)), 1::bigint, 'CEO retrieval can access finance evidence');

set local "request.jwt.claims" = '{"role":"authenticated","sub":"20000000-0000-4000-8000-000000000005"}';
set local "request.jwt.claim.sub" = '20000000-0000-4000-8000-000000000005';
select is((select count(*) from public.knowledge_chunks), 1::bigint,
  'Sales role can read its granted opportunity evidence');
select is((select count(*) from public.knowledge_chunks
  where id = '50000000-0000-4000-8000-000000000001'), 0::bigint,
  'Sales role cannot discover the finance citation by ID');
set local "request.jwt.claims" = '{"role":"authenticated","sub":"20000000-0000-4000-8000-000000000005","organization_id":"10000000-0000-4000-8000-000000000002"}';
select is((select count(*) from public.documents
  where organization_id = '10000000-0000-4000-8000-000000000002'), 0::bigint,
  'forged organization claim does not change the profile-scoped organization');

set local "request.jwt.claims" = '{"role":"authenticated","sub":"20000000-0000-4000-8000-000000000006"}';
set local "request.jwt.claim.sub" = '20000000-0000-4000-8000-000000000006';
select is((select count(*) from public.match_knowledge_chunks(
  ('[0,0,0,1,' || repeat('0,', 1531) || '0]')::extensions.vector, 'Atlas Gateway', 12
)), 1::bigint, 'Engineer role can retrieve its engineering project evidence');
select is((select count(*) from public.knowledge_chunks
  where id = '50000000-0000-4000-8000-000000000002'), 0::bigint,
  'Engineer role cannot discover the HR salary citation by ID');

reset role;
-- Row edits and deletions must immediately invalidate old index representations.
update public.invoices set payment_status='paid' where invoice_id='INV-2048';
set local role authenticated;
set local "request.jwt.claims" = '{"role":"authenticated","sub":"20000000-0000-4000-8000-000000000001"}';
set local "request.jwt.claim.sub" = '20000000-0000-4000-8000-000000000001';
select is((select count(*) from public.knowledge_chunks),0::bigint,'Changed row denies stale unpaid indexed excerpt');
reset role;
update public.invoices set payment_status='unpaid' where invoice_id='INV-2048';
delete from public.invoices where invoice_id='INV-2048';
set local role authenticated;
select is((select count(*) from public.knowledge_chunks),0::bigint,'Deleted structured row denies orphaned index evidence');
reset role;
delete from public.access_grants where document_id='40000000-0000-4000-8000-000000000002';
set local role authenticated;
set local "request.jwt.claims" = '{"role":"authenticated","sub":"20000000-0000-4000-8000-000000000002"}';
set local "request.jwt.claim.sub" = '20000000-0000-4000-8000-000000000002';
select is((select count(*) from public.knowledge_chunks),0::bigint,'Revoked grant denies retrieval immediately');
reset role;
delete from public.documents where id='40000000-0000-4000-8000-000000000005';
set local role authenticated;
set local "request.jwt.claims" = '{"role":"authenticated","sub":"20000000-0000-4000-8000-000000000006"}';
set local "request.jwt.claim.sub" = '20000000-0000-4000-8000-000000000006';
select is((select count(*) from public.knowledge_chunks),0::bigint,'Deleted document removes source chunks');
reset role;
insert into public.documents(id,organization_id,source_type,source_name) values
('40000000-0000-4000-8000-000000000006','10000000-0000-4000-8000-000000000001','pdf','Row-scoped evidence');
insert into public.knowledge_chunks(id,organization_id,document_id,source_type,source_name,source_id,chunk_index,content,page_number) values
('50000000-0000-4000-8000-000000000006','10000000-0000-4000-8000-000000000001','40000000-0000-4000-8000-000000000006','pdf','Row-scoped evidence','row-scoped',0,'Authorized excerpt only',1);
insert into public.access_grants(organization_id,chunk_id,principal_type,principal_id) values
('10000000-0000-4000-8000-000000000001','50000000-0000-4000-8000-000000000006','user','20000000-0000-4000-8000-000000000001');
set local role authenticated;
set local "request.jwt.claims" = '{"role":"authenticated","sub":"20000000-0000-4000-8000-000000000001"}';
set local "request.jwt.claim.sub" = '20000000-0000-4000-8000-000000000001';
select is((select count(*) from public.knowledge_chunks),1::bigint,'Chunk-only grant allows exactly its excerpt');
select is((select count(*) from public.documents where id='40000000-0000-4000-8000-000000000006'),0::bigint,'Chunk-only grant cannot expose a full original document');
reset role;
delete from public.access_grants where chunk_id='50000000-0000-4000-8000-000000000006';
set local role authenticated;
select is((select count(*) from public.knowledge_chunks),0::bigint,'Chunk-only grant revocation takes effect');
select * from finish();
rollback;
