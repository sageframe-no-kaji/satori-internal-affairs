<!--
  ActionBar — bottom bar composing one CategoryDropdown per action category.

  Groups playable_actions by base key (e.g. 'order_labs' from 'order_labs:cbc').
  Each group becomes a CategoryDropdown. The Wait/Observe action is not
  added in H02 — see TODO below.

  Right side shows the game clock (Clock: T+N min).

  Universal Design:
  - All interactive elements: min-height var(--touch-target-pref) = 72px
  - Gap between interactive elements: var(--touch-target-gap) = 16px
  - Keyboard-navigable (delegated to CategoryDropdown per-button)
  - No hover-only behaviours

  Props:
    actions         — array of available action key strings ('order_labs:cbc')
    loading         — disables all actions while the store is loading
    elapsed_minutes — current game clock in minutes (displayed as T+N min)
    onAction        — callback with the selected action key
-->
<script lang="ts">
  import CategoryDropdown from './CategoryDropdown.svelte';

  let {
    actions,
    loading,
    elapsed_minutes,
    onAction,
  }: {
    actions: string[];
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

  let groups = $derived(buildGroups(actions));
</script>

<div class="action-bar" role="toolbar" aria-label="Clinical actions">
  <div class="action-groups">
    {#if groups.length === 0}
      <span class="no-actions">No actions available.</span>
    {:else}
      {#each groups as group}
        <CategoryDropdown
          categoryLabel={group.label}
          actions={group.items}
          disabled={loading}
          disabledReason={loading ? 'Processing previous action…' : ''}
          {onAction}
        />
      {/each}
    {/if}

    <!--
      TODO H06: add Wait/Observe CategoryDropdown here.
      It will use the built-in 'wait' base action with subcategories
      wait:15, wait:30, wait:60 (durations in minutes).
    -->
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

  .clock {
    font-size: var(--font-size-base);
    color: var(--color-text-muted);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    flex-shrink: 0;
  }
</style>
