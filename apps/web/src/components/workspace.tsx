"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Icon, type IconName } from "@/components/icons";
import { createClient } from "@/lib/supabase/client";

type View = "Overview" | "Ask" | "Knowledge" | "Ingestion" | "Security" | "Evaluation";
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

const navigation: { label: View; icon: IconName }[] = [
  { label: "Overview", icon: "home" },
  { label: "Ask", icon: "chat" },
  { label: "Knowledge", icon: "files" },
  { label: "Ingestion", icon: "upload" },
  { label: "Security", icon: "lock" },
  { label: "Evaluation", icon: "chart" },
];

const exampleQuestions = [
  "What amount is shown on Acme's scanned invoice?",
  "What payment terms are in Acme's contract?",
  "Is Acme's invoice overdue?",
  "Is Acme overdue and what payment terms does its contract specify?",
];

export default function Workspace({ identity }: { identity: string }) {
  const router = useRouter();
  const [view, setView] = useState<View>("Ask");
  const [query, setQuery] = useState("");
  const [askedQuery, setAskedQuery] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [activeSource, setActiveSource] = useState<SourcePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [navigationOpen, setNavigationOpen] = useState(false);

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
      const supabase = createClient();
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) {
        router.replace("/login");
        return;
      }
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/v1/chat/query`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ query: question }),
        },
      );
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        if (response.status === 401) {
          router.replace("/login");
          return;
        }
        throw new Error(typeof payload?.detail === "string" ? payload.detail : "The knowledge service is unavailable.");
      }
      setResult(payload as QueryResult);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The knowledge service is unavailable.");
    } finally {
      setPending(false);
    }
  }

  async function openSource(citation: Citation) {
    setActiveSource({
      citation_id: citation.citation_id,
      source_type: citation.source_type,
      title: citation.title,
      source_id: null,
      location: citation.location,
      excerpt: "Loading the exact source excerpt…",
    });
    try {
      const { data } = await createClient().auth.getSession();
      const token = data.session?.access_token;
      if (!token) {
        router.replace("/login");
        return;
      }
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/v1/sources/${encodeURIComponent(citation.citation_id)}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error("This source is unavailable.");
      setActiveSource(payload as SourcePreview);
    } catch {
      setActiveSource({
        citation_id: citation.citation_id,
        source_type: citation.source_type,
        title: citation.title,
        source_id: null,
        location: citation.location,
        excerpt: "Could not load this source. Check the connection and your access, then try again.",
      });
    }
  }

  async function signOut() {
    await createClient().auth.signOut();
    router.replace("/login");
    router.refresh();
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <button
            className="icon-button mobile-menu-button"
            type="button"
            aria-label={navigationOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={navigationOpen}
            onClick={() => setNavigationOpen((open) => !open)}
          >
            <Icon name={navigationOpen ? "close" : "menu"} size={21} />
          </button>
          <span className="brand-name">Clearframe</span>
        </div>
        <div className="topbar-context">Secure knowledge workspace</div>
        <div className="topbar-state">
          <span className="user-indicator" aria-hidden="true">{identity.slice(0, 1).toUpperCase()}</span>
          <span className="identity-label" title={identity}>{identity}</span>
          <button className="signout-button" type="button" onClick={signOut}>Sign out</button>
        </div>
      </header>

      <div className="workspace-grid">
        <aside className={`navigation-rail ${navigationOpen ? "navigation-open" : ""}`}>
          <div className="rail-workspace-label">Workspace</div>
          <nav className="primary-navigation" aria-label="Workspace">
            {navigation.map(({ label, icon }) => (
              <button
                className={`navigation-item ${view === label ? "navigation-item-active" : ""}`}
                type="button"
                key={label}
                aria-current={view === label ? "page" : undefined}
                onClick={() => {
                  setView(label);
                  setNavigationOpen(false);
                }}
              >
                <Icon name={icon} size={19} />
                <span>{label}</span>
              </button>
            ))}
          </nav>
          <div className="rail-footer">
            <div className="preview-caption">Signed in</div>
            <p>Your requests use your authenticated session.</p>
          </div>
        </aside>

        <section className="main-column" aria-label={`${view} workspace`}>
          {view === "Ask" ? (
            <>
              <div className="conversation-header">
                <div>
                  <h1>Ask your knowledge base</h1>
                  <p>Answers cite evidence returned for your session. Check each source.</p>
                </div>
              </div>
              <div className="conversation-scroll">
                {result ? (
                  <div className="message-thread" aria-live="polite">
                    <div className="question-bubble">
                      <span className="message-avatar user-avatar" aria-hidden="true">{identity.slice(0, 1).toUpperCase()}</span>
                      <p>{askedQuery}</p>
                    </div>
                    {result.state === "INSUFFICIENT_EVIDENCE" ? (
                      <div className="preview-response" role="status">
                        <div className="answer-avatar" aria-hidden="true">C</div>
                        <div>
                          <p className="response-primary">I couldn’t find enough authorized evidence to answer.</p>
                          <p className="response-secondary">Try a more specific question or ask your workspace administrator about available sources.</p>
                        </div>
                      </div>
                    ) : (
                      <div className="answer-block">
                        <div className="answer-avatar" aria-hidden="true">C</div>
                        <div className="answer-copy">
                          {result.claims.map((claim, index) => (
                            <p key={`${result.request_id}-${index}`}>
                              {claim.text}{" "}
                              {claim.citations.map((citation) => (
                                <button
                                  className="inline-citation"
                                  key={citation.citation_id}
                                  type="button"
                                  aria-label={`Open source: ${citation.title ?? "Evidence"}`}
                                  onClick={() => void openSource(citation)}
                                >
                                  [{citationNumber(result.claims, citation.citation_id)}]
                                </button>
                              ))}
                            </p>
                          ))}
                          {result.state === "PARTIALLY_CITATION_VALIDATED" && (
                            <p className="response-secondary">Some claims lacked a valid source citation and were omitted.</p>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="empty-conversation">
                    <div className="empty-mark" aria-hidden="true"><Icon name="chat" size={22} /></div>
                    <p>Ask about a document, image, or business record.</p>
                    <div className="question-examples" aria-label="Example questions">
                      {exampleQuestions.map((question) => (
                        <button className="sample-question" type="button" key={question} onClick={() => setQuery(question)}>
                          <span>{question}</span>
                          <Icon name="arrow" size={17} />
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {pending && <p className="request-status" role="status">Searching authorized sources…</p>}
                {error && <p className="request-error" role="alert">{error}</p>}
              </div>
              <div className="composer-wrap">
                <form className="composer" onSubmit={ask}>
                  <label className="sr-only" htmlFor="query-input">Ask a question</label>
                  <textarea
                    id="query-input"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Ask a question about your knowledge..."
                    maxLength={2000}
                    rows={2}
                    disabled={pending}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        event.currentTarget.form?.requestSubmit();
                      }
                    }}
                  />
                  <div className="composer-actions">
                    <span className="composer-note">Your account session is sent to the knowledge API.</span>
                    <button className="send-button" type="submit" disabled={!query.trim() || pending}>
                      <Icon name="send" size={17} />
                      <span>{pending ? "Searching" : "Ask"}</span>
                    </button>
                  </div>
                </form>
              </div>
            </>
          ) : (
            <WorkspaceSection view={view} />
          )}
        </section>

        <aside className={`evidence-panel ${activeSource ? "evidence-panel-open" : ""}`} aria-label="Evidence details">
          <div className="evidence-heading">
            <div>
              <h2>Evidence</h2>
              <p>{activeSource ? "Exact source reference" : "Select a citation to inspect its source."}</p>
            </div>
            {activeSource && (
              <button className="icon-button close-evidence" type="button" aria-label="Close evidence" onClick={() => setActiveSource(null)}>
                <Icon name="close" size={20} />
              </button>
            )}
          </div>
          {activeSource ? (
            <article className="source-entry source-entry-active">
              <div className="source-entry-heading source-entry-static">
                <Icon name="files" size={19} />
                <span className="source-title-group">
                  <span className="source-title">{activeSource.title ?? "Source"}</span>
                  <span className="source-location">{formatLocation(activeSource.location)}</span>
                </span>
              </div>
              <div className="source-detail">
                <div className="source-meta-row"><span>Type</span><span>{activeSource.source_type}</span></div>
                {activeSource.source_id && <div className="source-meta-row"><span>Reference</span><span>{activeSource.source_id}</span></div>}
                <p className="source-excerpt">{activeSource.excerpt}</p>
              </div>
            </article>
          ) : (
            <div className="evidence-empty">
              <div className="evidence-empty-icon"><Icon name="lock" size={20} /></div>
              <p>Source details appear when you open a citation.</p>
              <span>The API applies the current user session to source lookup.</span>
            </div>
          )}
          <div className="trace-note">
            <div className="trace-note-icon"><Icon name="lock" size={17} /></div>
            <p>{result?.trace.session_verified
              ? `Session verified · ${result.trace.evidence_items_sent_to_model} evidence items sent to the model.`
              : "Retrieval and source lookup use the signed-in session."}</p>
          </div>
        </aside>
      </div>

      {navigationOpen && <button type="button" className="mobile-scrim nav-scrim" aria-label="Close navigation" onClick={() => setNavigationOpen(false)} />}
      {activeSource && <button type="button" className="mobile-scrim evidence-scrim" aria-label="Close evidence" onClick={() => setActiveSource(null)} />}
    </main>
  );
}

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

function WorkspaceSection({ view }: { view: Exclude<View, "Ask"> }) {
  const details: Record<Exclude<View, "Ask">, { title: string; body: string; status: string }> = {
    Overview: {
      title: "Overview",
      body: "Your workspace activity and indexed sources will appear here when the database connection is available.",
      status: "Workspace data unavailable",
    },
    Knowledge: {
      title: "Knowledge",
      body: "Browse authorized documents and business records after the database migration is applied.",
      status: "Knowledge index not connected",
    },
    Ingestion: {
      title: "Ingestion",
      body: "PDF, image OCR, and structured record ingestion will appear here once the ingestion service is connected.",
      status: "No ingestion service connected",
    },
    Security: {
      title: "Security",
      body: "Identity comes from your signed-in Supabase session. Database policy behavior has not yet been verified against the project.",
      status: "Policy verification pending",
    },
    Evaluation: {
      title: "Evaluation",
      body: "Retrieval, citation, and authorization results will appear here only after real evaluation runs.",
      status: "No evaluation runs recorded",
    },
  };
  const content = details[view];
  return (
    <div className="placeholder-view">
      <div className="placeholder-content">
        <h1>{content.title}</h1>
        <p>{content.body}</p>
        <div className="placeholder-state"><span className="placeholder-state-dot" />{content.status}</div>
      </div>
    </div>
  );
}
