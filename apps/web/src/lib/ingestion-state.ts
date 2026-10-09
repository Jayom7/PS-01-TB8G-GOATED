export type IngestionStatus = { pending: boolean; error: string | null; result: string | null };
export type IngestionState = { file: IngestionStatus; structured: IngestionStatus };
export const initialIngestion: IngestionState = {
  file: { pending: false, error: null, result: null },
  structured: { pending: false, error: null, result: null },
};
export function ingestionReducer(state: IngestionState, action: {
  operation: keyof IngestionState; status: "start" | "success" | "failure"; message?: string;
}): IngestionState {
  return { ...state, [action.operation]: {
    pending: action.status === "start",
    error: action.status === "failure" ? action.message ?? "Please retry." : null,
    result: action.status === "success" ? action.message ?? "Indexed" : null,
  } };
}

export function ingestionErrorMessage(payload: { code?: string; stage?: string }, status: number): string | null {
  if (status === 401 || status === 403) return null; // Keep the shared session/access handling.
  if (payload.stage === "embedding" || payload.code?.startsWith("provider_")) {
    return "Indexing is temporarily unavailable. Your input is still selected; please retry shortly or contact your workspace administrator.";
  }
  if (payload.code === "ingestion_unavailable") return "The source could not be confirmed in your workspace. Your input is still here; please retry.";
  return null;
}
