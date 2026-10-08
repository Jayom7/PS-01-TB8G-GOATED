"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type FormEvent, type KeyboardEvent } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Icon, type IconName } from "@/components/icons";
import { createClient } from "@/lib/supabase/client";

export type View = "Dashboard" | "Ask" | "Sources" | "Ingest" | "Security" | "Evaluation";
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
    generation_model: string | null;
    fallback_used: boolean;
    active_role: string;
    timing_ms: Record<string, number | null>;
    ranking_timing_note: string;
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

function readTheme(): "light" | "dark" {
  return window.localStorage.getItem("clearframe-theme") === "dark" ? "dark" : "light";
}

function subscribeTheme(callback: () => void) {
  window.addEventListener("clearframe-theme-change", callback);
  return () => window.removeEventListener("clearframe-theme-change", callback);
}
type WorkspaceData = {
  identity: Identity;
  active_role: string;
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
  latest_evaluation_status: string;
  demo_switch_available: boolean;
};
type SecurityData = {
  identity: Identity;
  active_role: string;
  effective_scope: string;
  trace: {
    created_at: string;
    query_id: string;
    state: string;
    active_role: string;
    authorized_evidence_count: number;
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
  measured_checks?: Record<string, boolean | number | string | null>;
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
const viewRoutes: Record<View, string> = {
  Dashboard: "/dashboard",
  Ask: "/ask",
  Sources: "/sources",
  Ingest: "/ingest",
  Security: "/security",
  Evaluation: "/evaluation",
};
const exampleQuestions = [
  "What amount is shown on Acme's scanned invoice?",
  "What payment terms are in Acme's contract?",
  "Is Acme's invoice overdue?",
  "Is Acme overdue and what payment terms does its contract specify?",
];
const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function readResponse<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const code = typeof body?.code === "string" ? body.code : "";
    const messages: Record<string, string> = {
      provider_unavailable: "The AI service is unavailable right now. Your question was not answered.",
      provider_rate_limited: "Answer generation is temporarily unavailable because the AI service is rate-limited. Your retrieved evidence remains protected; please retry later.",
      provider_timeout: "The AI service took too long to respond. Please try again.",
      provider_invalid_response: "The AI service returned an unusable answer. Please retry.",
      retrieval_unavailable: "Authorized search could not complete. No answer was generated.",
    };
    const message = response.status === 401
      ? "Your session expired. Sign in again to continue."
      : response.status === 403
        ? "Your current role does not have access to this action."
        : response.status === 404
          ? "This source is no longer available to your account."
          : response.status === 422
            ? "Check the submitted values and try again."
            : messages[code] ?? (response.status >= 500
              ? "The workspace service is temporarily unavailable. Please retry."
              : "The request could not be completed. Check the input and try again.");
    throw new Error(message);
  }
  return body as T;
}

function networkMessage(cause: unknown, fallback: string) {
  if (cause instanceof DOMException && (cause.name === "TimeoutError" || cause.name === "AbortError")) {
    return "The request took too long. Your input is still here; try again when the service is ready.";
  }
  if (cause instanceof TypeError) return "Could not reach the workspace service. Check that the API is running and try again.";
  return cause instanceof Error ? cause.message : fallback;
}

async function currentToken() {
  const { data } = await createClient().auth.getSession();
  return data.session?.access_token ?? null;
}

async function apiGet<T>(path: string, demoRole?: string) {
  const token = await currentToken();
  if (!token) throw new Error("Your session expired. Sign in again to continue.");
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  if (demoRole) headers["X-Demo-Role"] = demoRole;
  return readResponse<T>(await fetch(`${API_BASE}${path}`, {
    headers,
    cache: "no-store",
    signal: AbortSignal.timeout(20_000),
  }));
}

