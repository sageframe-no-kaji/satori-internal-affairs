/**
 * Pins the emergency-mode action bar contract (P2-H05, visual decision 2):
 * locked actions stay in place disabled, wait is disabled with a reason,
 * and emergency_intervention becomes a one-press button that takes focus.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';

import ActionBar from './ActionBar.svelte';

const BASE = {
	actions: ['history_general', 'order_labs:cbc', 'emergency_intervention'],
	loading: false,
	elapsed_minutes: 15,
};

describe('ActionBar', () => {
	it('renders a dropdown per action group plus Wait / Observe', () => {
		render(ActionBar, { ...BASE, onAction: vi.fn() });
		expect(screen.getByRole('button', { name: /History General/ })).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /Order Labs/ })).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /Wait \/ Observe/ })).toBeInTheDocument();
	});

	it('outside emergencies, emergency_intervention is an ordinary dropdown', () => {
		render(ActionBar, { ...BASE, onAction: vi.fn() });
		const trigger = screen.getByRole('button', { name: /Emergency Intervention/ });
		expect(trigger).toHaveAttribute('aria-haspopup', 'listbox');
	});

	it('during an emergency, wait is disabled with the reason', () => {
		render(ActionBar, { ...BASE, emergencyActive: true, onAction: vi.fn() });
		const wait = screen.getByRole('button', { name: /Wait \/ Observe/ });
		expect(wait).toHaveAttribute('aria-disabled', 'true');
		expect(wait).toHaveAccessibleName(/Emergency in progress/);
	});

	it('locked actions render disabled, in place, with the lock reason', () => {
		render(ActionBar, {
			...BASE,
			actions: ['order_labs:cbc', 'emergency_intervention'],
			lockedActions: ['history_general'],
			emergencyActive: true,
			onAction: vi.fn(),
		});
		const history = screen.getByRole('button', { name: /History General/ });
		expect(history).toHaveAttribute('aria-disabled', 'true');
		expect(history).toHaveAccessibleName(/Locked: emergency in progress/);
	});

	it('during an emergency, emergency_intervention is a one-press button that takes focus', async () => {
		const onAction = vi.fn();
		render(ActionBar, { ...BASE, emergencyActive: true, onAction });
		const button = screen.getByRole('button', { name: 'Emergency Intervention' });
		expect(button).not.toHaveAttribute('aria-haspopup');
		await waitFor(() => expect(button).toHaveFocus());
		await fireEvent.click(button);
		expect(onAction).toHaveBeenCalledWith('emergency_intervention');
	});

	it('merged ordering: locked and playable groups sort together (spatial stability)', () => {
		const { container } = render(ActionBar, {
			...BASE,
			actions: ['order_labs:cbc'],
			lockedActions: ['history_general'],
			emergencyActive: true,
			onAction: vi.fn(),
		});
		const labels = [...container.querySelectorAll('.category-label')].map((el) => el.textContent);
		// history_general < order_labs alphabetically — locked group holds its place
		expect(labels.indexOf('History General')).toBeLessThan(labels.indexOf('Order Labs'));
	});

	it('shows the game clock', () => {
		render(ActionBar, { ...BASE, onAction: vi.fn() });
		expect(screen.getByText(/T\+15/)).toBeInTheDocument();
	});
});
