<!--
  ActionBar — bottom bar composing one CategoryDropdown per action category.

  Groups playable_actions by base key (e.g. 'order_labs' from 'order_labs:cbc').
  Each group becomes a CategoryDropdown.

  Emergency mode (P2-H05, visual decision 2 — grayed inline):
  - Locked actions (in the store's calm snapshot but no longer playable) stay
    in their usual positions, disabled, with the reason on focus and hover.
    Both lists arrive sorted, so merging and re-sorting reproduces the calm
    ordering — no button moves when a crisis starts or ends.
  - emergency_intervention renders as a single prominent button (one press,
    not dropdown-then-select) and receives focus when the crisis begins.
  - Wait / Observe is disabled during emergencies (H06's decision, wired here).

  Right side shows the game clock (Clock: T+N min).

  Universal Design:
  - All interactive elements: min-height var(--touch-target-pref) = 72px
  - Gap between interactive elements: var(--touch-target-gap) = 16px
  - Keyboard-navigable (delegated to CategoryDropdown per-button)
  - No hover-only behaviours; lock reasons surface via title AND aria-label
  - Focus moves to the emergency action when a crisis starts — zero
    navigation cost to act under motor constraints

  Props:
    actions         — array of playable action key strings ('order_labs:cbc')
    lockedActions   — action keys locked by the current emergency (display only)
    emergencyActive — true while a crisis is in progress (server-derived)
    loading         — disables all actions while the store is loading
    elapsed_minutes — current game clock in minutes (displayed as T+N min)
    onAction        — callback with the selected action key
-->
<script lang="ts">
  import CategoryDropdown from './CategoryDropdown.svelte';

  const EMERGENCY_BASE = 'emergency_intervention';
  const LOCKED_REASON = 'Locked: emergency in progress';

  let {
    actions,
    lockedActions = [],
    emergencyActive = false,
    loading,
    elapsed_minutes,
    onAction,
  }: {
    actions: string[];
    lockedActions?: string[];
    emergencyActive?: boolean;
    loading: boolean;
    elapsed_minutes: number;
    onAction: (action: string) => void;
  } = $props();

  interface ActionGroup {
    label: string;
    baseKey: string;
    items: Array<{ key: string; label: string }>;
  }

  /** Convert a snake_case action key to Title Case label. */
  function humanise(key: string): string {
    return key
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  }

  /** Group action strings by base key. Returns ordered array. */
  function buildGroups(actionList: string[]): ActionGroup[] {
    const map = new Map<string, ActionGroup>();
    for (const action of actionList) {
      const [base, sub] = action.split(':', 2);
      const label = humanise(base);
      if (!map.has(base)) {
        map.set(base, { label, baseKey: base, items: [] });
      }
      const subLabel = sub ? humanise(sub) : label;
      map.get(base)!.items.push({ key: action, label: subLabel });
    }
    return [...map.values()];
  }

  // Playable + locked merged and re-sorted: reproduces the calm-state
  // ordering, so every button keeps its place through a crisis.
  let groups = $derived(buildGroups([...actions, ...lockedActions].sort()));
  let lockedBases = $derived(new Set(lockedActions.map((a) => a.split(':', 2)[0])));

  // Focus the emergency action the moment a crisis starts.
  let emergencyButton = $state<HTMLButtonElement | null>(null);
  $effect(() => {
    if (emergencyActive && emergencyButton) {
      emergencyButton.focus();
    }
  });
</script>

<div class="action-bar" role="toolbar" aria-label="Clinical actions">
  <div class="action-groups">
    {#if groups.length === 0}
      <span class="no-actions">No actions available.</span>
    {:else}
      {#each groups as group (group.baseKey)}
        {#if emergencyActive && group.baseKey === EMERGENCY_BASE}
          <!-- One press to act: no dropdown between the player and the rescue -->
          <button
            bind:this={emergencyButton}
            class="emergency-action"
            type="button"
            disabled={loading}
            onclick={() => onAction(EMERGENCY_BASE)}
          >
            {group.label}
          </button>
        {:else}
          <CategoryDropdown
            categoryLabel={group.label}
            actions={group.items}
            disabled={loading || lockedBases.has(group.baseKey)}
            disabledReason={loading ? 'Processing previous action…' : LOCKED_REASON}
            locked={lockedBases.has(group.baseKey)}
            {onAction}
          />
        {/if}
      {/each}
    {/if}

    <!-- Wait / Observe — always visible, sibling to clinical-action categories -->
    <CategoryDropdown
      categoryLabel="Wait / Observe"
      actions={[
        { key: 'wait:15', label: '15 minutes' },
        { key: 'wait:30', label: '30 minutes' },
        { key: 'wait:60', label: '60 minutes' },
      ]}
      disabled={loading || emergencyActive}
      disabledReason={loading ? 'Processing previous action…' : 'Emergency in progress'}
      locked={emergencyActive}
      {onAction}
    />
  </div>

  <div class="clock" aria-label="Game clock: {elapsed_minutes} minutes elapsed">
    Clock: T+{elapsed_minutes}&nbsp;min
  </div>
</div>

<style>
  .action-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-4);
    background: var(--color-bg-panel);
    border: var(--border-width) solid var(--color-border);
    border-radius: var(--radius);
    padding: var(--space-3) var(--space-4);
    min-height: var(--touch-target-pref);
    flex-wrap: wrap;
  }

  .action-groups {
    display: flex;
    align-items: center;
    gap: var(--touch-target-gap);
    flex-wrap: wrap;
  }

  .no-actions {
    font-size: var(--font-size-base);
    color: var(--color-text-dim);
    font-style: italic;
  }

  .emergency-action {
    min-height: var(--touch-target-pref);
    padding: 0 var(--space-6);
    background: var(--color-emergency-bg);
    border: var(--border-width) solid var(--color-state-critical);
    border-radius: var(--radius);
    color: var(--color-emergency-text);
    font-family: var(--font-stack);
    font-size: var(--font-size-lg);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.1s;
  }

  .emergency-action:hover:not(:disabled),
  .emergency-action:focus-visible {
    background: var(--color-badge-bg-critical);
    outline: 2px solid var(--color-state-critical);
    outline-offset: 2px;
  }

  .emergency-action:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .clock {
    font-size: var(--font-size-base);
    color: var(--color-text-muted);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    flex-shrink: 0;
  }
</style>
