import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';

import EmergencyBanner from './EmergencyBanner.svelte';

describe('EmergencyBanner', () => {
	it('renders the crisis label with the intervene call', () => {
		render(EmergencyBanner, { label: 'Seizure Crisis', remaining_minutes: 4 });
		expect(screen.getByText('Seizure Crisis — Intervene')).toBeInTheDocument();
	});

	it('renders the exact countdown', () => {
		render(EmergencyBanner, { label: 'Seizure Crisis', remaining_minutes: 4 });
		expect(screen.getByLabelText('4 minutes remaining')).toBeInTheDocument();
	});

	it('announces as an alert', () => {
		render(EmergencyBanner, { label: 'Seizure Crisis', remaining_minutes: 4 });
		expect(screen.getByRole('alert')).toBeInTheDocument();
	});
});
