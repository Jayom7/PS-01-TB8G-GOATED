"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { Icon, type IconName } from "@/components/icons";
import { createClient } from "@/lib/supabase/client";

type View = "Dashboard" | "Ask" | "Sources" | "Ingest" | "Security" | "Evaluation";
type Citation = {
  citation_id: string;
  source_type: string;
  title: string | null;
  location: Record<string, string | number | unknown>;
};
type Claim = { text: string; citations: Citation[] };
type QueryResult = {
  request_id: string;
  state: "CITATION_VALIDATED" | "PARTIALLY_CITATION_VALIDATED" | "INSUFFICIENT_EVIDENCE";
  claims: Claim[];
  trace: {
    session_verified: boolean;
    database_request_used_user_session: boolean;
    evidence_items_sent_to_model: number;
    unauthorized_evidence_sent_to_model: number;
    generation_model: string | null;
  };
};
type SourcePreview = {
  citation_id: string;
  source_type: string;
  title: string | null;
  source_id: string | null;
  location: Record<string, unknown>;
  excerpt: string;
};
type Source = {
  id: string;
  source_name: string;
  source_type: "pdf" | "image_ocr" | "structured";
  created_at: string;
  metadata: Record<string, unknown>;
};
type Identity = {
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  roles: string[];
};
type WorkspaceData = {
  identity: Identity;
  document_count: number;
  chunk_count: number;
  structured_record_count: number;
  documents: Source[];
  recent_queries: { query: string; state: string; created_at: string }[];
  authorization: string;
  api: string;
  supabase: string;
  gemini: string;
  ingestion: string;
  evaluation: string;
  demo_switch_available: boolean;
};
type SecurityData = {
  identity: Identity;
  effective_scope: string;
  trace: {
    created_at: string;
    query_id: string;
    state: string;
    authorized_evidence_count: number;
    unauthorized_evidence_count: number;
    decision: string;
  }[];
  security_tests: Record<string, string | number>;
};
type EvaluationData = {
  dataset: string;
  query_count: number;
  retrieval_recall_at_k: number;
  mean_reciprocal_rank: number;
  authorization_violations: number;
  results: Record<string, unknown>[];
  completed_at?: string;
};

const DEMO_ROLES = ["CEO", "Finance Manager", "HR Manager", "Sales Manager", "Engineer"];
const navigation: { label: View; icon: IconName }[] = [
  { label: "Dashboard", icon: "home" },
  { label: "Ask", icon: "chat" },
  { label: "Sources", icon: "files" },
  { label: "Ingest", icon: "upload" },
  { label: "Security", icon: "lock" },
  { label: "Evaluation", icon: "chart" },
];
const exampleQuestions = [
  "What amount is shown on Acme's scanned invoice?",
  "What payment terms are in Acme's contract?",
  "Is Acme's invoice overdue?",
  "Is Acme overdue and what payment terms does its contract specify?",
];
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function readResponse<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(typeof body?.detail === "string" ? body.detail : `Request failed (${response.status}).`);
  }
  return body as T;
}

async function currentToken() {
  const { data } = await createClient().auth.getSession();
  return data.session?.access_token ?? null;
}

async function apiGet<T>(path: string) {
  const token = await currentToken();
  if (!token) throw new Error("Your session expired. Sign in again to continue.");
  return readResponse<T>(await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  }));
}

