"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Icon, type IconName } from "@/components/icons";
import {
  previewAnswer,
  previewRoles,
  previewSources,
  type PreviewRole,
  sampleQuestion,
  type WorkspaceView,
} from "@/lib/preview-data";

const navigation: { label: WorkspaceView; icon: IconName }[] = [
  { label: "Chat", icon: "chat" },
  { label: "Sources", icon: "files" },
  { label: "Ingestion", icon: "upload" },
  { label: "Evaluation", icon: "chart" },
];

export default function Workspace() {
  const [role, setRole] = useState<PreviewRole>("Finance Manager");
  const [view, setView] = useState<WorkspaceView>("Chat");
  const [query, setQuery] = useState(sampleQuestion);
  const [submitted, setSubmitted] = useState(false);
  const [activeSource, setActiveSource] = useState<string | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const isPreviewQuestion = query.trim().toLowerCase() === sampleQuestion.toLowerCase();
  const hasPreviewEvidence = role === "Finance Manager" && submitted && isPreviewQuestion;

  useEffect(() => {
    const closePanels = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setEvidenceOpen(false);
        setNavigationOpen(false);
      }
    };
    window.addEventListener("keydown", closePanels);
    return () => window.removeEventListener("keydown", closePanels);
  }, []);

  function submitQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) return;
    setSubmitted(true);
    setActiveSource(isPreviewQuestion && role === "Finance Manager" ? "invoice-2048" : null);
    setEvidenceOpen(false);
  }

  function selectRole(nextRole: PreviewRole) {
    setRole(nextRole);
    setSubmitted(false);
    setActiveSource(null);
  }

  function cite(sourceId: string) {
    setActiveSource(sourceId);
    setEvidenceOpen(true);
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
          <span className="brand-name">PS-01</span>
        </div>
        <div className="topbar-context" aria-label="Atmiya University Code Carnival judges">
          <span>Atmiya University</span>
          <span className="context-separator" aria-hidden="true">·</span>
          <span>Code Carnival</span>
          <span className="context-separator" aria-hidden="true">·</span>
          <span>Judges</span>
        </div>
        <div className="topbar-state"><span className="preview-dot" />Preview mode</div>
      </header>

      <div className="workspace-grid">
        <aside className={`navigation-rail ${navigationOpen ? "navigation-open" : ""}`}>
          <div className="rail-workspace-label">Workspace</div>
          <label className="role-picker">
            <span className="sr-only">Preview identity</span>
            <Icon name="user" size={18} />
            <select value={role} onChange={(event) => selectRole(event.target.value as PreviewRole)}>
              {previewRoles.map((item) => <option key={item}>{item}</option>)}
            </select>
            <Icon name="chevron" size={16} />
          </label>
          <p className="rail-preview-note">Synthetic identity preview</p>

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
                  setEvidenceOpen(false);
                }}
              >
                <Icon name={icon} size={19} />
                <span>{label}</span>
              </button>
            ))}
          </nav>

          <div className="rail-footer">
            <div className="preview-caption">Local interface preview</div>
            <p>Authentication and retrieval are not connected.</p>
          </div>
        </aside>

        <section className="main-column" aria-label={`${view} workspace`}>
          {view === "Chat" ? (
            <>
              <div className="conversation-header">
                <div>
                  <h1>Ask your knowledge base</h1>
                  <p>Search documents and records from one workspace.</p>
                </div>
                <button
                  className="evidence-toggle"
                  type="button"
                  onClick={() => setEvidenceOpen(true)}
                  disabled={!hasPreviewEvidence}
                  aria-label="Open evidence panel"
                >
                  <Icon name="files" size={18} />
                  <span>Evidence{hasPreviewEvidence ? " (2)" : ""}</span>
                </button>
              </div>

              <div className="conversation-scroll">
                {submitted ? (
                  <div className="message-thread" aria-live="polite">
                    <div className="question-bubble">
                      <span className="message-avatar user-avatar" aria-hidden="true">{role.slice(0, 1)}</span>
                      <p>{query}</p>
                    </div>

                    {hasPreviewEvidence ? (
                      <div className="answer-block">
                        <div className="answer-avatar" aria-hidden="true">PS</div>
                        <div className="answer-copy">
                          {previewAnswer.map((claim) => (
                            <p key={claim.text}>
                              {claim.text}{" "}
                              {claim.citations.map((sourceId) => {
                                const source = previewSources.find((item) => item.id === sourceId);
                                return source ? (
                                  <button
                                    className="inline-citation"
                                    key={sourceId}
                                    type="button"
                                    aria-label={`Open citation ${source.number}: ${source.title}`}
                                    onClick={() => cite(sourceId)}
                                  >
                                    [{source.number}]
                                  </button>
                                ) : null;
                              })}
                            </p>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="preview-response" role="status">
                        <div className="answer-avatar" aria-hidden="true">PS</div>
                        <div>
                          <p className="response-primary">
                            {role === "Finance Manager"
                              ? "This preview only contains one sample question."
                              : "This preview has no evidence for that question."}
                          </p>
                          <p className="response-secondary">
                            {role === "Finance Manager"
                              ? "Try the sample question shown in the conversation preview."
                              : "Connect authenticated sessions and retrieval before using role-specific queries."}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="empty-conversation">
                    <div className="empty-mark" aria-hidden="true"><Icon name="chat" size={22} /></div>
                    <p>Ask about a document, image, or business record.</p>
                    <button className="sample-question" type="button" onClick={() => setQuery(sampleQuestion)}>
                      <span>{sampleQuestion}</span>
                      <Icon name="arrow" size={17} />
                    </button>
                  </div>
                )}
              </div>

              <div className="composer-wrap">
                <form className="composer" onSubmit={submitQuery}>
                  <label className="sr-only" htmlFor="query-input">Ask a question</label>
                  <textarea
                    id="query-input"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Ask a question about your documents..."
                    rows={2}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        event.currentTarget.form?.requestSubmit();
                      }
                    }}
                  />
                  <div className="composer-actions">
                    <span className="composer-note">Synthetic preview · not sent to an API</span>
                    <button className="send-button" type="submit" disabled={!query.trim()}>
                      <Icon name="send" size={17} />
                      <span>Preview answer</span>
                    </button>
                  </div>
                </form>
              </div>
            </>
          ) : (
            <WorkspacePlaceholder view={view} />
          )}
        </section>

        <aside className={`evidence-panel ${evidenceOpen ? "evidence-panel-open" : ""}`} aria-label="Evidence preview">
          <div className="evidence-heading">
            <div>
              <h2>Evidence</h2>
              <p>{hasPreviewEvidence ? "Synthetic source preview" : "Sources will appear here"}</p>
            </div>
            <button
              className="icon-button close-evidence"
              type="button"
              aria-label="Close evidence panel"
              onClick={() => setEvidenceOpen(false)}
            >
              <Icon name="close" size={20} />
            </button>
          </div>

          {hasPreviewEvidence ? (
            <div className="source-list">
              {previewSources.map((source) => (
                <article
                  className={`source-entry ${activeSource === source.id ? "source-entry-active" : ""}`}
                  key={source.id}
                >
                  <button
                    className="source-entry-heading"
                    type="button"
                    aria-expanded={activeSource === source.id}
                    onClick={() => setActiveSource((current) => current === source.id ? null : source.id)}
                  >
                    <Icon name={source.type === "PDF page" ? "files" : "table"} size={19} />
                    <span className="source-title-group">
                      <span className="source-title">{source.title}</span>
                      <span className="source-location">{source.location}</span>
                    </span>
                    <Icon name="chevron" size={17} />
                  </button>
                  {activeSource === source.id && (
                    <div className="source-detail">
                      <div className="source-meta-row"><span>Source type</span><span>{source.type}</span></div>
                      <div className="source-meta-row"><span>Reference</span><span>{source.location}</span></div>
                      <p className="source-excerpt">{source.detail}</p>
                      <p className="source-preview-label">Synthetic preview content</p>
                    </div>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <div className="evidence-empty">
              <div className="evidence-empty-icon"><Icon name="lock" size={20} /></div>
              <p>No evidence is loaded into this preview.</p>
              <span>Live source access will appear after the authenticated retrieval API is connected.</span>
            </div>
          )}

          <div className="trace-note">
            <div className="trace-note-icon"><Icon name="lock" size={17} /></div>
            <p>This interface preview does not perform authentication, authorization, retrieval, or model calls.</p>
          </div>
        </aside>
      </div>

      {navigationOpen && <button type="button" className="mobile-scrim nav-scrim" aria-label="Close navigation" onClick={() => setNavigationOpen(false)} />}
      {evidenceOpen && <button type="button" className="mobile-scrim evidence-scrim" aria-label="Close evidence" onClick={() => setEvidenceOpen(false)} />}
    </main>
  );
}

function WorkspacePlaceholder({ view }: { view: WorkspaceView }) {
  const content = {
    Sources: {
      title: "Sources",
      body: "Connect an authenticated source catalog to browse documents and records.",
      action: "No sources connected",
    },
    Ingestion: {
      title: "Ingestion",
      body: "PDF, image OCR, and structured record ingestion will be available after the API is connected.",
      action: "No ingestion jobs",
    },
    Evaluation: {
      title: "Evaluation",
      body: "Measured retrieval and citation results will appear after an evaluation run.",
      action: "No evaluation runs",
    },
    Chat: {
      title: "Ask your knowledge base",
      body: "Search documents and records from one workspace.",
      action: "",
    },
  }[view];

  return (
    <div className="placeholder-view">
      <div className="placeholder-content">
        <h1>{content.title}</h1>
        <p>{content.body}</p>
        <div className="placeholder-state"><span className="placeholder-state-dot" />{content.action}</div>
      </div>
    </div>
  );
}
