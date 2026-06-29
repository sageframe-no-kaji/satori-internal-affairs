/**
 * Game store — reactive state for the entire game session.
 *
 * Uses Svelte 5 runes. Exported as a class-shaped object so components
 * can import and use it directly:
 *
 *   import { game } from '$lib/stores/gameStore.svelte';
 *   game.startSession('cases/example-neurocysticercosis.json');
 *
 * Design note (DIP / F-008): every update replaces the full state from
 * the API response. The store never computes state deltas or maintains
 * hidden context — it mirrors what the server last said.
 */

import { createSession, executeAction, ApiError } from '$lib/api';
import type {
  AppView,
  EventLogEntry,
  GameState,
  PatientCondition,
  PatientContext,
} from '$lib/types';

// ---------------------------------------------------------------------------
// Phase 1: hardcoded case path — one case, one flow
// ---------------------------------------------------------------------------

export const DEFAULT_CASE_PATH = 'cases/example-neurocysticercosis.json';

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

function createGameStore() {
  // Core session state
  let sessionId = $state<string | null>(null);
  let gameState = $state<GameState | null>(null);
  let patient = $state<PatientContext | null>(null);
  let patientCondition = $state<PatientCondition>('stable');
  let availableActions = $state<string[]>([]);

  // Event log: one entry per executed action, newest first
  let eventLog = $state<EventLogEntry[]>([]);

  // Outcome narrative: the per-tier authored text from the case, set on case end.
  let outcomeNarrative = $state<string | null>(null);

  // UI state
  let view = $state<AppView>('start');
  let isLoading = $state(false);
  let error = $state<string | null>(null);

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  async function startSession(casePath: string = DEFAULT_CASE_PATH): Promise<void> {
    isLoading = true;
    error = null;
    try {
      const resp = await createSession(casePath);
      sessionId = resp.session_id;
      gameState = resp.state;
      patient = resp.patient;
      patientCondition = resp.patient_condition;
      availableActions = resp.playable_actions;
      eventLog = [];
      view = 'play';
    } catch (e) {
      error = e instanceof ApiError ? e.message : String(e);
    } finally {
      isLoading = false;
    }
  }

  async function performAction(action: string): Promise<void> {
    if (!sessionId) return;
    isLoading = true;
    error = null;
    try {
      const resp = await executeAction(sessionId, action);

      // Update reactive state from the self-contained response
      gameState = resp.state;
      patientCondition = resp.patient_condition;
      availableActions = resp.playable_actions;

      // Prepend to event log (newest first)
      eventLog = [
        {
          action,
          timestamp_minutes: resp.state.current_time_minutes,
          events: resp.events,
          narrations: resp.narrations,
        },
        ...eventLog,
      ];

      if (resp.case_ended) {
        outcomeNarrative = resp.outcome_narrative;
        view = 'outcome';
      }
    } catch (e) {
      error = e instanceof ApiError ? e.message : String(e);
    } finally {
      isLoading = false;
    }
  }

  function reset(): void {
    sessionId = null;
    gameState = null;
    patient = null;
    patientCondition = 'stable';
    availableActions = [];
    outcomeNarrative = null;
    eventLog = [];
    view = 'start';
    isLoading = false;
    error = null;
  }

  // ---------------------------------------------------------------------------
  // Expose reactive getters + actions
  // ---------------------------------------------------------------------------

  return {
    get sessionId() { return sessionId; },
    get gameState() { return gameState; },
    get patient() { return patient; },
    get patientCondition() { return patientCondition; },
    get availableActions() { return availableActions; },
    get outcomeNarrative() { return outcomeNarrative; },
    get eventLog() { return eventLog; },
    get view() { return view; },
    get isLoading() { return isLoading; },
    get error() { return error; },

    startSession,
    performAction,
    reset,
  };
}

export const game = createGameStore();
