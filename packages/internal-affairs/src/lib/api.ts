/**
 * Typed API client for the satori-api FastAPI bridge.
 *
 * All communication with the Python backend flows through this module.
 * The frontend never imports from satori directly — it depends only on
 * these request/response shapes (DIP principle, F-008).
 *
 * In development, Vite proxies /api → http://localhost:8000 so no CORS
 * configuration is needed in the browser. See vite.config.ts.
 */

import type {
  ActionResponse,
  NodeContentResponse,
  SessionResponse,
} from './types';

const API_BASE = '/api';

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

async function request<T>(
  method: 'GET' | 'POST' | 'DELETE',
  path: string,
  body?: unknown
): Promise<T> {
  const options: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) {
    options.body = JSON.stringify(body);
  }

  const resp = await fetch(`${API_BASE}${path}`, options);

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const err = await resp.json();
      detail = err.detail ?? err.error ?? detail;
    } catch {
      // non-JSON error body
    }
    throw new ApiError(resp.status, detail);
  }

  // 204 No Content
  if (resp.status === 204) {
    return undefined as T;
  }

  return resp.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Create a new game session for the given case file path.
 * The path is resolved relative to the repository root by the server.
 */
export async function createSession(casePath: string): Promise<SessionResponse> {
  return request<SessionResponse>('POST', '/sessions', { case_path: casePath });
}

/**
 * Get the current state of an existing session without advancing the simulation.
 */
export async function getSession(sessionId: string): Promise<SessionResponse> {
  return request<SessionResponse>('GET', `/sessions/${sessionId}`);
}

/**
 * Execute a player action and get the resulting events, narrations, and
 * updated state. This is the main game-loop call.
 */
export async function executeAction(
  sessionId: string,
  action: string
): Promise<ActionResponse> {
  return request<ActionResponse>('POST', `/sessions/${sessionId}/actions`, { action });
}

/**
 * Get the narrative text for a revealed node.
 */
export async function getNodeContent(
  sessionId: string,
  nodeId: string
): Promise<NodeContentResponse> {
  return request<NodeContentResponse>('GET', `/sessions/${sessionId}/nodes/${nodeId}`);
}

/**
 * Delete a session from the server. Idempotent.
 */
export async function deleteSession(sessionId: string): Promise<void> {
  return request<void>('DELETE', `/sessions/${sessionId}`);
}
