<!--
  ActionMenu — list of available actions as clickable buttons.

  Action strings like "order_labs:cbc" are humanised to "Order Labs: CBC"
  for display. All buttons are disabled while the store is loading to
  prevent double-execution.
-->
<script lang="ts">
  let {
    actions,
    loading,
    onAction,
  }: {
    actions: string[];
    loading: boolean;
    onAction: (action: string) => void;
  } = $props();

  /**
   * Convert an action key to a human-readable label.
   * "order_labs:cbc" → "Order Labs: CBC"
   * "history_general" → "History General"
   */
  function humanise(action: string): string {
    const [base, param] = action.split(':', 2);
    const baseLabel = base
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
    if (param) {
      const paramLabel = param
        .split('_')
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
      return `${baseLabel}: ${paramLabel}`;
    }
    return baseLabel;
  }

  /**
   * Group actions by their base type for visual separation.
   * "order_labs:cbc" → group "Order Labs"
   * "history_general" → group "History"
   */
  function groupActions(actionList: string[]): Map<string, string[]> {
    const groups = new Map<string, string[]>();
    for (const action of actionList) {
      // Split on ':' to get the base action key (e.g. 'order_labs' from 'order_labs:cbc'),
      // then humanise it as the group heading.
      const baseKey = action.split(':')[0];
      const groupKey = baseKey
        .split('_')
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
      if (!groups.has(groupKey)) groups.set(groupKey, []);
      groups.get(groupKey)!.push(action);
    }
    return groups;
  }

  let groups = $derived(groupActions(actions));
</script>

<div class="action-menu">
  <div class="menu-header">Choose an action</div>

  {#if actions.length === 0}
    <p class="no-actions">No actions available.</p>
  {:else}
    {#each [...groups.entries()] as [group, groupActions]}
      <div class="action-group">
        <div class="group-label">{group}</div>
        {#each groupActions as action}
          <button
            class="action-btn"
            disabled={loading}
            onclick={() => onAction(action)}
          >
            {humanise(action)}
          </button>
        {/each}
      </div>
    {/each}
  {/if}
</div>

<style>
  .action-menu {
    background: #1e2330;
    border: 1px solid #2e3447;
    border-radius: 6px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-width: 200px;
  }

  .menu-header {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #7a89a8;
    margin-bottom: 2px;
  }

  .action-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .group-label {
    font-size: 0.7rem;
    font-weight: 600;
    color: #4a5470;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding-bottom: 2px;
    border-bottom: 1px solid #252d3e;
    margin-bottom: 2px;
  }

  .action-btn {
    background: #252d3e;
    border: 1px solid #2e3a52;
    border-radius: 4px;
    color: #b8c2d8;
    cursor: pointer;
    font-size: 0.88rem;
    padding: 7px 10px;
    text-align: left;
    transition: background 0.1s, color 0.1s;
    width: 100%;
  }

  .action-btn:hover:not(:disabled) {
    background: #2e3a52;
    color: #e4eaf8;
  }

  .action-btn:active:not(:disabled) {
    background: #364460;
  }

  .action-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .no-actions {
    font-size: 0.85rem;
    color: #4a5470;
    font-style: italic;
    margin: 0;
  }
</style>
