"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type FormEvent } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Drawer } from "@/components/drawer";
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
  conversation_id?: string;
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
    history_saved?: boolean;
  };
};
type SourcePreview = {
  citation_id: string;
  source_type: string;
  title: string | null;
  source_id: string | null;
  location: Record<string, unknown>;
  excerpt: string;
  record_fields?: Record<string, unknown>;
  preview_path?: string | null;
  access?: string;
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
  retrieval_hit_rate_at_k: number;
  top_k: number;
  positive_query_count?: number;
  run_kind: "historical_legacy" | "recorded_local" | "fresh_local";
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
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [traceOpen, setTraceOpen] = useState(false);
  const [stage, setStage] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [turns, setTurns] = useState<{ query: string; response: QueryResult }[]>([]);
  const [conversations, setConversations] = useState<{ id: string; title: string; updated_at: string }[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
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
  const [structuredJson, setStructuredJson] = useState(JSON.stringify({ invoice_id: "INV-2049", customer_id: "CUST-ACM-1001", customer: "Acme Manufacturing", currency: "USD", total_minor_units: 120000, invoice_date: "2026-10-01", due_date: "2026-10-31", payment_status: "unpaid", status_as_of: "2026-10-09" }, null, 2));
  const [structuredMeta, setStructuredMeta] = useState({ table: "invoices", rowId: "INV-2049", sourceName: "Invoice INV-2049", accessRole: "CEO" });
  const [ingestFile, setIngestFile] = useState<File | null>(null);
  const [ingestResult, setIngestResult] = useState<string | null>(null);
  const sourceRequest = useRef(0);
  const navigationRef = useRef<HTMLElement>(null);
  const roleRestoreStarted = useRef(false);
  const activeRoleRef = useRef("");
  const sourceOpen = activeSource !== null;
  const closeSource = useCallback(() => {
    sourceRequest.current += 1;
    setActiveSource(null);
    setSourceError(null);
  }, []);

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
  async function ask(event?: FormEvent<HTMLFormElement>, retryQuestion?: string) {
    event?.preventDefault();
    const question = (retryQuestion ?? query).trim();
    if (!question || pending) return;
    setPending(true);
    setError(null);
    setResult(null);
    setActiveSource(null);
    setAskedQuery(question);
    setStage("connecting");
    try {
      const token = await currentToken();
      if (!token) {
        router.replace("/login");
        return;
      }
      const response = await fetch(`${API_BASE}/api/v1/chat/stream`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...(activeRole ? { "X-Demo-Role": activeRole } : {}) },
        body: JSON.stringify({ query: question, ...(conversationId ? { conversation_id: conversationId } : {}) }),
        signal: AbortSignal.timeout(90_000),
      });
      if (!response.ok) await readResponse(response);
      const reader = response.body?.getReader();
      if (!reader) throw new Error("The response stream is unavailable.");
      const decoder = new TextDecoder();
      let buffer = "";
      let complete = false;
      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value, { stream: !done });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          const kind = frame.split("\n").find((line) => line.startsWith("event:"))?.slice(6).trim();
          const data = frame.split("\n").filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n");
          if (!data) continue;
          const payload = JSON.parse(data);
          if (kind === "progress") setStage(payload.stage);
          if (kind === "error") throw new Error(payload.code === "provider_rate_limited"
            ? "Answer generation is rate-limited. Retry later."
            : "The answer service is unavailable. No unvalidated answer was released.");
          if (kind === "result") {
            setResult(payload);
            setConversationId(payload.conversation_id ?? null);
            setTurns((previous) => [...previous, { query: question, response: payload }]);
            setQuery("");
            complete = true;
          }
        }
        if (done) break;
      }
      if (!complete) throw new Error("The response ended before a validated answer arrived.");
      void loadHistory();
    } catch (cause) {
      setError(networkMessage(cause, "The answer could not be generated."));
    } finally {
      setPending(false);
    }
  }

  async function openSource(citation: Citation, trigger: HTMLElement) {
    const requestNumber = ++sourceRequest.current;
    trigger.focus();
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
      if (sourceRequest.current === requestNumber && activeRoleRef.current === requestedRole) setActiveSource(source);
    } catch (cause) {
      if (sourceRequest.current === requestNumber && activeRoleRef.current === requestedRole) setSourceError(cause instanceof Error ? cause.message : "This source is unavailable.");
    }
  }

  async function openDocument(source: Source, trigger: HTMLElement) {
    const requestNumber = ++sourceRequest.current;
    trigger.focus();
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
      if (sourceRequest.current === requestNumber && activeRoleRef.current === requestedRole) setActiveSource(preview);
    } catch (cause) {
      if (sourceRequest.current === requestNumber && activeRoleRef.current === requestedRole) setSourceError(networkMessage(cause, "This source is unavailable."));
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
      sourceRequest.current += 1;
      setActiveSource(null);
      setTraceOpen(false);
      setTurns([]);
      setResult(null);
      setAskedQuery("");
      setConversationId(null);
      setConversations([]);
      setAccountOpen(false);
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

  async function loadHistory() {
    try {
      const data = await apiGet<{ conversations: typeof conversations }>("/api/v1/conversations", activeRole || undefined);
      if (activeRoleRef.current === activeRole) setConversations(data.conversations);
      setHistoryError(null);
    } catch { setHistoryError("Conversation history is unavailable. This requires the current database migration."); }
  }

  async function reopenConversation(id: string) {
    if (pending) return;
    try {
      const data = await apiGet<{ turns: { query: string; response: QueryResult }[] }>(`/api/v1/conversations/${id}`, activeRole || undefined);
      if (activeRoleRef.current !== activeRole) return;
      setTurns(data.turns);
      setConversationId(id);
      const last = data.turns.at(-1);
      setResult(last?.response ?? null);
      setAskedQuery(last?.query ?? "");
      setQuery("");
      setHistoryOpen(false);
    } catch (cause) { setHistoryError(networkMessage(cause, "Conversation is outside your current access scope.")); }
  }

  async function removeConversation(id: string) {
    try {
      const token = await currentToken();
      await readResponse(await fetch(`${API_BASE}/api/v1/conversations/${id}`, {
        method: "DELETE", headers: { Authorization: `Bearer ${token}`, ...(activeRole ? { "X-Demo-Role": activeRole } : {}) },
      }));
      setConversations((previous) => previous.filter((entry) => entry.id !== id));
      if (conversationId === id) newConversation();
    } catch (cause) { setHistoryError(networkMessage(cause, "Conversation could not be removed.")); }
  }

  function newConversation() {
    if (pending) return;
    setConversationId(null); setTurns([]); setResult(null); setAskedQuery(""); setQuery(""); setError(null);
  }

  useEffect(() => {
    if (!activeSource?.preview_path || sourceError) return;
    const controller = new AbortController();
    let objectUrl: string | null = null;
    void currentToken().then(async (token) => {
      const response = await fetch(`${API_BASE}${activeSource.preview_path}`, {
        headers: { Authorization: `Bearer ${token}`, ...(activeRole ? { "X-Demo-Role": activeRole } : {}) },
        signal: controller.signal, cache: "no-store",
      });
      if (!response.ok) { setPreviewError("Original unavailable in this access context. The authorized excerpt is shown above."); return; }
      objectUrl = URL.createObjectURL(await response.blob());
      if (!controller.signal.aborted) setPreviewUrl(objectUrl);
      else URL.revokeObjectURL(objectUrl);
    }).catch(() => { if (!controller.signal.aborted) setPreviewError("Original preview could not load. Retry opening the source."); });
    return () => { controller.abort(); setPreviewUrl(null); setPreviewError(null); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [activeSource, activeRole, sourceError]);

  useEffect(() => {
    function dismiss(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") { setAccountOpen(false); setNavigationOpen(false); }
    }
    function outside(event: MouseEvent) {
      if (!(event.target as Element)?.closest(".account-menu")) setAccountOpen(false);
    }
    window.addEventListener("keydown", dismiss);
    window.addEventListener("click", outside);
    return () => { window.removeEventListener("keydown", dismiss); window.removeEventListener("click", outside); };
  }, []);

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
    try { const data = await apiGet<SecurityData>("/api/v1/security", activeRole || undefined); if (activeRoleRef.current === activeRole) setSecurity(data); }
    catch (cause) { setError(networkMessage(cause, "Security status is unavailable.")); }
    finally { setPending(false); }
  }, [activeRole]);

  const loadEvaluation = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      const data = await apiGet<{ state: string; result: EvaluationData | null }>("/api/v1/evaluation", activeRole || undefined);
      if (activeRoleRef.current === activeRole) setEvaluation(data.result);
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

  useEffect(() => {
    if (!navigationOpen) return;
    const trigger = document.activeElement;
    const rail = navigationRef.current;
    const content = document.querySelector<HTMLElement>(".main-column");
    const header = document.querySelector<HTMLElement>(".topbar");
    if (content) content.inert = true;
    if (header) header.inert = true;
    const focusable = () => Array.from(rail?.querySelectorAll<HTMLElement>('a, button:not(:disabled), summary, select:not(:disabled)') ?? []).filter((element) => element.getClientRects().length > 0);
    focusable()[0]?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); setNavigationOpen(false); }
      if (event.key === "Tab") {
        const items = focusable(); const first = items[0]; const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); if (content) content.inert = false; if (header) header.inert = false; if (trigger instanceof HTMLElement && trigger.isConnected) trigger.focus(); };
  }, [navigationOpen]);

  function setSelectedTheme(next: "light" | "dark") {
    setAccountOpen(false);
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
          <span className="brand-mark" aria-hidden="true"><Icon name="lock" size={17} /></span><span className="brand-name">Clearframe</span>
        </div>
        <div className="topbar-context"><span>Workspace</span><span className="context-separator" aria-hidden="true">/</span><strong>{view === "Dashboard" ? "Overview" : view}</strong></div>
        <div className="topbar-state"><span className="workspace-indicator"><Icon name="lock" size={14} />Protected knowledge</span></div>
      </header>

      <div className="workspace-grid">
        <aside ref={navigationRef} role={navigationOpen ? "dialog" : undefined} aria-modal={navigationOpen || undefined} aria-label={navigationOpen ? "Workspace navigation" : undefined} className={`navigation-rail ${navigationOpen ? "navigation-open" : ""}`}>
          <button className="icon-button mobile-nav-close" type="button" aria-label="Close navigation drawer" onClick={() => setNavigationOpen(false)}><Icon name="close" /></button>
          <div className="rail-workspace-label">NovaCore Industries</div>
          <nav className="primary-navigation" aria-label="Workspace">
            {navigation.map(({ label, icon }, index) => (<div key={label}>
              {[0, 2, 4].includes(index) && <div className="nav-group-label">{index === 0 ? "Workspace" : index === 2 ? "Knowledge" : "Assurance"}</div>}
              <Link className={`navigation-item ${view === label ? "navigation-item-active" : ""}`} href={viewRoutes[label]} key={label} aria-current={view === label ? "page" : undefined} onClick={() => { setError(null); setNavigationOpen(false); }}>
                <Icon name={icon} size={19} /><span>{label === "Dashboard" ? "Overview" : label}</span>
              </Link></div>
            ))}
          </nav>
          <div className="rail-footer">
          <p className="rail-security-note"><Icon name="lock" size={14} />Access follows the active demo context.</p>
            <details className="account-menu" open={accountOpen} onToggle={(event) => setAccountOpen((event.currentTarget as HTMLDetailsElement).open)}>
              <summary className="account-trigger" aria-label={`Account menu for ${userName}`}>
                <span className="account-avatar">{userName.slice(0, 1).toUpperCase()}</span>
                <span className="account-identity"><strong>{userName}</strong><small>Active context<span>{role}</span></small></span>
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
              onRetry={() => { setQuery(askedQuery); void ask(undefined, askedQuery); }}
              turns={turns}
              stage={stage}
              onTrace={() => setTraceOpen(true)}
              onNew={newConversation}
              onHistory={() => { setHistoryOpen((value) => !value); void loadHistory(); }}
              historyOpen={historyOpen}
              conversations={conversations}
              historyError={historyError}
              onReopen={reopenConversation}
              onRemove={removeConversation}
              onSource={openSource}
            />
          ) : view === "Dashboard" ? (
            <DashboardView data={workspace} error={error} onRefresh={() => void refreshWorkspace()} onNavigate={selectView} />
          ) : view === "Sources" ? (
            <SourcesView sources={sources === null ? null : filteredSources} filter={sourceFilter} onFilter={setSourceFilter} typeFilter={sourceTypeFilter} onTypeFilter={setSourceTypeFilter} pending={pending} error={error} onOpen={(source, trigger) => { void openDocument(source, trigger); }} onRefresh={() => { setSources(null); void loadSources(); }} />
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
      {sourceOpen && activeSource && <Drawer title="Source evidence" description="Authorized source inspection" onClose={closeSource}>
        {sourceError ? <p className="request-error" role="alert">This source is outside your current access scope or unavailable.</p> : <article className="drawer-source">
          <div className="drawer-source-title"><Icon name={activeSource.source_type === "structured" ? "table" : "files"} size={18} /><div><strong>{activeSource.source_type === "structured" ? "Structured record" : activeSource.title ?? "Source"}</strong><span>{formatLocation(activeSource.location)}</span></div></div>
          <dl className="source-facts"><div><dt>Type</dt><dd>{sourceTypeLabel(activeSource.source_type)}</dd></div><div><dt>Access</dt><dd>Current context · {role}</dd></div></dl>
          <p className="source-excerpt">{activeSource.excerpt}</p>
          {activeSource.record_fields && <dl className="record-preview">{Object.entries(activeSource.record_fields).map(([key, value]) => <div key={key}><dt>{key.replace("_minor_units", "").replaceAll("_", " ")}</dt><dd>{formatRecordField(key, value, activeSource.record_fields?.currency)}</dd></div>)}</dl>}
          {previewUrl && (activeSource.source_type === "pdf" ? <iframe title="Original PDF preview" className="original-preview" src={`${previewUrl}#page=${activeSource.location.page ?? 1}`} /> : <OriginalImage url={previewUrl} region={activeSource.location.region} />)}
          {previewError && <p className="request-status" role="status">{previewError}</p>}
        </article>}
        <div className="drawer-policy"><Icon name="lock" size={16} /><div><strong>Why this source is available</strong><p>Your current access includes this source. The database checks access again when you open its original.</p></div></div>
      </Drawer>}
      {traceOpen && result && <Drawer title="Retrieval trace" description="Operational steps for this answer" onClose={() => setTraceOpen(false)}>
        <div className="trace-boundary"><Icon name="lock" size={18} /><strong>Authorized evidence only</strong><p>Retrieval uses a verified user session. Only returned passages enter model context.</p></div>
        <ol className="operational-trace">{[
          ["Question", askedQuery], ["Identity", userName], ["Authorization", role],
          ["Retrieval", "Database policies applied before results are returned"],
          ["Evidence", `${result.trace.evidence_items_sent_to_model} canonical passages in context`],
          ["Generation", result.trace.generation_model ?? "Not required"],
          ["Citation validation", "Evidence IDs resolved to canonical source excerpts"],
        ].map(([label, value]) => <li key={label}><strong>{label}</strong><span>{value}</span></li>)}</ol>
        <dl className="source-facts">{Object.entries(result.trace.timing_ms).map(([key, value]) => <div key={key}><dt>{timingLabel(key)}</dt><dd>{typeof value === "number" ? `${Math.round(value)} ms` : "Not measured"}</dd></div>)}</dl>
        <p className="trace-disclaimer">Extractive evidence selection. Semantic entailment and relevance are not independently verified. Unauthorized evidence is not independently counted in this trace.</p>
      </Drawer>}

    </main>
  );
}