export default function Workspace({ identity, view }: { identity: string; view: View }) {
  const router = useRouter();
  const pathname = usePathname();
  const [query, setQuery] = useState("");
  const [askedQuery, setAskedQuery] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [activeSource, setActiveSource] = useState<SourcePreview | null>(null);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [sourceClosing, setSourceClosing] = useState(false);
  const [workspace, setWorkspace] = useState<WorkspaceData | null>(null);
  const [activeRole, setActiveRole] = useState("");
  const [sources, setSources] = useState<Source[] | null>(null);
  const [security, setSecurity] = useState<SecurityData | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const theme = useSyncExternalStore(subscribeTheme, readTheme, () => "light");
  const [sourceFilter, setSourceFilter] = useState("");
  const [sourceTypeFilter, setSourceTypeFilter] = useState("all");
  const [structuredJson, setStructuredJson] = useState('{\n  "invoice_id": "INV-2048",\n  "status": "unpaid"\n}');
  const [structuredMeta, setStructuredMeta] = useState({ table: "invoices", rowId: "INV-2048", sourceName: "Invoice record", accessRole: "CEO" });
  const [ingestFile, setIngestFile] = useState<File | null>(null);
  const [ingestResult, setIngestResult] = useState<string | null>(null);
  const sourceTrigger = useRef<HTMLElement | null>(null);
  const sourceClose = useRef<HTMLButtonElement>(null);
  const sourceCloseTimer = useRef<number | null>(null);
  const roleRestoreStarted = useRef(false);
  const activeRoleRef = useRef("");
  const sourceOpen = activeSource !== null;
  const closeSource = useCallback(() => {
    if (!sourceOpen || sourceClosing) return;
    setSourceClosing(true);
    sourceCloseTimer.current = window.setTimeout(() => {
      setActiveSource(null);
      setSourceClosing(false);
      sourceCloseTimer.current = null;
    }, 180);
  }, [sourceClosing, sourceOpen]);

  const refreshWorkspace = useCallback(async () => {
    try {
      setError(null);
      const data = await apiGet<WorkspaceData>("/api/v1/workspace", activeRole || undefined);
      if (!activeRoleRef.current || activeRoleRef.current === activeRole) setWorkspace(data);
    } catch (cause) {
      setError(networkMessage(cause, "Workspace information is unavailable."));
    }
  }, [activeRole]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void refreshWorkspace(); }, 0);
    return () => window.clearTimeout(timer);
  }, [refreshWorkspace]);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  useEffect(() => { activeRoleRef.current = activeRole; }, [activeRole]);
  useEffect(() => {
    if (sourceOpen) sourceClose.current?.focus();
    else sourceTrigger.current?.focus();
  }, [closeSource, sourceOpen]);
  useEffect(() => {
    if (!sourceOpen) return;
    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") closeSource();
      if (event.key === "Tab") {
        event.preventDefault();
        sourceClose.current?.focus();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [closeSource, sourceOpen]);

  useEffect(() => () => {
    if (sourceCloseTimer.current !== null) window.clearTimeout(sourceCloseTimer.current);
  }, []);

  async function ask(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
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
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...(activeRole ? { "X-Demo-Role": activeRole } : {}) },
        body: JSON.stringify({ query: question }),
        signal: AbortSignal.timeout(90_000),
      });
      setResult(await readResponse<QueryResult>(response));
    } catch (cause) {
      setError(networkMessage(cause, "The answer could not be generated."));
    } finally {
      setPending(false);
    }
  }

  async function openSource(citation: Citation, trigger: HTMLElement) {
    if (sourceCloseTimer.current !== null) window.clearTimeout(sourceCloseTimer.current);
    setSourceClosing(false);
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
    const requestedRole = activeRole;
    try {
      const source = await apiGet<SourcePreview>(`/api/v1/sources/${encodeURIComponent(citation.citation_id)}`, activeRole || undefined);
      if (activeRoleRef.current === requestedRole) setActiveSource(source);
    } catch (cause) {
      setSourceError(cause instanceof Error ? cause.message : "This source is unavailable.");
    }
  }

  async function openDocument(source: Source, trigger: HTMLElement) {
    if (sourceCloseTimer.current !== null) window.clearTimeout(sourceCloseTimer.current);
    setSourceClosing(false);
    sourceTrigger.current = trigger;
    setActiveSource({
      citation_id: source.id,
      source_type: source.source_type,
      title: source.source_name,
      source_id: source.id,
      location: {},
      excerpt: "Loading the first authorized excerpt…",
    });
    setSourceError(null);
    const requestedRole = activeRole;
    try {
      const preview = await apiGet<SourcePreview>(`/api/v1/sources/${encodeURIComponent(source.id)}/preview`, activeRole || undefined);
      if (activeRoleRef.current === requestedRole) setActiveSource(preview);
    } catch (cause) {
      setSourceError(networkMessage(cause, "This source is unavailable."));
    }
  }

  const switchDemoUser = useCallback(async (role: string) => {
    if (!workspace?.demo_switch_available || pending) return;
    setPending(true);
    setError(null);
    try {
      const token = await currentToken();
      if (!token) throw new Error("Your session expired. Sign in again to continue.");
      const switched = await readResponse<{ active_role: string }>(await fetch(`${API_BASE}/api/v1/demo/switch`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...(activeRole ? { "X-Demo-Role": activeRole } : {}) },
        body: JSON.stringify({ role }),
      }));
      activeRoleRef.current = switched.active_role;
      setActiveRole(switched.active_role);
      window.localStorage.setItem("clearframe-demo-role", switched.active_role);
      setResult(null);
      setSources(null);
      setSecurity(null);
      setEvaluation(null);
      if (sourceCloseTimer.current !== null) window.clearTimeout(sourceCloseTimer.current);
      setActiveSource(null);
      setSourceClosing(false);
      setWorkspace(null);
    } catch (cause) {
      setError(networkMessage(cause, "Could not switch the demo account."));
    } finally {
      setPending(false);
    }
  }, [activeRole, pending, workspace?.demo_switch_available]);

  useEffect(() => {
    if (!workspace || activeRole || roleRestoreStarted.current) return;
    roleRestoreStarted.current = true;
    const stored = workspace.demo_switch_available
      ? window.localStorage.getItem("clearframe-demo-role")
      : null;
    const role = stored && DEMO_ROLES.includes(stored) ? stored : workspace.active_role;
    const timer = window.setTimeout(() => {
      if (role === workspace.active_role) {
        activeRoleRef.current = role;
        setActiveRole(role);
      } else void switchDemoUser(role);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [activeRole, switchDemoUser, workspace]);

  async function signOut() {
    const { error: signOutError } = await createClient().auth.signOut();
    if (signOutError) {
      setError("Could not log out. Check your connection and try again.");
      return;
    }
    router.replace("/login");
    router.refresh();
  }

  const loadSources = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      const data = await apiGet<{ sources: Source[] }>("/api/v1/sources", activeRole || undefined);
      if (!activeRoleRef.current || activeRoleRef.current === activeRole) setSources(data.sources);
    } catch (cause) {
      setError(networkMessage(cause, "Authorized sources are unavailable."));
    } finally {
      setPending(false);
    }
  }, [activeRole]);

  const loadSecurity = useCallback(async () => {
    setPending(true);
    setError(null);
    try { setSecurity(await apiGet<SecurityData>("/api/v1/security", activeRole || undefined)); }
    catch (cause) { setError(networkMessage(cause, "Security status is unavailable.")); }
    finally { setPending(false); }
  }, [activeRole]);

  const loadEvaluation = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      const data = await apiGet<{ state: string; result: EvaluationData | null }>("/api/v1/evaluation", activeRole || undefined);
      setEvaluation(data.result);
    } catch (cause) { setError(networkMessage(cause, "Evaluation state is unavailable.")); }
    finally { setPending(false); }
  }, [activeRole]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (view === "Sources" && sources === null) void loadSources();
      if (view === "Security" && security === null) void loadSecurity();
      if (view === "Evaluation" && evaluation === null) void loadEvaluation();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [evaluation, loadEvaluation, loadSecurity, loadSources, security, sources, view]);

  function selectView(nextView: View) {
    setError(null);
    setNavigationOpen(false);
    if (pathname !== viewRoutes[nextView]) router.push(viewRoutes[nextView]);
  }

  async function uploadFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ingestFile) return;
    const fileInput = event.currentTarget.querySelector<HTMLInputElement>('input[type="file"]');
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
          ...(activeRole ? { "X-Demo-Role": activeRole } : {}),
        },
        body: ingestFile,
        signal: AbortSignal.timeout(180_000),
      });
      const payload = await readResponse<{ chunks_indexed: number; source_name: string }>(response);
      setIngestResult(`${payload.source_name} indexed · ${payload.chunks_indexed} chunks`);
      setIngestFile(null);
      if (fileInput) fileInput.value = "";
      await refreshWorkspace();
      setSources(null);
    } catch (cause) { setError(networkMessage(cause, "Ingestion failed. Your file is still selected; retry when the service is available.")); }
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
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...(activeRole ? { "X-Demo-Role": activeRole } : {}) },
        body: JSON.stringify({ table: structuredMeta.table, row_id: structuredMeta.rowId, source_name: structuredMeta.sourceName, fields, access_role: structuredMeta.accessRole }),
        signal: AbortSignal.timeout(90_000),
      });
      const payload = await readResponse<{ chunks_indexed: number; source_name: string }>(response);
      setIngestResult(`${payload.source_name} indexed · ${payload.chunks_indexed} chunks`);
      await refreshWorkspace();
      setSources(null);
    } catch (cause) {
      setError(networkMessage(cause, "Structured record indexing failed. Check the fields and retry."));
    } finally { setPending(false); }
  }

  async function runEvaluation() {
    setPending(true);
    setError(null);
    try {
      const token = await currentToken();
      if (!token) throw new Error("Your session expired. Sign in again to continue.");
      const payload = await readResponse<{ result: EvaluationData }>(await fetch(`${API_BASE}/api/v1/evaluation/run`, {
        method: "POST", headers: { Authorization: `Bearer ${token}`, ...(activeRole ? { "X-Demo-Role": activeRole } : {}) },
      }));
      setEvaluation(payload.result);
    } catch (cause) { setError(networkMessage(cause, "The evaluation run failed.")); }
    finally { setPending(false); }
  }

  const role = activeRole || workspace?.active_role || workspace?.identity.role || "Loading";
  const userName = workspace?.identity.display_name ?? identity;
  const filteredSources = (sources ?? []).filter((source) =>
    (sourceTypeFilter === "all" || source.source_type === sourceTypeFilter)
      && `${source.source_name} ${source.source_type} ${source.id}`.toLocaleLowerCase().includes(sourceFilter.trim().toLocaleLowerCase()),
  );

  function setSelectedTheme(next: "light" | "dark") {
    document.documentElement.dataset.theme = next;
    window.localStorage.setItem("clearframe-theme", next);
    window.dispatchEvent(new Event("clearframe-theme-change"));
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <button className="icon-button mobile-menu-button" type="button" aria-label={navigationOpen ? "Close navigation" : "Open navigation"} aria-expanded={navigationOpen} onClick={() => setNavigationOpen((open) => !open)}>
            <Icon name={navigationOpen ? "close" : "menu"} size={21} />
          </button>
          <span className="brand-name">Clearframe</span>
        </div>
        <div className="topbar-context" aria-hidden="true" />
        <div className="topbar-state"><span className="workspace-indicator"><i />Workspace</span></div>
      </header>

      <div className="workspace-grid">
        <aside className={`navigation-rail ${navigationOpen ? "navigation-open" : ""}`}>
          <div className="rail-workspace-label">Workspace</div>
          <nav className="primary-navigation" aria-label="Workspace">
            {navigation.map(({ label, icon }) => (
              <Link className={`navigation-item ${view === label ? "navigation-item-active" : ""}`} href={viewRoutes[label]} key={label} aria-current={view === label ? "page" : undefined} onClick={() => { setError(null); setNavigationOpen(false); }}>
                <Icon name={icon} size={19} /><span>{label}</span>
              </Link>
            ))}
          </nav>
          <div className="rail-footer">
          <p className="rail-security-note"><Icon name="lock" size={14} />Access follows the active demo context.</p>
            <details className="account-menu" open={accountOpen} onToggle={(event) => setAccountOpen((event.currentTarget as HTMLDetailsElement).open)}>
              <summary className="account-trigger" aria-label={`Account menu for ${userName}`}>
                <span className="account-avatar">{userName.slice(0, 1).toUpperCase()}</span>
                <span className="account-identity"><strong>{userName}</strong><small>Active context · {role}</small></span>
                <Icon name="chevron" size={16} />
              </summary>
              <div className="account-popover">
                <p className="account-current"><strong>Authenticated identity · {userName}</strong><span>{workspace?.identity.email ?? identity}</span><small>Active demo context · {role}</small></p>
                {workspace?.demo_switch_available && <label className="field-label account-role-field">Switch demo role<select aria-label="Switch demo role" value={DEMO_ROLES.includes(role) ? role : "CEO"} disabled={pending} onChange={(event) => void switchDemoUser(event.target.value)}>{DEMO_ROLES.map((demoRole) => <option key={demoRole}>{demoRole}</option>)}</select></label>}
                <button className="account-action" type="button" onClick={() => setSelectedTheme(theme === "light" ? "dark" : "light")}>{theme === "light" ? "Use dark theme" : "Use light theme"}</button>
                <button className="account-action account-logout" type="button" onClick={() => void signOut()}>Log out</button>
              </div>
            </details>
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
              onRetry={() => void ask()}
              onSource={openSource}
            />
          ) : view === "Dashboard" ? (
            <DashboardView data={workspace} error={error} onRefresh={() => void refreshWorkspace()} onNavigate={selectView} />
          ) : view === "Sources" ? (
            <SourcesView sources={filteredSources} filter={sourceFilter} onFilter={setSourceFilter} typeFilter={sourceTypeFilter} onTypeFilter={setSourceTypeFilter} pending={pending} error={error} onOpen={(source, trigger) => { void openDocument(source, trigger); }} onRefresh={() => { setSources(null); void loadSources(); }} />
          ) : view === "Ingest" ? (
            <IngestView
              role={role}
              available={workspace?.ingestion === "ready"}
              error={error}
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
        <button type="button" className="drawer-scrim" aria-label="Close source details" onClick={closeSource} />
        <aside className="source-drawer" data-closing={sourceClosing || undefined} role="dialog" aria-modal="true" aria-labelledby="source-drawer-title" onKeyDown={(event: KeyboardEvent<HTMLElement>) => { if (event.key === "Tab") { event.preventDefault(); sourceClose.current?.focus(); } }}>
          <header className="drawer-heading">
            <div><h2 id="source-drawer-title">Source evidence</h2><p>Authorized source lookup</p></div>
            <button ref={sourceClose} className="icon-button" type="button" aria-label="Close source details" onClick={closeSource}><Icon name="close" /></button>
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

function AskView({ identity, role, query, setQuery, askedQuery, result, pending, error, onSubmit, onRetry, onSource }: {
  identity: string; role: string; query: string; setQuery: (value: string) => void; askedQuery: string;
  result: QueryResult | null; pending: boolean; error: string | null;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onRetry: () => void;
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
          <div className="answer-foot"><span className="grounded-state"><Icon name="lock" size={14} />{result.state === "CITATION_VALIDATED" ? "Citations and excerpt matches checked" : "Partially validated"}</span><span>{result.trace.evidence_items_sent_to_model} authorized evidence items</span>{result.trace.generation_model && <span>{result.trace.generation_model}{result.trace.fallback_used ? " · fallback" : ""}</span>}<span className="answer-latency" title="Database ranking is included in retrieval timing">Total {formatLatency(result.trace.timing_ms.total_ms)} · retrieval + ranking {formatLatency(result.trace.timing_ms.retrieval_and_ranking_ms)}</span>
            {refs.length > 0 && <button className="view-sources" type="button" onClick={(event) => onSource(refs[0], event.currentTarget)}>View sources <Icon name="arrow" size={15} /></button>}
          </div>
          <p className="trace-disclaimer">Source IDs and exact excerpt matches were checked; semantic claim entailment is not verified.</p>
          <details className="latency-details"><summary>Timing details</summary><span>Session/auth {formatLatency(result.trace.timing_ms.auth_session_ms)} · embedding {formatLatency(result.trace.timing_ms.embedding_ms)} · retrieval + database ranking {formatLatency(result.trace.timing_ms.retrieval_and_ranking_ms)} · ranking alone not exposed · Gemini {formatLatency(result.trace.timing_ms.gemini_ms)} · citation checks {formatLatency(result.trace.timing_ms.citation_validation_ms)} · total {formatLatency(result.trace.timing_ms.total_ms)}</span></details>
        </div></div>}
      </div> : <div className="empty-conversation"><div className="empty-mark" aria-hidden="true"><Icon name="chat" size={22} /></div><p>Ask about a document, image, or business record.</p><div className="question-examples" aria-label="Example questions">{exampleQuestions.map((example) => <button className="sample-question" type="button" key={example} onClick={() => setQuery(example)}><span>{example}</span><Icon name="arrow" size={17} /></button>)}</div></div>}
      {pending && <p className="request-status" role="status"><span className="loading-dot" />Checking your session, searching authorized sources, and preparing a cited answer…</p>}
      {error && <div className="request-error" role="alert"><p>{error}</p><button className="text-button" type="button" disabled={pending} onClick={onRetry}>Retry question</button></div>}
    </div>
    <div className="composer-wrap"><form className="composer" onSubmit={onSubmit}><label className="sr-only" htmlFor="query-input">Ask a question</label><textarea id="query-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ask a question about your knowledge..." maxLength={2000} rows={2} disabled={pending} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} /><div className="composer-actions"><span className="composer-note">{pending ? "Please wait; duplicate requests are disabled." : "Enter to ask · Shift + Enter for a new line"}</span><button className="send-button" type="submit" disabled={!query.trim() || pending}><Icon name="send" size={17} /><span>{pending ? "Searching" : "Ask"}</span></button></div></form></div>
  </>;
}

