import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';

import type { VitalSigns } from '$lib/types';
import VitalsStrip from './VitalsStrip.svelte';

function vitals(overrides: Partial<VitalSigns> = {}): VitalSigns {
	return {
		heart_rate: 78,
		blood_pressure_systolic: 120,
		blood_pressure_diastolic: 80,
		temperature: 98.6,
		respiratory_rate: 16,
		o2_saturation: 98,
		...overrides,
	};
}

describe('VitalsStrip', () => {
	it('renders the SpO₂ label correctly (regression: malformed &sub2; entity)', () => {
		render(VitalsStrip, { vitals: vitals(), condition: 'stable', elapsed_minutes: 0 });
		expect(screen.getByText('SpO₂')).toBeInTheDocument();
	});

	it('normal vitals render in the normal state', () => {
		const { container } = render(VitalsStrip, {
			vitals: vitals(),
			condition: 'stable',
			elapsed_minutes: 0,
		});
		expect(container.querySelectorAll('.vital-normal')).toHaveLength(5);
		expect(container.querySelector('.vital-critical')).toBeNull();
	});

	it('crisis vitals render critical (HR > 150, SpO₂ < 88, systolic < 90)', () => {
		const { container } = render(VitalsStrip, {
			vitals: vitals({ heart_rate: 152, o2_saturation: 84, blood_pressure_systolic: 78 }),
			condition: 'critical',
			elapsed_minutes: 195,
		});
		expect(container.querySelectorAll('.vital-critical').length).toBeGreaterThanOrEqual(3);
	});

	it('moderate deviation renders the warning state', () => {
		const { container } = render(VitalsStrip, {
			vitals: vitals({ heart_rate: 130 }),
			condition: 'compensating',
			elapsed_minutes: 60,
		});
		expect(container.querySelector('.vital-warn')).not.toBeNull();
	});

	it('shows the condition badge and clock', () => {
		render(VitalsStrip, { vitals: vitals(), condition: 'compensating', elapsed_minutes: 15 });
		expect(screen.getByText('Compensating')).toBeInTheDocument();
		expect(screen.getByText(/T\+15/)).toBeInTheDocument();
	});

	it('missing vitals render as em dashes, not crashes', () => {
		render(VitalsStrip, {
			vitals: vitals({ temperature: null, respiratory_rate: null }),
			condition: 'stable',
			elapsed_minutes: 0,
		});
		expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(2);
	});
});
