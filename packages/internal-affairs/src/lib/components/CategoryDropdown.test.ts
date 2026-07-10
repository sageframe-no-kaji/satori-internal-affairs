/**
 * Pins the UD-4/UD-5 keyboard contract (P2-H12): opening focuses the first
 * option, arrows cycle with wrap, Esc and selection return focus to the
 * trigger, and disabled dropdowns expose their reason.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';

import CategoryDropdown from './CategoryDropdown.svelte';

const ACTIONS = [
	{ key: 'order_labs:cbc', label: 'Cbc' },
	{ key: 'order_labs:metabolic_panel', label: 'Metabolic Panel' },
];

function renderDropdown(props: Record<string, unknown> = {}) {
	const onAction = vi.fn();
	const utils = render(CategoryDropdown, {
		categoryLabel: 'Order Labs',
		actions: ACTIONS,
		onAction,
		...props,
	});
	return { ...utils, onAction, trigger: screen.getByRole('button', { name: /Order Labs/ }) };
}

describe('CategoryDropdown', () => {
	it('opening moves focus to the first option (UD-4)', async () => {
		const { trigger } = renderDropdown();
		await fireEvent.click(trigger);
		const options = screen.getAllByRole('option');
		await waitFor(() => expect(options[0]).toHaveFocus());
	});

	it('arrow keys cycle options with wrap (UD-5)', async () => {
		const { trigger } = renderDropdown();
		await fireEvent.click(trigger);
		const options = screen.getAllByRole('option');
		await waitFor(() => expect(options[0]).toHaveFocus());

		await fireEvent.keyDown(options[0], { key: 'ArrowDown' });
		expect(options[1]).toHaveFocus();
		await fireEvent.keyDown(options[1], { key: 'ArrowDown' });
		expect(options[0]).toHaveFocus(); // wrapped
		await fireEvent.keyDown(options[0], { key: 'ArrowUp' });
		expect(options[1]).toHaveFocus(); // wrapped backwards
	});

	it('Escape closes and returns focus to the trigger (UD-5)', async () => {
		const { trigger } = renderDropdown();
		await fireEvent.click(trigger);
		const options = screen.getAllByRole('option');
		await waitFor(() => expect(options[0]).toHaveFocus());

		await fireEvent.keyDown(options[0], { key: 'Escape' });
		expect(screen.queryByRole('listbox')).toBeNull();
		expect(trigger).toHaveFocus();
	});

	it('Enter selects, fires the action, closes, and returns focus', async () => {
		const { trigger, onAction } = renderDropdown();
		await fireEvent.click(trigger);
		const options = screen.getAllByRole('option');
		await waitFor(() => expect(options[0]).toHaveFocus());

		await fireEvent.keyDown(options[0], { key: 'Enter' });
		expect(onAction).toHaveBeenCalledWith('order_labs:cbc');
		expect(screen.queryByRole('listbox')).toBeNull();
		expect(trigger).toHaveFocus();
	});

	it('either arrow key on the trigger opens the menu', async () => {
		const { trigger } = renderDropdown();
		await fireEvent.keyDown(trigger, { key: 'ArrowUp' });
		expect(screen.getByRole('listbox')).toBeInTheDocument();
	});

	it('disabled: does not open and exposes the reason', async () => {
		const { trigger } = renderDropdown({ disabled: true, disabledReason: 'Emergency in progress' });
		await fireEvent.click(trigger);
		expect(screen.queryByRole('listbox')).toBeNull();
		expect(trigger).toHaveAttribute('aria-disabled', 'true');
		expect(trigger).toHaveAccessibleName('Order Labs — Emergency in progress');
		expect(screen.getByRole('tooltip')).toHaveTextContent('Emergency in progress');
	});

	it('locked applies the emergency-locked treatment class', () => {
		const { container } = renderDropdown({ disabled: true, locked: true, disabledReason: 'Locked' });
		expect(container.querySelector('.is-locked')).not.toBeNull();
	});
});