function DashboardView({ data, error, onRefresh, onNavigate }: { data: WorkspaceData | null; error: string | null; onRefresh: () => void; onNavigate: (view: View) => void }) {
  if (!data) return <PageState title="Dashboard" error={error} pending={!error} onRefresh={onRefresh} />;
  return <div className="data-page"><PageHeading title="Dashboard" description="Live state from your authenticated Clearframe workspace." action={<button className="quiet-button" type="button" onClick={onRefresh}>Refresh</button>} />
    <div className="dashboard-identity"><span className="user-indicator">{data.identity.display_name.slice(0, 1).toUpperCase()}</span><div><strong>Authenticated · {data.identity.display_name}</strong><span>{data.identity.email} · Active context: {data.active_role}</span></div><span className="status-pill status-good">Authorization {data.authorization}</span></div>
    <dl className="metric-strip"><Metric label="Authorized sources" value={data.document_count} /><Metric label="Searchable chunks" value={data.chunk_count} /><Metric label="Structured records" value={data.structured_record_count} /></dl>
    <div className="dashboard-shortcuts" aria-label="Workspace shortcuts">{(["Ask", "Sources", "Ingest", "Security", "Evaluation"] as const).map((item) => <button className="quiet-button" key={item} type="button" onClick={() => onNavigate(item)}>{item}</button>)}</div>
    <div className="dashboard-columns"><section className="data-section"><SectionTitle title="System connections" /><div className="connection-list"><StatusRow label="API" value={data.api} /><StatusRow label="Supabase" value={data.supabase} /><StatusRow label="Gemini" value={data.gemini} /><StatusRow label="Ingestion" value={data.ingestion} /><StatusRow label="Latest evaluation" value={data.latest_evaluation_status} /></div></section>
      <section className="data-section"><SectionTitle title="Recent queries" action={<button className="text-button" type="button" onClick={() => onNavigate("Ask")}>Ask a question</button>} />{data.recent_queries.length ? <ol className="recent-query-list">{data.recent_queries.slice(0, 6).map((item, index) => <li key={`${item.created_at}-${index}`}><span>{item.query}</span><small>{item.state.replaceAll("_", " ")} · {formatTime(item.created_at)}</small></li>)}</ol> : <p className="empty-note">No queries in this API session yet.</p>}</section></div>
  </div>;
}