function AskView({ identity, role, query, setQuery, askedQuery, result, pending, error, onSubmit, onRetry, onSource, turns, stage, onTrace, onNew, onHistory, historyOpen, conversations, historyError, onReopen, onRemove }: {
  identity: string; role: string; query: string; setQuery: (value: string) => void; askedQuery: string;
  result: QueryResult | null; pending: boolean; error: string | null;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void; onRetry: () => void;
  onSource: (citation: Citation, trigger: HTMLElement) => void;
  turns: { query: string; response: QueryResult }[]; stage: string; onTrace: () => void; onNew: () => void;
  onHistory: () => void; historyOpen: boolean; conversations: { id: string; title: string; updated_at: string }[];
  historyError: string | null; onReopen: (id: string) => void; onRemove: (id: string) => void;
}) {
  const steps = ["checking_access", "searching_knowledge", "evidence_selected", "generating_response", "validating_citations", "validation_complete"];
  const stageIndex = stage === "access_checked" ? 1 : stage === "retrieval_complete" ? 2 : steps.indexOf(stage);
  const messages = turns.length ? turns : result ? [{ query: askedQuery, response: result }] : [];
  return <>
    <div className="conversation-header"><div><h1>Ask</h1><p>Ask about protected company knowledge.</p></div><div className="conversation-controls"><button className="quiet-button" type="button" disabled={pending} aria-expanded={historyOpen} onClick={onHistory}><Icon name="files" size={15} />History</button><button className="quiet-button" type="button" disabled={pending} onClick={onNew}>New conversation</button></div></div>
    <div className="ask-context"><Icon name="lock" size={14} /><span>{role}</span><span>Access checked before search</span></div>
    <div className={`ask-layout ${historyOpen ? "with-history" : ""}`}>
      {historyOpen && <aside className="conversation-history" aria-label="Conversation history"><h2>Recent conversations</h2><p>In your current access context</p>{historyError ? <p role="status">{historyError}</p> : conversations.length ? <ol>{conversations.map((entry) => <li key={entry.id}><button type="button" disabled={pending} onClick={() => onReopen(entry.id)}><strong>{entry.title}</strong><small>{formatTime(entry.updated_at)}</small></button><button className="history-remove" type="button" disabled={pending} aria-label={`Remove conversation ${entry.title}`} onClick={() => onRemove(entry.id)}><Icon name="close" size={14} /></button></li>)}</ol> : <p>No conversations saved yet.</p>}</aside>}
      <div className="ask-main"><div className="conversation-scroll">
      {messages.length ? <div className="message-thread" aria-live="polite">{messages.map((turn) => <div className="conversation-turn" key={turn.response.request_id}>
        <div className="question-bubble"><span className="message-avatar user-avatar" aria-hidden="true">{identity.slice(0, 1).toUpperCase()}</span><p>{turn.query}</p></div>
        {turn.response.state === "INSUFFICIENT_EVIDENCE" ? <div className="preview-response"><div className="answer-avatar" aria-hidden="true"><Icon name="lock" size={15} /></div><div><p className="response-primary">Insufficient authorized evidence</p><p className="response-secondary">I couldn’t find enough evidence within your current access. Try a more specific question or contact your workspace administrator.</p></div></div> : <div className="answer-block"><div className="answer-avatar" aria-hidden="true">C</div><div className="answer-copy"><h2 className="answer-label">From your authorized sources</h2>
        {turn.response.claims.map((claim, index) => <p key={index}>{claim.text} {claim.citations.map((citation, citationIndex) => <button className="inline-citation" key={`${citation.citation_id}-${citationIndex}`} type="button" aria-label={`Open evidence ${citationNumber(turn.response.claims, citation.citation_id)}: ${citation.title ?? "Source"}`} onClick={(event) => onSource(citation, event.currentTarget)}>[{citationNumber(turn.response.claims, citation.citation_id)}]</button>)}</p>)}
        <div className="answer-foot"><span className="grounded-state"><Icon name="lock" size={14} />Canonical excerpts · source checked</span><button className="text-button" type="button" onClick={(event) => { const citation = turn.response.claims[0]?.citations[0]; if (citation) onSource(citation, event.currentTarget); }}>View evidence</button></div>
        {turn.response.trace.history_saved === false && <p className="response-secondary">This answer could not be saved to history.</p>}
        </div></div>}
      </div>)}</div> : !pending && !error && <div className="empty-conversation"><div className="empty-mark" aria-hidden="true"><Icon name="files" size={24} /></div><h2>What would you like to know?</h2><p>Find answers in contracts, scanned documents, and business records.</p><div className="question-examples" aria-label="Example questions">{exampleQuestions.map((example) => <button className="sample-question" type="button" key={example} onClick={() => setQuery(example)}><span>{example}</span><Icon name="arrow" size={17} /></button>)}</div></div>}
      {(pending || error) && askedQuery && <div className="question-bubble pending-question"><span className="message-avatar user-avatar" aria-hidden="true">{identity.slice(0, 1).toUpperCase()}</span><p>{askedQuery}</p></div>}
      {pending && <ol className="query-progress" aria-label="Request progress" aria-live="polite">{["Checking access", "Searching protected knowledge", "Selecting evidence", "Generating response", "Validating citations"].map((label, index) => <li key={label} data-state={index < stageIndex ? "done" : index === stageIndex ? "active" : "waiting"}><span>{index < stageIndex ? "✓" : "○"}</span>{label}</li>)}</ol>}
      {error && <div className="request-error" role="alert"><p>{error}</p><button className="text-button" type="button" disabled={pending} onClick={onRetry}>Retry question</button></div>}
      {result && !pending && <button className="trace-control text-button" type="button" onClick={onTrace}>View retrieval trace <Icon name="arrow" size={14} /></button>}
      </div>
      <div className="composer-wrap"><form className="composer" onSubmit={onSubmit}><label className="sr-only" htmlFor="query-input">Ask a question</label><textarea id="query-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ask about your company knowledge…" maxLength={2000} rows={2} disabled={pending} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} /><div className="composer-actions"><span className="composer-note">{pending ? "Waiting for a verified response" : "Enter to ask · Shift + Enter for a new line"}</span><button className="send-button" type="submit" disabled={!query.trim() || pending}><Icon name="send" size={17} /><span>{pending ? "Processing" : "Ask"}</span></button></div></form><p className="composer-policy">Answers show canonical source excerpts. Open evidence to inspect the original.</p></div>
      </div>
    </div>
  </>;
}

