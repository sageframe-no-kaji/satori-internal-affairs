/**
 * TypeScript types mirroring the satori-api response models.
 *
 * These are the shapes the frontend depends on. Keep them in sync with
 * packages/satori-api/src/satori_api/models.py.
 *
 * Design note (F-008 / DIP): every response from the API is self-contained.
 * The frontend renders what it receives and never relies on prior state.
 */

// ---------------------------------------------------------------------------
// Vitals
// ---------------------------------------------------------------------------

export interface VitalSigns {
  heart_rate: number | null;
  blood_pressure_systolic: number | null;
  blood_pressure_diastolic: number | null;
  temperature: number | null;
  respiratory_rate: number | null;
  o2_saturation: number | null;
}

// ---------------------------------------------------------------------------
// Patient
// ---------------------------------------------------------------------------

export interface PatientContext {
  name: string;
  age: number;
  sex: string;
  setting: string;
  chief_complaint: string;
  appearance: string;
  backstory: string | null;
  arriving_vitals: VitalSigns;
  triage_note: string | null;
}

// ---------------------------------------------------------------------------
// Game state
// ---------------------------------------------------------------------------

export interface GameState {
  case_id: string;
  current_time_minutes: number;
  flags: string[];
  active_nodes: string[];
  revealed_nodes: string[];
  expired_nodes: string[];
  pending_reveals: Record<string, number>;
  timers: Record<string, number>;
  timer_stages: Record<string, number>;
  current_vitals: VitalSigns;
  available_actions: string[];
  case_ended: boolean;
  outcome_tier: string | null;
  end_reason: string | null;
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

export interface GameEvent {
  type: string;
  timestamp_minutes: number;
  data: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// API responses
// ---------------------------------------------------------------------------

export interface SessionResponse {
  session_id: string;
  state: GameState;
  patient: PatientContext;
  patient_condition: PatientCondition;
  available_actions: string[];
  playable_actions: string[];
}

export interface ActionResponse {
  events: GameEvent[];
  narrations: string[];
  state: GameState;
  patient_condition: PatientCondition;
  available_actions: string[];
  playable_actions: string[];
  case_ended: boolean;
  outcome_tier: string | null;
  end_reason: string | null;
  outcome_narrative: string | null;
}

export interface NodeContentResponse {
  node_id: string;
  narrative_text: string;
  structured_data: Record<string, unknown> | null;
}

export interface ErrorResponse {
  error: string;
  detail: string | null;
}

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/**
 * Patient condition derived server-side via compute_patient_condition.
 * Maps to satori.PatientCondition enum values.
 */
export type PatientCondition =
  | 'stable'
  | 'compensating'
  | 'decompensating'
  | 'critical'
  | 'dead'
  | 'recovered';

/**
 * An entry in the event log: a single turn's events with their narrations.
 */
export interface EventLogEntry {
  action: string;
  timestamp_minutes: number;
  events: GameEvent[];
  narrations: string[];
}

// ---------------------------------------------------------------------------
// UI state
// ---------------------------------------------------------------------------

/**
 * The three views the application can be in.
 */
export type AppView = 'start' | 'play' | 'outcome';