function SourcesView({ sources, filter, onFilter, typeFilter, onTypeFilter, pending, error, onOpen, onRefresh }: {
  sources: Source[] | null; filter: string; onFilter: (value: string) => void; typeFilter: string; onTypeFilter: (value: string) => void; pending: boolean; error: string | null;
  onOpen: (source: Source, trigger: HTMLElement) => void; onRefresh: () => void;
}) {
  if (!sources) return <PageState title="Sources" pending={pending} error={error} onRefresh={onRefresh} />;
  return <div className="data-page"><PageHeading title="Sources" description="Only documents visible under your current database policies appear here." action={<button className="quiet-button" type="button" onClick={onRefresh}>Refresh</button>} />
    <div className="sources-toolbar"><div className="sources-filters"><label className="source-search"><Icon name="search" size={16} /><span className="sr-only">Filter authorized sources</span><input value={filter} onChange={(event) => onFilter(event.target.value)} placeholder="Search authorized names or IDs" /></label><label className="source-type-filter"><span className="sr-only">Filter by source type</span><select value={typeFilter} onChange={(event) => onTypeFilter(event.target.value)}><option value="all">All types</option><option value="pdf">PDF</option><option value="image_ocr">Image / OCR</option><option value="structured">Structured record</option></select></label></div><p className="list-count">{sources.length} authorized {sources.length === 1 ? "source" : "sources"}</p></div>
    {sources.length ? <div className="source-table-wrap"><table className="source-table"><thead><tr><th>Source</th><th>Type</th><th>Added</th><th>Ingested chunks</th><th><span className="sr-only">Open source</span></th></tr></thead><tbody>{sources.map((source) => <tr key={source.id}><td><strong>{source.source_name}</strong><small>{source.id}</small></td><td><span className={`source-kind source-kind-${source.source_type}`}>{sourceTypeLabel(source.source_type)}</span></td><td>{formatTime(source.created_at)}</td><td>{typeof source.metadata.chunk_count === "number" ? source.metadata.chunk_count : "—"}</td><td><button className="text-button" type="button" onClick={(event) => onOpen(source, event.currentTarget)}>Open</button></td></tr>)}</tbody></table></div> : <div className="empty-state"><Icon name="files" size={22} /><h2>{filter ? "No matching sources" : "No authorized sources yet"}</h2><p>{filter ? "Try a different name, type, or source ID." : "Sources added for your role will appear here after ingestion."}</p></div>}
  </div>;
}