function DashboardView({ data, error, onRefresh, onNavigate }: { data: WorkspaceData | null; error: string | null; onRefresh: () => void; onNavigate: (view: View) => void }) {
  if (!data) return <PageState title="Overview" error={error} pending={!error} onRefresh={onRefresh} />;
  return <div className="data-page"><PageHeading title="Overview" description="NovaCore Industries · Your protected knowledge workspace." action={<button className="quiet-button" type="button" onClick={onRefresh}>Refresh</button>} />
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
  return <div className="data-page"><PageHeading title="Sources" description="Documents and business records within your current access." action={<button className="quiet-button" type="button" onClick={onRefresh}>Refresh</button>} />
    <div className="sources-toolbar"><div className="sources-filters"><label className="source-search"><Icon name="search" size={16} /><span className="sr-only">Filter authorized sources</span><input value={filter} onChange={(event) => onFilter(event.target.value)} placeholder="Search authorized names or IDs" /></label><label className="source-type-filter"><span className="sr-only">Filter by source type</span><select value={typeFilter} onChange={(event) => onTypeFilter(event.target.value)}><option value="all">All types</option><option value="pdf">PDF</option><option value="image_ocr">Image / OCR</option><option value="structured">Structured record</option></select></label></div><p className="list-count">{sources.length} authorized {sources.length === 1 ? "source" : "sources"}</p></div>
    {sources.length ? <div className="source-table-wrap"><table className="source-table knowledge-table"><thead><tr><th>Source</th><th>Type</th><th>Added</th><th>Ingested chunks</th><th><span className="sr-only">Open source</span></th></tr></thead><tbody>{sources.map((source) => <tr key={source.id}><td><strong>{source.source_name}</strong><small>{typeof source.metadata.table === "string" ? source.metadata.table : "Protected source"}</small><button className="text-button mobile-source-open" type="button" onClick={(event) => onOpen(source, event.currentTarget)}>Open source</button></td><td><span className={`source-kind source-kind-${source.source_type}`}>{sourceTypeLabel(source.source_type)}</span></td><td>{formatTime(source.created_at)}</td><td>{typeof source.metadata.chunk_count === "number" ? source.metadata.chunk_count : "—"}</td><td><button className="text-button" type="button" onClick={(event) => onOpen(source, event.currentTarget)}>Open</button></td></tr>)}</tbody></table></div> : <div className="empty-state"><Icon name="files" size={22} /><h2>{filter ? "No matching sources" : "No authorized sources yet"}</h2><p>{filter ? "Try a different name, type, or source ID." : "Sources added for your role will appear here after ingestion."}</p></div>}
  </div>;
}

