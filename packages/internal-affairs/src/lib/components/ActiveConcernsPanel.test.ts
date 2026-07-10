/**
 * Pins the evidence board (P2-H03 decision A + P2-H11 windowshade/fresh):
 * fixed-order sections with counts, flag chips, shade toggles, and the
 * fresh-evidence highlight with auto-shade of stale sections.
 */
import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';

import type { Finding } from '$lib/types';
import ActiveConcernsPanel from './ActiveConcernsPanel.svelte';

function finding(overrides: Partial<Finding>): Finding {
	return {
		node_id: 'node_01_chief_complaint',
		category: 'history',
		label: 'Chief Complaint',
		narrative_text: 'Sudden speech difficulty and seizure at work.',
		structured_data: null,
		revealed_at_minutes: 15,
		...overrides,
	};
}

const HISTORY = finding({});
const CBC = finding({
	node_id: 'node_04_cbc_results',
	category: 'lab_result',
	label: 'Cbc Results',
	narrative_text: 'Eosinophils 8%.',
	structured_data: { eosinophils_percent: 8, eosinophils_flag: 'HIGH' },
	revealed_at_minutes: 57,
});

describe('ActiveConcernsPanel', () => {
	it('renders the empty state with no findings', () => {
		render(ActiveConcernsPanel, { findings: [] });
		expect(screen.getByText('No findings yet.')).toBeInTheDocument();
	});

	it('groups findings under fixed-order category headers with counts', () => {
		render(ActiveConcernsPanel, { findings: [CBC, HISTORY] });
		const headers = screen.getAllByRole('button').map((b) => b.textContent);
		expect(headers[0]).toContain('History (1)');
		expect(headers[1]).toContain('Labs (1)');
	});

	it('renders flag chips from structured data', () => {
		render(ActiveConcernsPanel, { findings: [CBC] });
		expect(screen.getByText('Eosinophils: HIGH')).toBeInTheDocument();
	});

	it('renders the reveal timestamp', () => {
		render(ActiveConcernsPanel, { findings: [CBC] });
		expect(screen.getByText(/T\+57/)).toBeInTheDocument();
	});

	it('windowshade: header click collapses and reopens the section', async () => {
		render(ActiveConcernsPanel, { findings: [HISTORY] });
		const header = screen.getByRole('button', { name: /History \(1\)/ });
		expect(header).toHaveAttribute('aria-expanded', 'true');
		expect(screen.getByText('Chief Complaint')).toBeInTheDocument();

		await fireEvent.click(header);
		expect(header).toHaveAttribute('aria-expanded', 'false');
		expect(screen.queryByText('Chief Complaint')).toBeNull();

		await fireEvent.click(header);
		expect(screen.getByText('Chief Complaint')).toBeInTheDocument();
	});

	it('fresh evidence: new finding highlights its section, other sections auto-shade', async () => {
		const { rerender, container } = render(ActiveConcernsPanel, { findings: [HISTORY] });

		await rerender({ findings: [HISTORY, CBC] });

		const labsHeader = screen.getByRole('button', { name: /Labs \(1\)/ });
		const historyHeader = screen.getByRole('button', { name: /History \(1\)/ });
		expect(labsHeader).toHaveClass('is-fresh');
		expect(labsHeader).toHaveAttribute('aria-expanded', 'true');
		expect(historyHeader).toHaveAttribute('aria-expanded', 'false'); // auto-shaded
		expect(container.querySelector('.finding-card.is-fresh')).not.toBeNull();
	});

	it('fresh highlight self-clears when the next turn brings nothing new', async () => {
		const { rerender } = render(ActiveConcernsPanel, { findings: [HISTORY] });
		await rerender({ findings: [HISTORY, CBC] });
		await rerender({ findings: [HISTORY, CBC] });
		// same set again — rerender with identical ids clears freshness
		expect(screen.getByRole('button', { name: /Labs \(1\)/ })).not.toHaveClass('is-fresh');
	});

	it('unknown categories fall through to Other', () => {
		render(ActiveConcernsPanel, {
			findings: [finding({ category: 'mystery', node_id: 'node_99_x', label: 'X' })],
		});
		expect(screen.getByRole('button', { name: /Other \(1\)/ })).toBeInTheDocument();
	});
});
