// Thin client for the webfreeze backend. All paths are relative so the Vite
// dev proxy (and, in production, the FastAPI static mount) route them to the
// same backend.

export type Mode = "auto" | "static" | "render";

export interface SessionResponse {
  sessionId: string;
  previewUrl: string;
  title: string;
  renderMode: string;
  warnings: string[];
}

export interface WidgetReport {
  selector: string;
  type: string;
  strategy: string;
  confidence: number;
  note: string;
}

export interface FreezeReport {
  sizeKB: number;
  keptScripts: number;
  widgets: WidgetReport[];
}

export interface FreezeResponse {
  html: string;
  report: FreezeReport;
}

export interface FreezeOptions {
  inlineImages?: boolean;
  jsFidelity?: "off" | "css" | "css+js";
  stripUnselectedSiblings?: boolean;
}

async function asError(resp: Response): Promise<Error> {
  let detail = `${resp.status} ${resp.statusText}`;
  try {
    const body = await resp.json();
    if (body?.detail) detail = body.detail;
  } catch {
    /* non-JSON error body */
  }
  return new Error(detail);
}

export async function createSession(url: string, mode: Mode = "auto"): Promise<SessionResponse> {
  const resp = await fetch("/api/session", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ url, mode }),
  });
  if (!resp.ok) throw await asError(resp);
  return resp.json();
}

export async function freeze(
  sessionId: string,
  keep: "selection" | "whole",
  options: FreezeOptions = {},
  domHtml?: string,
): Promise<FreezeResponse> {
  const resp = await fetch("/api/freeze", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ sessionId, keep, domHtml, options }),
  });
  if (!resp.ok) throw await asError(resp);
  return resp.json();
}
