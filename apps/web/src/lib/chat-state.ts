export function chatErrorMessage(payload: { code?: string; status?: number } = {}, status?: number): string {
  const code = payload.code ?? "";
  if (code === "session_expired" || status === 401 || payload.status === 401) return "Your session expired. Sign in again to continue.";
  if (code === "authorization_denied" || status === 403 || payload.status === 403) return "Your current access does not permit this action.";
  if (status === 404 || payload.status === 404) return "This conversation or source is no longer available to your account.";
  if (code === "provider_timeout") return "The answer took too long to complete. Your access permissions remain in place. Please try again shortly.";
  if (code === "provider_invalid_response") return "The response could not be validated. No answer was released. Please retry your question.";
  if (code === "provider_rate_limited" || code === "provider_unavailable") return "The answer service is temporarily unavailable. Your question is still here; try again when the service is ready.";
  if (code === "provider_safety_block") return "I couldn’t answer that request. Please try rephrasing your question.";
  if (["provider_authentication_failed", "provider_invalid_model", "provider_invalid_request"].includes(code)) return "The answer service needs attention. Please contact your workspace administrator.";
  if (code === "retrieval_unavailable") return "Authorized search could not complete. Please try again shortly.";
  if (code === "evidence_changed") return "Source access or content changed. Please ask again to use current evidence.";
  return "I couldn’t complete that answer just now. Your access permissions remain in place. Please try again shortly.";
}

export function chatFailureTitle(payload: {code?: string; status?: number} = {}) {
  if (payload.status === 403 || payload.code === "authorization_denied") return "Access denied";
  if (payload.status === 401 || payload.code === "session_expired") return "Sign in to continue";
  if (payload.code === "provider_invalid_response") return "Response validation failed";
  if (payload.code === "retrieval_unavailable") return "Authorized search unavailable";
  if (payload.code === "evidence_changed") return "Evidence changed";
  if (payload.code === "provider_safety_block") return "Rephrase this request";
  return payload.code?.startsWith("provider_") ? "Generation unavailable" : "Answer unavailable";
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
    const key = citation.document_id || citation.citation_id;
    const group = groups.get(key) ?? { key, title: citation.title ?? "Authorized source", citations: [] };
    if (!group.citations.some((saved) => citationKey(saved) === citationKey(citation) && JSON.stringify(saved.location) === JSON.stringify(citation.location))) group.citations.push(citation);
    groups.set(key, group);
  }
  return [...groups.values()];
}