function IngestView({ role, available, error, accessRole, setAccessRole, file, setFile, result, pending, structuredMeta, setStructuredMeta, structuredJson, setStructuredJson, onUpload, onStructured }: {
  role: string; available: boolean; error: string | null; accessRole: string; setAccessRole: (role: string) => void; file: File | null; setFile: (file: File | null) => void; result: string | null; pending: boolean;
  structuredMeta: { table: string; rowId: string; sourceName: string; accessRole: string }; setStructuredMeta: (update: Partial<{ table: string; rowId: string; sourceName: string; accessRole: string }>) => void;
  structuredJson: string; setStructuredJson: (value: string) => void; onUpload: (event: FormEvent<HTMLFormElement>) => void; onStructured: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const [fileError, setFileError] = useState<string | null>(null);
  const canIngest = available && role === "CEO";
  function chooseFile(selected: File | null) {
    const extension = selected?.name.toLowerCase().split(".").pop();
    if (selected && (!extension || !["pdf", "png", "jpg", "jpeg"].includes(extension) || selected.size === 0 || selected.size > 25 * 1024 * 1024)) {
      setFile(null); setFileError("Choose a nonempty PDF, PNG, or JPEG under 25 MB."); return;
    }
    setFileError(null); setFile(selected);
  }
  return <div className="data-page"><PageHeading title="Ingest" description="Index source files and structured records into the secured knowledge store." />
    {role === "Loading" && <div className="inline-notice" role="status"><span className="loading-dot" /><span>Checking ingestion service availability…</span></div>}
    {!available && role !== "Loading" && <div className="inline-notice" role="status"><Icon name="lock" size={17} /><span>The local ingestion service is unavailable. Confirm the local API and Supabase are running.</span></div>}
    {available && role !== "CEO" && role !== "Loading" && <div className="inline-notice" role="status"><Icon name="lock" size={17} /><span>Ingestion is restricted to the CEO demo account. Your current role remains read-only.</span></div>}
    {error && <p className="request-error" role="alert">{error}</p>}
    <div className={`ingest-progress ${error ? "ingest-failed" : result ? "ingest-indexed" : ""}`} role="status"><strong>{error ? "Failed" : result ? "Indexed" : role === "Loading" ? "Checking availability" : !available ? "Unavailable" : role !== "CEO" ? "Read-only" : pending ? "Indexing source…" : file ? "Ready to upload" : "Ready"}</strong><span>{error ? "Your selected file or record remains available to retry." : result ?? (pending ? "The API processes and indexes this source before returning; per-stage progress is not available." : "PDF, PNG, JPEG, or structured records can be indexed here.")}</span></div>
    <div className="ingest-columns"><form className="ingest-form" onSubmit={onUpload}><div className="form-title"><Icon name="upload" size={18} /><div><h2>Document or image</h2><p>PDF, PNG, or JPEG · up to 25 MB</p></div></div>
      <label className="file-drop" onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); if (canIngest && !pending) chooseFile(event.dataTransfer.files[0] ?? null); }}><input type="file" accept="application/pdf,image/png,image/jpeg,.pdf,.png,.jpg,.jpeg" disabled={!canIngest || pending} onChange={(event) => { chooseFile(event.target.files?.[0] ?? null); event.currentTarget.value = ""; }} /><Icon name="files" size={20} /><strong>{file?.name ?? "Drop a file or choose a source"}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : "PDF text and scanned pages, or image OCR · max 25 MB"}</span></label>
      {fileError && <p className="request-error" role="alert">{fileError}</p>}
      <label className="field-label">Grant source to<select value={accessRole} disabled={!canIngest || pending} onChange={(event) => setAccessRole(event.target.value)}>{DEMO_ROLES.map((value) => <option key={value}>{value}</option>)}</select></label>
      <button className="primary-action" type="submit" disabled={!canIngest || pending || !file}>{pending ? "Uploading and indexing…" : "Upload and index"}</button>
      <p className="form-footnote">Files are stored in the local private ingestion folder. Access is granted to the selected role and the CEO.</p>
    </form>
    <form className="ingest-form" onSubmit={onStructured}><div className="form-title"><Icon name="table" size={18} /><div><h2>Structured record</h2><p>Save a relational row and index its authorized representation.</p></div></div>
      <div className="field-pair"><label className="field-label">Table<select value={structuredMeta.table} disabled={!canIngest || pending} onChange={(event) => setStructuredMeta({ table: event.target.value })} required>{["invoices", "customers", "payments", "purchase_orders", "projects", "employees", "opportunities"].map((table) => <option key={table}>{table}</option>)}</select></label><label className="field-label">Row ID<input value={structuredMeta.rowId} disabled={!canIngest || pending} onChange={(event) => setStructuredMeta({ rowId: event.target.value })} required /></label></div>
      <label className="field-label">Source name<input value={structuredMeta.sourceName} disabled={!canIngest || pending} onChange={(event) => setStructuredMeta({ sourceName: event.target.value })} required /></label>
      <label className="field-label">Record fields<textarea className="json-input" value={structuredJson} disabled={!canIngest || pending} onChange={(event) => setStructuredJson(event.target.value)} spellCheck={false} aria-describedby="structured-json-help" /></label><small className="field-hint" id="structured-json-help">JSON object with scalar values: strings, numbers, booleans, or null.</small>
      <label className="field-label">Grant source to<select value={structuredMeta.accessRole} disabled={!canIngest || pending} onChange={(event) => setStructuredMeta({ accessRole: event.target.value })}>{DEMO_ROLES.map((value) => <option key={value}>{value}</option>)}</select></label>
      <button className="primary-action" type="submit" disabled={!canIngest || pending}>{pending ? "Indexing record…" : "Index structured record"}</button>
    </form></div>
  </div>;
}