export default function Workspace({ identity }: { identity: string }) {
  const router = useRouter();
  const [view, setView] = useState<View>("Ask");
  const [query, setQuery] = useState("");
  const [askedQuery, setAskedQuery] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [activeSource, setActiveSource] = useState<SourcePreview | null>(null);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceData | null>(null);
  const [sources, setSources] = useState<Source[] | null>(null);
  const [security, setSecurity] = useState<SecurityData | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [structuredJson, setStructuredJson] = useState('{\n  "invoice_id": "INV-2048",\n  "status": "unpaid"\n}');
  const [structuredMeta, setStructuredMeta] = useState({ table: "invoices", rowId: "INV-2048", sourceName: "Invoice record", accessRole: "CEO" });
  const [ingestFile, setIngestFile] = useState<File | null>(null);
  const [ingestResult, setIngestResult] = useState<string | null>(null);
  const sourceTrigger = useRef<HTMLElement | null>(null);
  const sourceClose = useRef<HTMLButtonElement>(null);
  const sourceOpen = activeSource !== null;

  const refreshWorkspace = useCallback(async () => {
    try {
      setError(null);
      const data = await apiGet<WorkspaceData>("/api/v1/workspace");
      setWorkspace(data);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Workspace data is unavailable.");
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => { void refreshWorkspace(); }, 0);
    return () => window.clearTimeout(timer);
  }, [refreshWorkspace]);
  useEffect(() => {
    if (sourceOpen) sourceClose.current?.focus();
    else sourceTrigger.current?.focus();
  }, [sourceOpen]);
  useEffect(() => {
    if (!sourceOpen) return;
    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") setActiveSource(null);
      if (event.key === "Tab") {
        event.preventDefault();
        sourceClose.current?.focus();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [sourceOpen]);

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = query.trim();
    if (!question || pending) return;
    setPending(true);
    setError(null);
    setResult(null);
    setActiveSource(null);
    setAskedQuery(question);
    try {
      const token = await currentToken();
      if (!token) {
        router.replace("/login");
        return;
      }
      const response = await fetch(`${API_BASE}/api/v1/chat/query`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ query: question }),
      });
      setResult(await readResponse<QueryResult>(response));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The knowledge service is unavailable.");
    } finally {
      setPending(false);
    }
  }

  async function openSource(citation: Citation, trigger: HTMLElement) {
    sourceTrigger.current = trigger;
    setActiveSource({
      citation_id: citation.citation_id,
      source_type: citation.source_type,
      title: citation.title,
      source_id: null,
      location: citation.location,
      excerpt: "Loading the exact source excerpt…",
    });
    setSourceError(null);
    try {
      const source = await apiGet<SourcePreview>(`/api/v1/sources/${encodeURIComponent(citation.citation_id)}`);
      setActiveSource(source);
    } catch (cause) {
      setSourceError(cause instanceof Error ? cause.message : "This source is unavailable.");
    }
  }

  async function switchDemoUser(role: string) {
    if (!workspace?.demo_switch_available || pending) return;
    setPending(true);
    setError(null);
    try {
      const token = await currentToken();
      if (!token) throw new Error("Your session expired. Sign in again to continue.");
      const switched = await readResponse<{ access_token: string; refresh_token: string }>(await fetch(`${API_BASE}/api/v1/demo/switch`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      }));
      const { error: authError } = await createClient().auth.setSession(switched);
      if (authError) throw authError;
      setResult(null);
      setWorkspace(null);
      await refreshWorkspace();
      router.refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not switch the demo account.");
    } finally {
      setPending(false);
    }
  }

  async function signOut() {
    await createClient().auth.signOut();
    router.replace("/login");
    router.refresh();
  }

  async function loadSources() {
    setPending(true);
    setError(null);
    try {
      const data = await apiGet<{ sources: Source[] }>("/api/v1/sources");
      setSources(data.sources);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Authorized sources are unavailable.");
    } finally {
      setPending(false);
    }
  }

  async function loadSecurity() {
    setPending(true);
    setError(null);
    try { setSecurity(await apiGet<SecurityData>("/api/v1/security")); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Security status is unavailable."); }
    finally { setPending(false); }
  }

  async function loadEvaluation() {
    setPending(true);
    setError(null);
    try {
      const data = await apiGet<{ state: string; result: EvaluationData | null }>("/api/v1/evaluation");
      setEvaluation(data.result);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Evaluation state is unavailable."); }
    finally { setPending(false); }
  }

  function selectView(nextView: View) {
    setView(nextView);
    setError(null);
    setNavigationOpen(false);
    if (nextView === "Sources" && sources === null) void loadSources();
    if (nextView === "Security" && security === null) void loadSecurity();
    if (nextView === "Evaluation" && evaluation === null) void loadEvaluation();
  }

  async function uploadFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ingestFile) return;
    setPending(true);
    setError(null);
    setIngestResult(null);
    try {
      const token = await currentToken();
      if (!token) throw new Error("Your session expired. Sign in again to continue.");
      const response = await fetch(`${API_BASE}/api/v1/ingest/file`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": ingestFile.type || "application/octet-stream",
          "X-Source-Name": encodeURIComponent(ingestFile.name),
          "X-Access-Role": structuredMeta.accessRole,
        },
        body: ingestFile,
      });
      const payload = await readResponse<{ chunks_indexed: number; source_name: string }>(response);
      setIngestResult(`${payload.source_name} indexed · ${payload.chunks_indexed} chunks`);
      setIngestFile(null);
      await refreshWorkspace();
      setSources(null);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Ingestion failed."); }
    finally { setPending(false); }
  }

  async function ingestStructured(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setIngestResult(null);
    try {
      const fields = JSON.parse(structuredJson) as unknown;
      if (!fields || typeof fields !== "object" || Array.isArray(fields)) throw new Error("Fields must be a JSON object.");
      const token = await currentToken();
      if (!token) throw new Error("Your session expired. Sign in again to continue.");
      const response = await fetch(`${API_BASE}/api/v1/ingest/structured`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ table: structuredMeta.table, row_id: structuredMeta.rowId, source_name: structuredMeta.sourceName, fields, access_role: structuredMeta.accessRole }),
      });
      const payload = await readResponse<{ chunks_indexed: number; source_name: string }>(response);
      setIngestResult(`${payload.source_name} indexed · ${payload.chunks_indexed} chunks`);
      await refreshWorkspace();
      setSources(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Structured record ingestion failed.");
    } finally { setPending(false); }
  }

  async function runEvaluation() {
    setPending(true);
    setError(null);
    try {
      const token = await currentToken();
      if (!token) throw new Error("Your session expired. Sign in again to continue.");
      const payload = await readResponse<{ result: EvaluationData }>(await fetch(`${API_BASE}/api/v1/evaluation/run`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` },
      }));
      setEvaluation(payload.result);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "The evaluation run failed."); }
    finally { setPending(false); }
  }

  const role = workspace?.identity.role ?? "Loading";
  const userName = workspace?.identity.display_name ?? identity;

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <button className="icon-button mobile-menu-button" type="button" aria-label={navigationOpen ? "Close navigation" : "Open navigation"} aria-expanded={navigationOpen} onClick={() => setNavigationOpen((open) => !open)}>
            <Icon name={navigationOpen ? "close" : "menu"} size={21} />
          </button>
          <span className="brand-name">Clearframe</span>
        </div>
        <div className="topbar-context">Secure knowledge workspace</div>
        <div className="topbar-state">
          {workspace?.demo_switch_available ? (
            <label className="demo-switcher"><span>Demo user</span>
              <select aria-label="Switch demo user" value={DEMO_ROLES.includes(role) ? role : "CEO"} disabled={pending} onChange={(event) => void switchDemoUser(event.target.value)}>
                {DEMO_ROLES.map((demoRole) => <option key={demoRole}>{demoRole}</option>)}
              </select>
            </label>
          ) : <span className="identity-label" title={identity}>{userName}</span>}
          <span className="role-tag">{role}</span>
          <button className="signout-button" type="button" onClick={signOut}>Sign out</button>
        </div>
      </header>

      <div className="workspace-grid">
        <aside className={`navigation-rail ${navigationOpen ? "navigation-open" : ""}`}>
          <div className="rail-workspace-label">Workspace</div>
          <nav className="primary-navigation" aria-label="Workspace">
            {navigation.map(({ label, icon }) => (
              <button className={`navigation-item ${view === label ? "navigation-item-active" : ""}`} type="button" key={label} aria-current={view === label ? "page" : undefined} onClick={() => selectView(label)}>
                <Icon name={icon} size={19} /><span>{label}</span>
              </button>
            ))}
          </nav>
          <div className="rail-footer">
            <div className="preview-caption">Signed in as {role}</div>
            <p>Queries use your verified session and database access policies.</p>
          </div>
        </aside>

        <section className="main-column" aria-label={`${view} workspace`}>
          {error && view === "Ingest" && <div className="workspace-error" role="alert">{error}</div>}
          {view === "Ask" ? (
            <AskView
              identity={userName}
              role={role}
              query={query}
              setQuery={setQuery}
              askedQuery={askedQuery}
              result={result}
              pending={pending}
              error={error}
              onSubmit={ask}
              onSource={openSource}
            />
          ) : view === "Dashboard" ? (
            <DashboardView data={workspace} error={error} onRefresh={() => void refreshWorkspace()} onNavigate={setView} />
          ) : view === "Sources" ? (
            <SourcesView sources={sources} pending={pending} error={error} onRefresh={() => { setSources(null); void loadSources(); }} />
          ) : view === "Ingest" ? (
            <IngestView
              role={role}
              available={workspace?.ingestion === "ready"}
              accessRole={structuredMeta.accessRole}
              setAccessRole={(accessRole) => setStructuredMeta((value) => ({ ...value, accessRole }))}
              file={ingestFile}
              setFile={setIngestFile}
              result={ingestResult}
              pending={pending}
              structuredMeta={structuredMeta}
              setStructuredMeta={(update) => setStructuredMeta((value) => ({ ...value, ...update }))}
              structuredJson={structuredJson}
              setStructuredJson={setStructuredJson}
              onUpload={uploadFile}
              onStructured={ingestStructured}
            />
          ) : view === "Security" ? (
            <SecurityView data={security} pending={pending} error={error} onRefresh={() => void loadSecurity()} />
          ) : (
            <EvaluationView data={evaluation} pending={pending} error={error} role={role} onRefresh={() => void loadEvaluation()} onRun={() => void runEvaluation()} />
          )}
        </section>
      </div>

      {navigationOpen && <button type="button" className="mobile-scrim nav-scrim" aria-label="Close navigation" onClick={() => setNavigationOpen(false)} />}
      {sourceOpen && activeSource && <>
        <button type="button" className="drawer-scrim" aria-label="Close source details" onClick={() => setActiveSource(null)} />
        <aside className="source-drawer" role="dialog" aria-modal="true" aria-labelledby="source-drawer-title" onKeyDown={(event: KeyboardEvent<HTMLElement>) => { if (event.key === "Tab") { event.preventDefault(); sourceClose.current?.focus(); } }}>
          <header className="drawer-heading">
            <div><h2 id="source-drawer-title">Source evidence</h2><p>Authorized source lookup</p></div>
            <button ref={sourceClose} className="icon-button" type="button" aria-label="Close source details" onClick={() => setActiveSource(null)}><Icon name="close" /></button>
          </header>
          {sourceError ? <p className="request-error" role="alert">{sourceError}</p> : <article className="drawer-source">
            <div className="drawer-source-title"><Icon name="files" size={18} /><div><strong>{activeSource.title ?? "Source"}</strong><span>{formatLocation(activeSource.location)}</span></div></div>
            <dl className="source-facts"><div><dt>Type</dt><dd>{sourceTypeLabel(activeSource.source_type)}</dd></div>
              {activeSource.source_id && <div><dt>Reference</dt><dd>{activeSource.source_id}</dd></div>}
              {typeof activeSource.location.region === "object" && activeSource.location.region !== null && <div><dt>OCR region</dt><dd>{JSON.stringify(activeSource.location.region)}</dd></div>}
            </dl>
            <p className="source-excerpt">{activeSource.excerpt}</p>
          </article>}
          <p className="drawer-policy"><Icon name="lock" size={16} />The API applied this user&apos;s database session to the source lookup.</p>
        </aside>
      </>}
    </main>
  );
}

function AskView({ identity, role, query, setQuery, askedQuery, result, pending, error, onSubmit, onSource }: {
  identity: string; role: string; query: string; setQuery: (value: string) => void; askedQuery: string;
  result: QueryResult | null; pending: boolean; error: string | null;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onSource: (citation: Citation, trigger: HTMLElement) => void;
}) {
  const refs = result ? [...new Map(result.claims.flatMap((claim) => claim.citations).map((citation) => [citation.citation_id, citation])).values()] : [];
  return <>
    <div className="conversation-header"><div><h1>Ask your knowledge base</h1><p>{role} · answers use evidence available to this session</p></div></div>
    <div className="conversation-scroll">
      {result ? <div className="message-thread" aria-live="polite">
        <div className="question-bubble"><span className="message-avatar user-avatar" aria-hidden="true">{identity.slice(0, 1).toUpperCase()}</span><p>{askedQuery}</p></div>
        {result.state === "INSUFFICIENT_EVIDENCE" ? <div className="preview-response" role="status"><div className="answer-avatar" aria-hidden="true">C</div><div><p className="response-primary">I couldn’t find enough authorized evidence to answer.</p><p className="response-secondary">Try a more specific question or ask your workspace administrator about available sources.</p></div></div> : <div className="answer-block"><div className="answer-avatar" aria-hidden="true">C</div><div className="answer-copy">
          {result.claims.map((claim, index) => <p key={`${result.request_id}-${index}`}>{claim.text} {claim.citations.map((citation) => <button className="inline-citation" key={citation.citation_id} type="button" aria-label={`Open source: ${citation.title ?? "Evidence"}`} onClick={(event) => onSource(citation, event.currentTarget)}>[{citationNumber(result.claims, citation.citation_id)}]</button>)}</p>)}
          {result.state === "PARTIALLY_CITATION_VALIDATED" && <p className="response-secondary">Claims without a valid source citation were omitted.</p>}
          <div className="answer-foot"><span className="grounded-state"><Icon name="lock" size={14} />{result.state === "CITATION_VALIDATED" ? "Citations validated" : "Partially validated"}</span><span>{result.trace.evidence_items_sent_to_model} authorized evidence items</span>{result.trace.generation_model && <span>{result.trace.generation_model}</span>}
            {refs.length > 0 && <button className="view-sources" type="button" onClick={(event) => onSource(refs[0], event.currentTarget)}>View sources <Icon name="arrow" size={15} /></button>}
          </div>
        </div></div>}
      </div> : <div className="empty-conversation"><div className="empty-mark" aria-hidden="true"><Icon name="chat" size={22} /></div><p>Ask about a document, image, or business record.</p><div className="question-examples" aria-label="Example questions">{exampleQuestions.map((example) => <button className="sample-question" type="button" key={example} onClick={() => setQuery(example)}><span>{example}</span><Icon name="arrow" size={17} /></button>)}</div></div>}
      {pending && <p className="request-status" role="status">Searching authorized sources…</p>}
      {error && <p className="request-error" role="alert">{error}</p>}
    </div>
    <div className="composer-wrap"><form className="composer" onSubmit={onSubmit}><label className="sr-only" htmlFor="query-input">Ask a question</label><textarea id="query-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ask a question about your knowledge..." maxLength={2000} rows={2} disabled={pending} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} /><div className="composer-actions"><span className="composer-note">Your session scopes retrieval and citation lookup.</span><button className="send-button" type="submit" disabled={!query.trim() || pending}><Icon name="send" size={17} /><span>{pending ? "Searching" : "Ask"}</span></button></div></form></div>
  </>;
}

function DashboardView({ data, error, onRefresh, onNavigate }: { data: WorkspaceData | null; error: string | null; onRefresh: () => void; onNavigate: (view: View) => void }) {
  if (!data) return <PageState title="Dashboard" error={error} pending={!error} onRefresh={onRefresh} />;
  return <div className="data-page"><PageHeading title="Dashboard" description="Live state from your authenticated Clearframe workspace." action={<button className="quiet-button" type="button" onClick={onRefresh}>Refresh</button>} />
    <div className="dashboard-identity"><span className="user-indicator">{data.identity.display_name.slice(0, 1).toUpperCase()}</span><div><strong>{data.identity.display_name}</strong><span>{data.identity.email} · {data.identity.role}</span></div><span className="status-pill status-good">Authorization active</span></div>
    <dl className="metric-strip"><Metric label="Authorized sources" value={data.document_count} /><Metric label="Searchable chunks" value={data.chunk_count} /><Metric label="Structured records" value={data.structured_record_count} /></dl>
    <div className="dashboard-columns"><section className="data-section"><SectionTitle title="System connections" action={<span className="live-status"><i />Live</span>} /><div className="connection-list"><StatusRow label="API" value={data.api} /><StatusRow label="Supabase" value={data.supabase} /><StatusRow label="Gemini" value={data.gemini} /><StatusRow label="Ingestion" value={data.ingestion} /><StatusRow label="Evaluation" value={data.evaluation} /></div></section>
      <section className="data-section"><SectionTitle title="Recent queries" action={<button className="text-button" type="button" onClick={() => onNavigate("Ask")}>Ask a question</button>} />{data.recent_queries.length ? <ol className="recent-query-list">{data.recent_queries.slice(0, 6).map((item, index) => <li key={`${item.created_at}-${index}`}><span>{item.query}</span><small>{item.state.replaceAll("_", " ")} · {formatTime(item.created_at)}</small></li>)}</ol> : <p className="empty-note">No queries in this API session yet.</p>}</section></div>
  </div>;
}

function SourcesView({ sources, pending, error, onRefresh }: { sources: Source[] | null; pending: boolean; error: string | null; onRefresh: () => void }) {
  if (!sources) return <PageState title="Sources" pending={pending} error={error} onRefresh={onRefresh} />;
  return <div className="data-page"><PageHeading title="Sources" description="Only documents visible under your current database policies appear here." action={<button className="quiet-button" type="button" onClick={onRefresh}>Refresh</button>} />
    <p className="list-count">{sources.length} authorized {sources.length === 1 ? "source" : "sources"}</p>
    {sources.length ? <div className="source-table-wrap"><table className="source-table"><thead><tr><th>Source</th><th>Type</th><th>Added</th><th>Ingested chunks</th></tr></thead><tbody>{sources.map((source) => <tr key={source.id}><td><strong>{source.source_name}</strong><small>{source.id}</small></td><td><span className={`source-kind source-kind-${source.source_type}`}>{sourceTypeLabel(source.source_type)}</span></td><td>{formatTime(source.created_at)}</td><td>{typeof source.metadata.chunk_count === "number" ? source.metadata.chunk_count : "—"}</td></tr>)}</tbody></table></div> : <div className="empty-state"><Icon name="files" size={22} /><h2>No authorized sources yet</h2><p>Sources added for your role will appear here after ingestion.</p></div>}
  </div>;
}

function IngestView({ role, available, accessRole, setAccessRole, file, setFile, result, pending, structuredMeta, setStructuredMeta, structuredJson, setStructuredJson, onUpload, onStructured }: {
  role: string; available: boolean; accessRole: string; setAccessRole: (role: string) => void; file: File | null; setFile: (file: File | null) => void; result: string | null; pending: boolean;
  structuredMeta: { table: string; rowId: string; sourceName: string; accessRole: string }; setStructuredMeta: (update: Partial<{ table: string; rowId: string; sourceName: string; accessRole: string }>) => void;
  structuredJson: string; setStructuredJson: (value: string) => void; onUpload: (event: FormEvent<HTMLFormElement>) => void; onStructured: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const canIngest = available && role === "CEO";
  return <div className="data-page"><PageHeading title="Ingest" description="Index source files and structured records into the secured knowledge store." />
    {!available && <div className="inline-notice" role="status"><Icon name="lock" size={17} /><span>The local ingestion service is unavailable. Confirm the local API and Supabase are running.</span></div>}
    {available && role !== "CEO" && <div className="inline-notice" role="status"><Icon name="lock" size={17} /><span>Ingestion is restricted to the CEO demo account. Your current role remains read-only.</span></div>}
    {result && <div className="success-notice" role="status">{result}</div>}
    <div className="ingest-columns"><form className="ingest-form" onSubmit={onUpload}><div className="form-title"><Icon name="upload" size={18} /><div><h2>Document or image</h2><p>PDF, PNG, or JPEG · up to 25 MB</p></div></div>
      <label className="file-drop"><input type="file" accept="application/pdf,image/png,image/jpeg,.pdf,.png,.jpg,.jpeg" disabled={!canIngest || pending} onChange={(event) => setFile(event.target.files?.[0] ?? null)} /><Icon name="files" size={20} /><strong>{file?.name ?? "Choose a source file"}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : "PDF text and scanned pages, or image OCR"}</span></label>
      <label className="field-label">Grant source to<select value={accessRole} disabled={!canIngest || pending} onChange={(event) => setAccessRole(event.target.value)}>{DEMO_ROLES.map((value) => <option key={value}>{value}</option>)}</select></label>
      <button className="primary-action" type="submit" disabled={!canIngest || pending || !file}>{pending ? "Indexing source…" : "Upload and index"}</button>
      <p className="form-footnote">Files are stored in the local private ingestion folder. The selected role is the only role granted access.</p>
    </form>
    <form className="ingest-form" onSubmit={onStructured}><div className="form-title"><Icon name="table" size={18} /><div><h2>Structured record</h2><p>Canonical text and embeddings are generated server-side.</p></div></div>
      <div className="field-pair"><label className="field-label">Table<input value={structuredMeta.table} disabled={!canIngest || pending} onChange={(event) => setStructuredMeta({ table: event.target.value })} required /></label><label className="field-label">Row ID<input value={structuredMeta.rowId} disabled={!canIngest || pending} onChange={(event) => setStructuredMeta({ rowId: event.target.value })} required /></label></div>
      <label className="field-label">Source name<input value={structuredMeta.sourceName} disabled={!canIngest || pending} onChange={(event) => setStructuredMeta({ sourceName: event.target.value })} required /></label>
      <label className="field-label">Record fields<textarea className="json-input" value={structuredJson} disabled={!canIngest || pending} onChange={(event) => setStructuredJson(event.target.value)} spellCheck={false} /></label>
      <label className="field-label">Grant source to<select value={structuredMeta.accessRole} disabled={!canIngest || pending} onChange={(event) => setStructuredMeta({ accessRole: event.target.value })}>{DEMO_ROLES.map((value) => <option key={value}>{value}</option>)}</select></label>
      <button className="primary-action" type="submit" disabled={!canIngest || pending}>{pending ? "Indexing record…" : "Index structured record"}</button>
    </form></div>
  </div>;
}

function SecurityView({ data, pending, error, onRefresh }: { data: SecurityData | null; pending: boolean; error: string | null; onRefresh: () => void }) {
  if (!data) return <PageState title="Security" pending={pending} error={error} onRefresh={onRefresh} />;
  return <div className="data-page"><PageHeading title="Security" description="Identity and authorization decisions from the current API session." action={<button className="quiet-button" type="button" onClick={onRefresh}>Refresh trace</button>} />
    <div className="security-identity"><span className="security-mark"><Icon name="lock" size={20} /></span><div><strong>{data.identity.display_name}</strong><span>{data.identity.email} · {data.identity.roles.join(", ") || "No assigned role"}</span></div><span className="status-pill status-good">Session verified</span></div>
    <section className="data-section"><SectionTitle title="Effective access scope" /><p className="scope-copy">{data.effective_scope}</p><div className="security-checks">{Object.entries(data.security_tests).map(([label, value]) => <div key={label}><span>{label.replaceAll("_", " ")}</span><strong>{String(value)}</strong></div>)}</div></section>
    <section className="data-section"><SectionTitle title="Recent retrieval decisions" /><ol className="trace-list">{data.trace.length ? data.trace.map((entry) => <li key={entry.query_id}><span className="trace-dot" /><div><strong>{entry.decision}</strong><span>{entry.authorized_evidence_count} authorized evidence items · {entry.unauthorized_evidence_count} unauthorized items supplied</span></div><time>{formatTime(entry.created_at)}</time></li>) : <li className="empty-note">Ask a question to see a real retrieval trace for this session.</li>}</ol><p className="trace-disclaimer">The trace omits source names and contents. Recent events are held in this API process and clear when it restarts.</p></section>
  </div>;
}

function EvaluationView({ data, pending, error, role, onRefresh, onRun }: { data: EvaluationData | null; pending: boolean; error: string | null; role: string; onRefresh: () => void; onRun: () => void }) {
  return <div className="data-page"><PageHeading title="Evaluation" description="Measured results from the local NovaCore retrieval and authorization suite." action={<button className="quiet-button" type="button" onClick={onRefresh}>Refresh</button>} />
    {!data ? <div className="evaluation-empty"><Icon name="chart" size={22} />{error ? <p className="request-error" role="alert">{error}</p> : <><h2>No evaluation run recorded</h2><p>Run the real retrieval suite to measure recall, ranking, modality coverage, and authorization boundaries.</p></>}<button className="primary-action" type="button" disabled={pending || role !== "CEO"} onClick={onRun}>{pending ? "Running evaluation…" : "Run evaluation"}</button>{role !== "CEO" && <small>Switch to the CEO demo user to run the local test suite.</small>}</div> : <>
      <div className="evaluation-summary"><div><span>Dataset</span><strong>{data.dataset}</strong></div><div><span>Queries</span><strong>{data.query_count}</strong></div><div><span>Recall@12</span><strong>{formatMetric(data.retrieval_recall_at_k)}</strong></div><div><span>Mean reciprocal rank</span><strong>{formatMetric(data.mean_reciprocal_rank)}</strong></div><div><span>Authorization leaks</span><strong className={data.authorization_violations ? "metric-bad" : "metric-good"}>{data.authorization_violations}</strong></div></div>
      <div className="source-table-wrap"><table className="source-table evaluation-table"><thead><tr><th>Evaluation case</th><th>Role</th><th>Result</th><th>Latency</th><th>Forbidden hits</th></tr></thead><tbody>{data.results.map((row, index) => <tr key={`${String(row.name)}-${index}`}><td><strong>{String(row.name)}</strong></td><td>{String(row.role ?? "—")}</td><td><span className={`status-pill ${row.hit === true ? "status-good" : "status-bad"}`}>{row.hit === true ? "Pass" : "Review"}</span></td><td>{typeof row.latency_ms === "number" ? `${row.latency_ms} ms` : "—"}</td><td>{Array.isArray(row.forbidden_source_hits) ? row.forbidden_source_hits.length : "—"}</td></tr>)}</tbody></table></div>
      <p className="trace-disclaimer">Retrieved with authenticated demo users against the local database. This run measures retrieval and row-level authorization; it does not score semantic answer quality.</p>
      <button className="quiet-button" type="button" disabled={pending || role !== "CEO"} onClick={onRun}>{pending ? "Running…" : "Run again"}</button>
    </>}
  </div>;
}

function PageHeading({ title, description, action }: { title: string; description: string; action?: React.ReactNode }) {
  return <div className="page-heading"><div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}
function PageState({ title, error, pending, onRefresh }: { title: string; error?: string | null; pending: boolean; onRefresh: () => void }) {
  return <div className="data-page"><PageHeading title={title} description="Live information from your authenticated workspace." />{error ? <p className="request-error" role="alert">{error}</p> : <p className="request-status" role="status">{pending ? "Loading authorized workspace data…" : "No data available."}</p>}<button className="quiet-button" type="button" onClick={onRefresh}>Retry</button></div>;
}
function Metric({ label, value }: { label: string; value: number }) { return <div><dt>{label}</dt><dd>{value.toLocaleString()}</dd></div>; }
function SectionTitle({ title, action }: { title: string; action?: React.ReactNode }) { return <div className="section-title"><h2>{title}</h2>{action}</div>; }
function StatusRow({ label, value }: { label: string; value: string }) { const ready = ["connected", "configured", "ready", "available"].includes(value); return <div className="connection-row"><span>{label}</span><span className={`connection-state ${ready ? "is-ready" : ""}`}><i />{value.replaceAll("_", " ")}</span></div>; }

function citationNumber(claims: Claim[], id: string) {
  const ids = [...new Set(claims.flatMap((claim) => claim.citations.map((citation) => citation.citation_id)))];
  return ids.indexOf(id) + 1;
}
function formatLocation(location: Record<string, unknown>) {
  if (typeof location.page === "number") return `Page ${location.page}`;
  if (typeof location.row === "string") return `Row ${location.row}`;
  if (typeof location.image_id === "string") return `Image ${location.image_id}`;
  return "Source location unavailable";
}
function sourceTypeLabel(sourceType: string) {
  if (sourceType === "image_ocr") return "Image / OCR";
  if (sourceType === "structured") return "Structured record";
  return sourceType.toUpperCase();
}
function formatTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}
function formatMetric(value: number) { return Number.isFinite(value) ? value.toFixed(3) : "—"; }