function IngestView({ role, available, error, accessRole, setAccessRole, file, setFile, result, pending, structuredMeta, setStructuredMeta, structuredJson, setStructuredJson, onUpload, onStructured }: {
  role: string; available: boolean; error: string | null; accessRole: string; setAccessRole: (role: string) => void; file: File | null; setFile: (file: File | null) => void; result: string | null; pending: boolean;
  structuredMeta: { table: string; rowId: string; sourceName: string; accessRole: string }; setStructuredMeta: (update: Partial<{ table: string; rowId: string; sourceName: string; accessRole: string }>) => void;
  structuredJson: string; setStructuredJson: (value: string) => void; onUpload: (event: FormEvent<HTMLFormElement>) => void; onStructured: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const canIngest = available && role === "CEO";
  return <div className="data-page"><PageHeading title="Ingest" description="Index source files and structured records into the secured knowledge store." />
    {!available && <div className="inline-notice" role="status"><Icon name="lock" size={17} /><span>The local ingestion service is unavailable. Confirm the local API and Supabase are running.</span></div>}
    {available && role !== "CEO" && <div className="inline-notice" role="status"><Icon name="lock" size={17} /><span>Ingestion is restricted to the CEO demo account. Your current role remains read-only.</span></div>}
    {error && <p className="request-error" role="alert">{error}</p>}
    <div className={`ingest-progress ${error ? "ingest-failed" : result ? "ingest-indexed" : ""}`} role="status"><strong>{error ? "Failed" : result ? "Indexed" : pending ? "Indexing source…" : file ? "Ready to upload" : "Ready"}</strong><span>{error ? "Your selected file or record remains available to retry." : result ?? (pending ? "The API processes and indexes this source before returning; per-stage progress is not available." : "PDF, PNG, JPEG, or structured records can be indexed here.")}</span></div>
    <div className="ingest-columns"><form className="ingest-form" onSubmit={onUpload}><div className="form-title"><Icon name="upload" size={18} /><div><h2>Document or image</h2><p>PDF, PNG, or JPEG · up to 25 MB</p></div></div>
      <label className="file-drop"><input type="file" accept="application/pdf,image/png,image/jpeg,.pdf,.png,.jpg,.jpeg" disabled={!canIngest || pending} onChange={(event) => { const selected = event.target.files?.[0] ?? null; const extension = selected?.name.toLowerCase().split(".").pop(); if (selected && (!extension || !["pdf", "png", "jpg", "jpeg"].includes(extension) || selected.size === 0 || selected.size > 25 * 1024 * 1024)) { setFile(null); event.currentTarget.value = ""; return; } setFile(selected); }} /><Icon name="files" size={20} /><strong>{file?.name ?? "Choose a source file"}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : "PDF text and scanned pages, or image OCR · max 25 MB"}</span></label>
      <label className="field-label">Grant source to<select value={accessRole} disabled={!canIngest || pending} onChange={(event) => setAccessRole(event.target.value)}>{DEMO_ROLES.map((value) => <option key={value}>{value}</option>)}</select></label>
      <button className="primary-action" type="submit" disabled={!canIngest || pending || !file}>{pending ? "Uploading and indexing…" : "Upload and index"}</button>
      <p className="form-footnote">Files are stored in the local private ingestion folder. The selected role is the only role granted access.</p>
    </form>
    <form className="ingest-form" onSubmit={onStructured}><div className="form-title"><Icon name="table" size={18} /><div><h2>Structured record</h2><p>Canonical text and embeddings are generated server-side.</p></div></div>
      <div className="field-pair"><label className="field-label">Table<input value={structuredMeta.table} disabled={!canIngest || pending} onChange={(event) => setStructuredMeta({ table: event.target.value })} required /></label><label className="field-label">Row ID<input value={structuredMeta.rowId} disabled={!canIngest || pending} onChange={(event) => setStructuredMeta({ rowId: event.target.value })} required /></label></div>
      <label className="field-label">Source name<input value={structuredMeta.sourceName} disabled={!canIngest || pending} onChange={(event) => setStructuredMeta({ sourceName: event.target.value })} required /></label>
      <label className="field-label">Record fields<textarea className="json-input" value={structuredJson} disabled={!canIngest || pending} onChange={(event) => setStructuredJson(event.target.value)} spellCheck={false} aria-describedby="structured-json-help" /></label><small className="field-hint" id="structured-json-help">JSON object with scalar values: strings, numbers, booleans, or null.</small>
      <label className="field-label">Grant source to<select value={structuredMeta.accessRole} disabled={!canIngest || pending} onChange={(event) => setStructuredMeta({ accessRole: event.target.value })}>{DEMO_ROLES.map((value) => <option key={value}>{value}</option>)}</select></label>
      <button className="primary-action" type="submit" disabled={!canIngest || pending}>{pending ? "Indexing record…" : "Index structured record"}</button>
    </form></div>
  </div>;
}

