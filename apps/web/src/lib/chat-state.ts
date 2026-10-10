export function chatErrorMessage(payload: { code?: string; status?: number } = {}, status?: number): string {
  const code = payload.code ?? "";
  if (code === "session_expired" || status === 401 || payload.status === 401) return "Your session expired. Sign in again to continue.";
  if (code === "authorization_denied" || status === 403 || payload.status === 403) return "Your current access does not permit this action.";
  if (status === 404 || payload.status === 404) return "This conversation or source is no longer available to your account.";
  if (code === "provider_timeout") return "The answer took too long. Your question is still here; please try again shortly.";
  if (code === "provider_invalid_response") return "The response could not be validated. No answer was released. Please retry your question.";
  if (code === "provider_rate_limited" || code === "provider_unavailable") return "The answer service is temporarily unavailable. Your question is still here; try again when the service is ready.";
  if (code === "provider_safety_block") return "I couldn’t answer that request. Please try rephrasing your question.";
  if (["provider_authentication_failed", "provider_invalid_model", "provider_invalid_request"].includes(code)) return "The answer service needs attention. Please contact your workspace administrator.";
  if (code === "retrieval_unavailable") return "Authorized search could not complete. Please try again shortly.";
  if (code === "evidence_changed") return "Source access or content changed. Please ask again to use current evidence.";
  if (code === "request_cancelled") return "The answer was stopped. Your question is still here if you want to try again.";
  return "I couldn’t complete that answer just now. Your access permissions remain in place. Please try again shortly.";
}

export const progressLabels: Record<string, string> = {
  loading_history: "Rechecking saved sources", connecting: "Preparing your question",
  checking_access: "Checking access", access_checked: "Access checked",
  searching_knowledge: "Searching your accessible sources", retrieval_complete: "Search complete",
  checking_references: "Checking source references", evidence_selected: "Evidence selected",
  generating_response: "Preparing an answer from the evidence",
  checking_final_access: "Rechecking source access", composing_verified_evidence: "Preparing a verified source answer",
  validating_citations: "Checking the answer and citations", validation_complete: "Saving the checked answer",
};

export function insufficientMessage(query: string): string {
  if (/\brevenue\b/i.test(query)) return "I couldn’t find a revenue figure in your accessible sources. Specify the reporting period or document you want checked. An invoice or order total alone does not establish revenue.";
  if (/\binvoice\b/i.test(query)) return "I couldn’t find that invoice detail in your accessible sources. Check the exact invoice ID and specify the amount, date or payment status you need.";
  return "I couldn’t find enough information in your accessible sources to answer that. Try a specific document, record ID or detail.";
}

export function parseSseFrames(buffer: string) {
  const events: {kind: string; payload: Record<string, unknown>}[] = [];
  const boundary = /\r?\n\r?\n/g;
  let consumed = 0;
  for (let match = boundary.exec(buffer); match; match = boundary.exec(buffer)) {
    const frame = buffer.slice(consumed, match.index);
    consumed = match.index + match[0].length;
    const lines = frame.split(/\r?\n/);
    const kind = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
    if (!kind || !["progress", "error", "result"].includes(kind)) continue;
    const data = lines.filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trimStart()).join("\n");
    if (!data) continue;
    const payload = JSON.parse(data);
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) throw new Error("Invalid answer stream.");
    events.push({kind, payload});
  }
  return {events, remainder: buffer.slice(consumed)};
}

// A stalled session refresh must not make Stop wait for authentication. The
// underlying auth refresh can finish, but this request cannot resume afterward.
export function waitForRequest<T>(operation: Promise<T>, signal: AbortSignal): Promise<T> {
  return new Promise((resolve, reject) => {
    const abort = () => reject(signal.reason);
    if (signal.aborted) { void operation.catch(() => {}); reject(signal.reason); return; }
    signal.addEventListener("abort", abort, {once: true});
    operation.then((value) => {
      signal.removeEventListener("abort", abort); resolve(value);
    }, (cause) => {
      signal.removeEventListener("abort", abort); reject(cause);
    });
  });
}

export function chatFailureTitle(payload: {code?: string; status?: number} = {}) {
  if (payload.status === 403 || payload.code === "authorization_denied") return "Access denied";
  if (payload.status === 401 || payload.code === "session_expired") return "Sign in to continue";
  if (payload.code === "provider_invalid_response") return "Response validation failed";
  if (payload.code === "retrieval_unavailable") return "Authorized search unavailable";
  if (payload.code === "evidence_changed") return "Evidence changed";
  if (payload.code === "provider_safety_block") return "Rephrase this request";
  return payload.code?.startsWith("provider_") ? "Couldn’t finish the answer" : "Answer unavailable";
}

export function answerLabel(response: {state: string; claims?: {composition?: string}[]; trace: {response_mode?: string; generation_model?: string | null; history_replay?: boolean}}) {
  if (response.state === "VERIFIED_EVIDENCE") return "Verified source answer";
  if (response.trace.history_replay) return "Source-backed answer";
  if (response.trace.generation_model && response.trace.response_mode === "model_generated" && response.state === "CITATION_VALIDATED" && response.claims?.length && response.claims.every((claim) => claim.composition === "model")) return "AI-generated explanation";
  return "Source-backed answer";
}

export function citationKey(citation: {citation_id: string; evidence_id?: string | null}) {
  return citation.evidence_id || citation.citation_id;
}

export function appendTurn<T extends { response: { request_id: string } }>(turns: T[], turn: T): T[] {
  return turns.some((saved) => saved.response.request_id === turn.response.request_id) ? turns : [...turns, turn];
}

export function groupCitations<T extends { citation_id: string; evidence_id?: string | null; document_id?: string | null; title: string | null; location: Record<string, unknown> }>(citations: T[]) {
  const groups = new Map<string, { key: string; title: string; citations: T[] }>();
  for (const citation of citations) {
    // Never merge unrelated sources merely because their titles happen to match.
    const source = citation.document_id || citation.citation_id;
    const key = citation.location.table && citation.location.row ? `${source}:${citation.location.table}:${citation.location.row}` : source;
    const group = groups.get(key) ?? { key, title: citation.title ?? "Authorized source", citations: [] };
    if (!group.citations.some((saved) => citationKey(saved) === citationKey(citation) && JSON.stringify(saved.location) === JSON.stringify(citation.location))) group.citations.push(citation);
    groups.set(key, group);
  }
  return [...groups.values()];
}