function SecurityView({ data, pending, error, onRefresh }: { data: SecurityData | null; pending: boolean; error: string | null; onRefresh: () => void }) {
  if (!data) return <PageState title="Security" pending={pending} error={error} onRefresh={onRefresh} />;
  return <div className="data-page"><PageHeading title="Security" description="Authorization is enforced before information reaches the model." action={<button className="quiet-button" type="button" onClick={onRefresh}>Refresh trace</button>} />
    <ContextBand identity={data.identity.display_name} email={data.identity.email} role={data.active_role} verified />
    <section className="data-section"><SectionTitle title="Retrieval authorization boundary" /><div className="security-flow">{([{ label: "Identity", icon: "user", note: "Validated session" }, { label: "Authorization", icon: "lock", note: "Database policies" }, { label: "Secure retrieval", icon: "search", note: "Role-scoped matches" }, { label: "Authorized evidence", icon: "files", note: "Retrieved source rows" }, { label: "Generation", icon: "chat", note: "Answer generation" }] as const).map((step, index) => <div className={`security-step ${index === 1 ? "security-boundary" : ""}`} key={step.label}><Icon name={step.icon} size={19} /><strong>{step.label}</strong><span>{step.note}</span>{index < 4 && <Icon name="arrow" size={15} className="flow-arrow" />}</div>)}</div><p className="trace-disclaimer">Architectural design: retrieval uses the validated user or server-brokered demo-role session. Unauthorized evidence supplied to the model: not independently measured in this trace. The endpoint does not probe hosted RLS status.</p></section>
    <section className="data-section"><SectionTitle title="Effective access scope" /><p className="scope-copy"><Icon name="lock" size={15} />{data.effective_scope}</p><div className="security-checks">{Object.entries(data.security_tests).map(([label, value]) => <div key={label} className={label === "basis" ? "security-check-basis" : undefined} data-unverified={/not checked|not independently measured|not verified/.test(String(value)) || undefined}><span>{label.replaceAll("_", " ")}</span><strong>{String(value)}</strong></div>)}</div></section>
    <section className="data-section"><SectionTitle title="Recent retrieval decisions" /><ol className="trace-list">{data.trace.length ? data.trace.map((entry) => <li key={entry.query_id}><span className="trace-dot" /><div><strong>{entry.decision} · {entry.active_role}</strong><span>{entry.authorized_evidence_count} authorized evidence items · unauthorized evidence supplied to the model: not independently measured</span></div><time>{formatTime(entry.created_at)}</time></li>) : <li className="empty-note">Ask a question to see a real retrieval trace for this session.</li>}</ol><p className="trace-disclaimer">The trace omits source names and contents. Recent events are held in this API process and clear when it restarts.</p></section>
  </div>;
}

