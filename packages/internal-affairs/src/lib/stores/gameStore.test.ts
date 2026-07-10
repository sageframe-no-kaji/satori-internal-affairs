/**
 * Pins the game store's contract with the API layer: full-state replacement
 * per response, the calm-snapshot presentation memory behind lockedActions
 * (P2-H05), emergency tagging on log entries, and reset.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { ActionResponse, GameState, SessionResponse } from '$lib/types';

vi.mock('$lib/api', () => {
	class ApiError extends Error {
		constructor(
			public readonly status: number,
			message: string
		) {
			super(message);
			this.name = 'ApiError';
		}
	}
	return {
		ApiError,
		createSession: vi.fn(),
		executeAction: vi.fn(),
		getSession: vi.fn(),
		getNodeContent: vi.fn(),
		deleteSession: vi.fn(),
	};
});

import { ApiError, createSession, executeAction } from '$lib/api';
import { game } from './gameStore.svelte';

function makeState(overrides: Partial<GameState> = {}): GameState {
	return {
		case_id: 'case-1',
		current_time_minutes: 0,
		flags: [],
		active_nodes: [],
		revealed_nodes: [],
		expired_nodes: [],
		pending_reveals: {},
		timers: {},
		timer_stages: {},
		current_vitals: {
			heart_rate: 78,
			blood_pressure_systolic: 120,
			blood_pressure_diastolic: 80,
			temperature: 98.6,
			respiratory_rate: 16,
			o2_saturation: 98,
		},
		available_actions: [],
		visible_timers: [],
		emergency_active: false,
		emergency_timer: null,
		findings: [],
		case_ended: false,
		outcome_tier: null,
		end_reason: null,
		...overrides,
	};
}

function sessionResponse(playable: string[]): SessionResponse {
	return {
		session_id: 'sid-1',
		state: makeState(),
		patient: {
			name: 'Maria Santos',
			age: 28,
			sex: 'female',
			setting: 'Emergency Department',
			chief_complaint: 'Seizure',
			appearance: 'Alert but frightened',
			backstory: null,
			arriving_vitals: makeState().current_vitals,
			triage_note: null,
		},
		patient_condition: 'stable',
		available_actions: playable,
		playable_actions: playable,
	};
}

function actionResponse(state: GameState, playable: string[]): ActionResponse {
	return {
		events: [],
		narrations: [],
		state,
		patient_condition: 'stable',
		available_actions: playable,
		playable_actions: playable,
		case_ended: state.case_ended,
		outcome_tier: state.outcome_tier,
		end_reason: state.end_reason,
		outcome_narrative: null,
	};
}

const CALM_ACTIONS = ['history_general', 'order_labs:cbc', 'emergency_intervention'];
const CRISIS_ACTIONS = ['emergency_intervention'];

beforeEach(() => {
	vi.clearAllMocks();
	game.reset();
});

describe('gameStore', () => {
	it('startSession populates state and enters play view', async () => {
		vi.mocked(createSession).mockResolvedValue(sessionResponse(CALM_ACTIONS));
		await game.startSession();
		expect(game.view).toBe('play');
		expect(game.sessionId).toBe('sid-1');
		expect(game.availableActions).toEqual(CALM_ACTIONS);
		expect(game.emergencyActive).toBe(false);
	});

	it('performAction replaces state and prepends the event log, tagged with emergency', async () => {
		vi.mocked(createSession).mockResolvedValue(sessionResponse(CALM_ACTIONS));
		await game.startSession();

		const crisisState = makeState({ current_time_minutes: 195, emergency_active: true });
		vi.mocked(executeAction).mockResolvedValue(actionResponse(crisisState, CRISIS_ACTIONS));
		await game.performAction('wait:60');

		expect(game.gameState?.current_time_minutes).toBe(195);
		expect(game.eventLog).toHaveLength(1);
		expect(game.eventLog[0].action).toBe('wait:60');
		expect(game.eventLog[0].emergency).toBe(true);
	});

	it('lockedActions: calm snapshot minus current playable, only during emergencies (P2-H05)', async () => {
		vi.mocked(createSession).mockResolvedValue(sessionResponse(CALM_ACTIONS));
		await game.startSession();
		expect(game.lockedActions).toEqual([]);

		const crisisState = makeState({ emergency_active: true });
		vi.mocked(executeAction).mockResolvedValue(actionResponse(crisisState, CRISIS_ACTIONS));
		await game.performAction('wait:60');
		expect(game.emergencyActive).toBe(true);
		expect(game.lockedActions).toEqual(['history_general', 'order_labs:cbc']);

		// Rescue: calm again — nothing locked, snapshot refreshed
		vi.mocked(executeAction).mockResolvedValue(actionResponse(makeState(), CALM_ACTIONS));
		await game.performAction('emergency_intervention');
		expect(game.lockedActions).toEqual([]);
	});

	it('case end switches to the outcome view and records the narrative', async () => {
		vi.mocked(createSession).mockResolvedValue(sessionResponse(CALM_ACTIONS));
		await game.startSession();

		const ended = makeState({ case_ended: true, outcome_tier: 'partial' });
		vi.mocked(executeAction).mockResolvedValue({
			...actionResponse(ended, []),
			case_ended: true,
			outcome_tier: 'partial',
			outcome_narrative: 'Maria survives.',
		});
		await game.performAction('start_treatment:albendazole');
		expect(game.view).toBe('outcome');
		expect(game.outcomeNarrative).toBe('Maria survives.');
	});

	it('API errors surface without corrupting state', async () => {
		vi.mocked(createSession).mockResolvedValue(sessionResponse(CALM_ACTIONS));
		await game.startSession();

		vi.mocked(executeAction).mockRejectedValue(new ApiError(400, 'Action order_imaging is currently locked'));
		await game.performAction('order_imaging:ct_head');
		expect(game.error).toBe('Action order_imaging is currently locked');
		expect(game.view).toBe('play');
		expect(game.eventLog).toHaveLength(0);
	});

	it('findings getter mirrors the server-composed list', async () => {
		vi.mocked(createSession).mockResolvedValue(sessionResponse(CALM_ACTIONS));
		await game.startSession();

		const withFinding = makeState({
			findings: [
				{
					node_id: 'node_01_chief_complaint',
					category: 'history',
					label: 'Chief Complaint',
					narrative_text: 'Seizure at work.',
					structured_data: null,
					revealed_at_minutes: 15,
				},
			],
		});
		vi.mocked(executeAction).mockResolvedValue(actionResponse(withFinding, CALM_ACTIONS));
		await game.performAction('history_general');
		expect(game.findings).toHaveLength(1);
		expect(game.findings[0].label).toBe('Chief Complaint');
	});

	it('reset returns everything to the start view', async () => {
		vi.mocked(createSession).mockResolvedValue(sessionResponse(CALM_ACTIONS));
		await game.startSession();
		game.reset();
		expect(game.view).toBe('start');
		expect(game.gameState).toBeNull();
		expect(game.availableActions).toEqual([]);
		expect(game.lockedActions).toEqual([]);
	});
});
