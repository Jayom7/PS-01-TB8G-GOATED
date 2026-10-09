export function chatErrorMessage(payload: { code?: string; status?: number } = {}, status?: number): string {
  const code = payload.code ?? "";
  if (code === "session_expired" || status === 401 || payload.status === 401) return "Your session expired. Sign in again to continue.";
  if (code === "authorization_denied" || status === 403 || payload.status === 403) return "Your current access does not permit this action.";
  if (status === 404 || payload.status === 404) return "This conversation or source is no longer available to your account.";
  if (code === "provider_timeout") return "The answer took too long to complete. Your access permissions remain in place. Please try again shortly.";
  if (code === "provider_safety_block") return "I couldn’t answer that request. Please try rephrasing your question.";
  if (["provider_authentication_failed", "provider_invalid_model"].includes(code)) return "The answer service needs attention. Please contact your workspace administrator.";
  if (code === "retrieval_unavailable") return "Authorized search could not complete. Please try again shortly.";
  if (code === "evidence_changed") return "Source access or content changed. Please ask again to use current evidence.";
  return "I couldn’t complete that answer just now. Your access permissions remain in place. Please try again shortly.";
}

export function appendTurn<T extends { response: { request_id: string } }>(turns: T[], turn: T): T[] {
  return turns.some((saved) => saved.response.request_id === turn.response.request_id) ? turns : [...turns, turn];
}