function EvaluationView({ data, pending, error, role, onRefresh, onRun }: { data: EvaluationData | null; pending: boolean; error: string | null; role: string; onRefresh: () => void; onRun: () => void }) {
  return <div className="data-page"><PageHeading title="Evaluation" description="Local synthetic smoke results for retrieval and authorization; not a production benchmark." action={<button className="quiet-button" type="button" onClick={onRefresh}>Refresh</button>} />
    {!data ? <div className="evaluation-empty"><Icon name="chart" size={22} />{error ? <p className="request-error" role="alert">{error}</p> : <><h2>No evaluation run recorded</h2><p>Run the real retrieval suite to measure hit rate, ranking, modality coverage, and authorization boundaries.</p></>}<button className="primary-action" type="button" disabled={pending || role !== "CEO"} onClick={onRun}>{pending ? "Running evaluation…" : "Run evaluation"}</button>{role !== "CEO" && <small>Switch to the CEO access context to inspect or run the local test suite.</small>}</div> : <>
      <div className="evaluation-scope"><p className="evaluation-run-label"><Icon name="chart" size={15} />{data.run_kind === "historical_legacy" ? "Historical saved run · legacy labels corrected; not rerun" : data.run_kind === "fresh_local" ? "Fresh local synthetic run" : "Recorded local synthetic run; not rerun on refresh"}</p><div className="evaluation-observations"><span>Checked authorization cases · {data.authorization_violations} forbidden hits</span><span>Retrieved citation locations · {String(data.measured_checks?.retrieved_citation_locations_present ?? "not measured")} / {String(data.measured_checks?.retrieved_citation_locations_checked ?? "not measured")} present</span><span>Mean latency · {formatLatency(data.measured_checks?.mean_latency_ms)}</span></div></div>
      <div className="evaluation-summary"><div><span>Dataset</span><strong>{data.dataset}</strong></div><div><span>Queries</span><strong>{data.query_count}</strong></div><div><span>Hit rate@{data.top_k}</span><strong>{formatMetric(data.retrieval_hit_rate_at_k)}</strong></div><div><span>Mean reciprocal rank</span><strong>{formatMetric(data.mean_reciprocal_rank)}</strong></div><div><span>Checked forbidden hits</span><strong className={data.authorization_violations ? "metric-bad" : "metric-good"}>{data.authorization_violations}</strong></div></div>
      <div className="source-table-wrap"><table className="source-table evaluation-table"><thead><tr><th>Evaluation case</th><th>Role</th><th>Result</th><th>Latency</th><th>Forbidden hits</th></tr></thead><tbody>{data.results.map((row, index) => <tr key={`${String(row.name)}-${index}`}><td><strong>{String(row.name)}</strong></td><td>{String(row.role ?? "—")}</td><td><span className={`status-pill ${row.hit === true ? "status-good" : "status-bad"}`}>{row.hit === true ? "Pass" : "Review"}</span></td><td>{typeof row.latency_ms === "number" ? `${row.latency_ms} ms` : "—"}</td><td>{Array.isArray(row.forbidden_source_hits) ? row.forbidden_source_hits.length : "—"}</td></tr>)}</tbody></table></div>
      <p className="trace-disclaimer">Retrieved with authenticated demo users against the local database. This small synthetic run measures retrieval and row-level authorization; hit rate means any expected source was found, not recall over all relevant sources. Citation-location presence does not verify answer provenance or entailment. It does not establish representative-scale quality or semantic answer quality.{data.completed_at ? ` Completed ${formatTime(data.completed_at)}.` : ""}</p>
      <button className="quiet-button" type="button" disabled={pending || role !== "CEO"} onClick={onRun}>{pending ? "Running…" : "Run again"}</button>
    </>}
  </div>;
}

