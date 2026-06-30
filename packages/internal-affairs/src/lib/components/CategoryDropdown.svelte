<!--
  CategoryDropdown — one action category button that expands to show subcategories.

  Universal Design requirements:
  - All interactive elements: min-height var(--touch-target-pref) = 72px
  - Gap between elements >= var(--space-4) = 16px
  - Keyboard navigation: Enter to toggle open, Esc to close, Tab through options
  - No hover-only behaviours: focus and active show the same states as hover
  - Visible focus rings on all interactive elements

  Props:
    categoryLabel  — display name for the category button (e.g. "Order Labs")
    actions        — array of { key, label } subcategory options
    disabled       — disables the entire dropdown when true
    disabledReason — tooltip / aria-label clarifying why it's disabled
    onAction       — callback with the selected action key
-->
<script lang="ts">
  let {
    categoryLabel,
    actions,
    disabled = false,
    disabledReason = '',
    onAction,
  }: {
    categoryLabel: string;
    actions: Array<{ key: string; label: string }>;
    disabled?: boolean;
    disabledReason?: string;
    onAction: (key: string) => void;
  } = $props();

  let isOpen = $state(false);

  function toggle() {
    if (disabled) return;
    isOpen = !isOpen;
  }

  function close() {
    isOpen = false;
  }

  function handleAction(key: string) {
    onAction(key);
    close();
  }

  function handleTriggerKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggle();
    } else if (e.key === 'Escape') {
      close();
    }
  }

  function handleOptionKeydown(e: KeyboardEvent, key: string) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleAction(key);
    } else if (e.key === 'Escape') {
      close();
    }
  }
</script>

<div class="category-dropdown" class:is-open={isOpen} class:is-disabled={disabled}>
  <button
    class="category-trigger"
    type="button"
    aria-haspopup="listbox"
    aria-expanded={isOpen}
    aria-disabled={disabled}
    title={disabled && disabledReason ? disabledReason : undefined}
    onclick={toggle}
    onkeydown={handleTriggerKeydown}
  >
    <span class="category-label">{categoryLabel}</span>
    <span class="dropdown-arrow" aria-hidden="true">{isOpen ? '▴' : '▾'}</span>
  </button>

  {#if isOpen}
    <ul class="subcategory-list" role="listbox" aria-label="{categoryLabel} options">
      {#each actions as action}
        <li
          class="subcategory-option"
          role="option"
          aria-selected="false"
          tabindex="0"
          onclick={() => handleAction(action.key)}
          onkeydown={(e) => handleOptionKeydown(e, action.key)}
        >
          {action.label}
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .category-dropdown {
    position: relative;
    display: inline-flex;
    flex-direction: column;
  }

  .category-trigger {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
    min-height: var(--touch-target-pref);
    padding: 0 var(--space-4);
    background: var(--color-bg-panel-alt);
    border: var(--border-width) solid var(--color-border);
    border-radius: var(--radius);
    color: var(--color-accent);
    font-family: var(--font-stack);
    font-size: var(--font-size-base);
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.1s, border-color 0.1s;
  }

  .category-trigger:hover:not([aria-disabled='true']),
  .category-trigger:focus-visible {
    background: var(--color-bg-panel);
    border-color: var(--color-border-strong);
    color: var(--color-accent-hover);
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }

  .category-trigger:active:not([aria-disabled='true']) {
    color: var(--color-accent-active);
  }

  .is-disabled .category-trigger {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .is-open .category-trigger {
    border-color: var(--color-accent);
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
  }

  .dropdown-arrow {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    pointer-events: none;
  }

  .subcategory-list {
    position: absolute;
    top: 100%;
    left: 0;
    min-width: 100%;
    list-style: none;
    margin: 0;
    padding: var(--space-1) 0;
    background: var(--color-bg-panel-alt);
    border: var(--border-width) solid var(--color-accent);
    border-top: none;
    border-bottom-left-radius: var(--radius);
    border-bottom-right-radius: var(--radius);
    z-index: 100;
    box-shadow: var(--shadow-panel);
  }

  .subcategory-option {
    display: flex;
    align-items: center;
    min-height: var(--touch-target-min);
    padding: 0 var(--space-4);
    font-family: var(--font-stack);
    font-size: var(--font-size-base);
    color: var(--color-text);
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.1s;
  }

  .subcategory-option:hover,
  .subcategory-option:focus-visible {
    background: var(--color-bg-panel);
    color: var(--color-accent-hover);
    outline: 2px solid var(--color-accent);
    outline-offset: -2px;
  }

  .subcategory-option:active {
    background: var(--color-bg-app);
  }
</style>
