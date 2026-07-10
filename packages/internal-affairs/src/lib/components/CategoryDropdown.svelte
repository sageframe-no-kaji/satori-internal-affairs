<!--
  CategoryDropdown — one action category button that expands to show subcategories.

  Universal Design requirements:
  - All interactive elements: min-height var(--touch-target-pref) = 72px
  - Gap between elements >= var(--space-4) = 16px
  - Keyboard (ARIA listbox, P2-H12): Enter/Space/arrows open and focus the
    first option; arrows cycle with wrap; Home/End jump; Esc and selection
    close and return focus to the trigger; Tab out closes; click-off closes
    without stealing focus
  - No hover-only behaviours: focus and active show the same states as hover
  - Visible focus rings on all interactive elements

  Props:
    categoryLabel  — display name for the category button (e.g. "Order Labs")
    actions        — array of { key, label } subcategory options
    disabled       — disables the entire dropdown when true
    disabledReason — reason shown on hover AND focus (and via aria-label)
    locked         — emergency-locked treatment (P2-H05): grayed further in
                     place rather than the generic disabled look
    onAction       — callback with the selected action key
-->
<script lang="ts">
  import { tick } from 'svelte';

  let {
    categoryLabel,
    actions,
    disabled = false,
    disabledReason = '',
    locked = false,
    onAction,
  }: {
    categoryLabel: string;
    actions: Array<{ key: string; label: string }>;
    disabled?: boolean;
    disabledReason?: string;
    locked?: boolean;
    onAction: (key: string) => void;
  } = $props();

  let isOpen = $state(false);
  let rootEl = $state<HTMLDivElement | null>(null);
  let triggerEl = $state<HTMLButtonElement | null>(null);
  let listEl = $state<HTMLUListElement | null>(null);

  function optionEls(): HTMLElement[] {
    return listEl ? [...listEl.querySelectorAll<HTMLElement>('[role="option"]')] : [];
  }

  function open() {
    if (disabled) return;
    isOpen = true;
    // UD-4: focus lands on the first option once the list renders
    void tick().then(() => optionEls()[0]?.focus());
  }

  /** returnFocus: true for keyboard/selection paths (UD-5 — focus must not
      drop to <body>); false for click-off (the player aimed elsewhere). */
  function close(returnFocus: boolean) {
    isOpen = false;
    if (returnFocus) triggerEl?.focus();
  }

  function toggle() {
    if (disabled) return;
    if (isOpen) close(true);
    else open();
  }

  /** Click/tap anywhere outside this dropdown closes it. */
  function handleOutsidePointer(e: PointerEvent) {
    if (isOpen && rootEl && !rootEl.contains(e.target as Node)) {
      close(false);
    }
  }

  /** Tab (or any focus move) out of the component closes the menu. */
  function handleFocusOut(e: FocusEvent) {
    if (isOpen && rootEl && !rootEl.contains(e.relatedTarget as Node)) {
      close(false);
    }
  }

  function handleAction(key: string) {
    onAction(key);
    close(true);
  }

  function handleTriggerKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggle();
    } else if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
      // Either arrow opens (the menu folds up, so Up is the natural gesture)
      e.preventDefault();
      if (!isOpen) open();
      else optionEls()[0]?.focus();
    } else if (e.key === 'Escape') {
      close(true);
    }
  }

  function handleOptionKeydown(e: KeyboardEvent, key: string) {
    const opts = optionEls();
    const idx = opts.indexOf(e.currentTarget as HTMLElement);
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleAction(key);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      close(true);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      opts[(idx + 1) % opts.length]?.focus();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      opts[(idx - 1 + opts.length) % opts.length]?.focus();
    } else if (e.key === 'Home') {
      e.preventDefault();
      opts[0]?.focus();
    } else if (e.key === 'End') {
      e.preventDefault();
      opts[opts.length - 1]?.focus();
    }
  }
</script>

<svelte:window onpointerdown={handleOutsidePointer} />

<div
  class="category-dropdown"
  bind:this={rootEl}
  class:is-open={isOpen}
  class:is-disabled={disabled}
  class:is-locked={locked}
  onfocusout={handleFocusOut}
>
  <button
    bind:this={triggerEl}
    class="category-trigger"
    type="button"
    aria-haspopup="listbox"
    aria-expanded={isOpen}
    aria-disabled={disabled}
    aria-label={disabled && disabledReason ? `${categoryLabel} — ${disabledReason}` : undefined}
    onclick={toggle}
    onkeydown={handleTriggerKeydown}
  >
    <span class="category-label">{categoryLabel}</span>
    <span class="dropdown-arrow" aria-hidden="true">{isOpen ? '▾' : '▴'}</span>
  </button>

  {#if disabled && disabledReason}
    <!-- Visible on hover AND keyboard focus — no hover-only behaviours -->
    <span class="disabled-reason" role="tooltip">{disabledReason}</span>
  {/if}

  {#if isOpen}
    <ul bind:this={listEl} class="subcategory-list" role="listbox" aria-label="{categoryLabel} options">
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

  /* Emergency-locked (P2-H05): grayed further, but still in place — spatial
     memory is the point of the inline treatment. */
  .is-locked .category-trigger {
    opacity: var(--emergency-locked-opacity);
  }

  /* Lock reason: hidden until the trigger is hovered or keyboard-focused.
     Positioned above the button — the action bar sits at the viewport bottom. */
  .disabled-reason {
    position: absolute;
    bottom: 100%;
    left: 0;
    margin-bottom: var(--space-1);
    padding: var(--space-1) var(--space-3);
    background: var(--color-bg-panel-alt);
    border: var(--border-width) solid var(--color-border-strong);
    border-radius: var(--radius-sm);
    color: var(--color-text-muted);
    font-size: var(--font-size-sm);
    white-space: nowrap;
    box-shadow: var(--shadow-panel);
    opacity: 0;
    pointer-events: none;
    z-index: 100;
  }

  .category-dropdown:hover .disabled-reason,
  .category-trigger:focus-visible ~ .disabled-reason {
    opacity: 1;
  }

  /* The action bar is pinned to the viewport bottom (P2-H11), so menus
     always fold UP — opening downward would clip at the screen edge. */
  .is-open .category-trigger {
    border-color: var(--color-accent);
    border-top-left-radius: 0;
    border-top-right-radius: 0;
  }

  .dropdown-arrow {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    pointer-events: none;
  }

  .subcategory-list {
    position: absolute;
    bottom: 100%;
    left: 0;
    min-width: 100%;
    list-style: none;
    margin: 0;
    padding: var(--space-1) 0;
    background: var(--color-bg-panel-alt);
    border: var(--border-width) solid var(--color-accent);
    border-bottom: none;
    border-top-left-radius: var(--radius);
    border-top-right-radius: var(--radius);
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