function PageHeading({ title, description, action }: { title: string; description: string; action?: React.ReactNode }) {
  return <div className="page-heading"><div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}
function ContextBand({ identity, email, role, verified = false }: { identity: string; email?: string; role: string; verified?: boolean }) {
  return <div className="context-band"><div className="context-detail"><Icon name="user" size={19} /><div><span>Authenticated identity</span><strong>{identity}</strong>{email && <small>{email}</small>}</div></div><div className="context-detail"><Icon name="lock" size={19} /><div><span>Authorization context</span><strong>{role}</strong></div></div>{verified && <span className="session-state"><Icon name="lock" size={13} />Session verified</span>}</div>;
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
  if (typeof location.row === "string") return `${location.table ?? "Record"} / ${location.row}`;
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

function timingLabel(key: string) {
  return ({auth_session_ms: "Access check", embedding_ms: "Search preparation", retrieval_and_ranking_ms: "Retrieval & ranking", gemini_ms: "Generation", citation_validation_ms: "Citation validation", ranking_only_ms: "Ranking separately", history_persistence_ms: "History save", total_ms: "Total"} as Record<string, string>)[key] ?? key.replaceAll("_", " ");
}
function formatRecordField(key: string, value: unknown, currency: unknown) {
  if (key.endsWith("_minor_units") && typeof value === "number" && typeof currency === "string") {
    try { return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(value / 100); } catch { /* Preserve the canonical field if its currency is unknown. */ }
  }
  return String(value ?? "Not set");
}

function OriginalImage({ url, region }: { url: string; region: unknown }) {
  const [size, setSize] = useState({ width: 0, height: 0 });
  const box = region as Record<string, number> | null;
  const valid = box && size.width > 0 && size.height > 0 && [box.x_min, box.y_min, box.x_max, box.y_max].every(Number.isFinite) && box.x_min >= 0 && box.y_min >= 0 && box.x_max <= size.width && box.y_max <= size.height && box.x_max > box.x_min && box.y_max > box.y_min;
  return <div className="image-preview"><div className="image-original">
    {/* Original bytes are fetched with the current authorization headers. */}
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img src={url} alt="Original authorized source" onLoad={(event) => setSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight })} />
    {valid && <span className="ocr-highlight" aria-label="Cited OCR region" style={{ left: `${100 * box.x_min / size.width}%`, top: `${100 * box.y_min / size.height}%`, width: `${100 * (box.x_max - box.x_min) / size.width}%`, height: `${100 * (box.y_max - box.y_min) / size.height}%` }} />}
  </div><p>{valid ? "Highlighted region identifies the cited OCR text." : "OCR region overlay unavailable for this source."}</p></div>;
}