function SecurityView({ data, pending, error, onRefresh }: { data: SecurityData | null; pending: boolean; error: string | null; onRefresh: () => void }) {
  if (!data) return <PageState title="Security" pending={pending} error={error} onRefresh={onRefresh} />;
  return <div className="data-page"><PageHeading title="Security" description="Identity and authorization decisions from the current API session." action={<button className="quiet-button" type="button" onClick={onRefresh}>Refresh trace</button>} />
    <div className="security-identity"><span className="security-mark"><Icon name="lock" size={20} /></span><div><strong>Authenticated · {data.identity.display_name}</strong><span>{data.identity.email} · Active demo context: {data.active_role}</span></div><span className="status-pill status-good">Session verified</span></div>
    <section className="data-section"><SectionTitle title="Effective access scope" /><p className="scope-copy">{data.effective_scope}</p><div className="security-checks">{Object.entries(data.security_tests).map(([label, value]) => <div key={label}><span>{label.replaceAll("_", " ")}</span><strong>{String(value)}</strong></div>)}</div></section>
    <section className="data-section"><SectionTitle title="Retrieval authorization boundary" /><div className="security-flow"><span>Identity</span><b>→</b><span>Authorization</span><b>→</b><span>Secure retrieval</span><b>→</b><span>Authorized evidence</span><b>→</b><span>Generation</span></div><p className="trace-disclaimer">Architectural design: retrieval uses the validated user or server-brokered demo-role session. Unauthorized evidence supplied to the model: not independently measured in this trace. The endpoint does not probe hosted RLS status.</p></section>
    <section className="data-section"><SectionTitle title="Recent retrieval decisions" /><ol className="trace-list">{data.trace.length ? data.trace.map((entry) => <li key={entry.query_id}><span className="trace-dot" /><div><strong>{entry.decision} · {entry.active_role}</strong><span>{entry.authorized_evidence_count} authorized evidence items · unauthorized evidence supplied to the model: not independently measured</span></div><time>{formatTime(entry.created_at)}</time></li>) : <li className="empty-note">Ask a question to see a real retrieval trace for this session.</li>}</ol><p className="trace-disclaimer">The trace omits source names and contents. Recent events are held in this API process and clear when it restarts.</p></section>
  </div>;
}

function EvaluationView({ data, pending, error, role, onRefresh, onRun }: { data: EvaluationData | null; pending: boolean; error: string | null; role: string; onRefresh: () => void; onRun: () => void }) {
  return <div className="data-page"><PageHeading title="Evaluation" description="Local synthetic smoke results for retrieval and authorization; not a production benchmark." action={<button className="quiet-button" type="button" onClick={onRefresh}>Refresh</button>} />
    {!data ? <div className="evaluation-empty"><Icon name="chart" size={22} />{error ? <p className="request-error" role="alert">{error}</p> : <><h2>No evaluation run recorded</h2><p>Run the real retrieval suite to measure recall, ranking, modality coverage, and authorization boundaries.</p></>}<button className="primary-action" type="button" disabled={pending || role !== "CEO"} onClick={onRun}>{pending ? "Running evaluation…" : "Run evaluation"}</button>{role !== "CEO" && <small>Switch to the CEO demo user to run the local test suite.</small>}</div> : <>
      <p className="evaluation-scope">Retrieval quality · Recall@12 {formatMetric(data.retrieval_recall_at_k)} · MRR {formatMetric(data.mean_reciprocal_rank)} <span>Authorization security · {data.authorization_violations} measured leaks</span> <span>Citation validation · {String(data.measured_checks?.citation_provenance_valid ?? "not measured")} provenance checks</span> <span>Latency · {formatLatency(data.measured_checks?.mean_latency_ms)}</span></p>
      <div className="evaluation-summary"><div><span>Dataset</span><strong>{data.dataset}</strong></div><div><span>Queries</span><strong>{data.query_count}</strong></div><div><span>Recall@12</span><strong>{formatMetric(data.retrieval_recall_at_k)}</strong></div><div><span>Mean reciprocal rank</span><strong>{formatMetric(data.mean_reciprocal_rank)}</strong></div><div><span>Authorization leaks</span><strong className={data.authorization_violations ? "metric-bad" : "metric-good"}>{data.authorization_violations}</strong></div></div>
      <div className="source-table-wrap"><table className="source-table evaluation-table"><thead><tr><th>Evaluation case</th><th>Role</th><th>Result</th><th>Latency</th><th>Forbidden hits</th></tr></thead><tbody>{data.results.map((row, index) => <tr key={`${String(row.name)}-${index}`}><td><strong>{String(row.name)}</strong></td><td>{String(row.role ?? "—")}</td><td><span className={`status-pill ${row.hit === true ? "status-good" : "status-bad"}`}>{row.hit === true ? "Pass" : "Review"}</span></td><td>{typeof row.latency_ms === "number" ? `${row.latency_ms} ms` : "—"}</td><td>{Array.isArray(row.forbidden_source_hits) ? row.forbidden_source_hits.length : "—"}</td></tr>)}</tbody></table></div>
      <p className="trace-disclaimer">Retrieved with authenticated demo users against the local database. This small synthetic run measures retrieval and row-level authorization; it does not establish representative-scale quality or semantic answer quality.{data.completed_at ? ` Completed ${formatTime(data.completed_at)}.` : ""}</p>
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
function StatusRow({ label, value }: { label: string; value: string }) { const ready = ["connected", "ready", "available"].includes(value); return <div className="connection-row"><span>{label}</span><span className={`connection-state ${ready ? "is-ready" : ""}`}><i />{value.replaceAll("_", " ")}</span></div>; }

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
function formatLatency(value: unknown) { return typeof value === "number" ? `${Math.round(value)} ms` : "—"; }
