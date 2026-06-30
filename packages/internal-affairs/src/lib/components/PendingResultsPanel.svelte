<!--
  PendingResultsPanel — diegetic countdown timers.

  Renders visible_timers from game state as countdown cards. The engine
  provides timers sorted by remaining_minutes ascending, then node_id.
  We trust that order and do not re-sort here.

  Each item shows the label and an intentionally-approximate remaining time:
    > 10 min  → round to nearest 5   (e.g. 27 → "~25 min")
    ≤ 10 min  → round to nearest 1   (e.g. 7  → "~7 min")

  This is the only place in the UI (besides emergencies) where a clock is
  shown. Deterioration timers remain hidden by design.

  Universal Design:
  - 18px+ font throughout
  - Each timer card meets the 60px touch-target height floor
  - High-contrast text on panel background
  - ARIA landmark on the section
-->
<script lang="ts">
  import type { VisibleTimer } from '$lib/types';

  let { timers }: { timers: VisibleTimer[] } = $props();

  /**
   * Produce an intentionally-approximate display string for remaining minutes.
   *
   * > 10  → nearest 5 (e.g. 27 → "~25 min", 23 → "~25 min")
   * ≤ 10  → nearest 1 (e.g. 7 → "~7 min", 0 → "~0 min")
   */
  function formatRemaining(minutes: number): string {
    if (minutes > 10) {
      const rounded = Math.round(minutes / 5) * 5;
      return `~${rounded} min`;
    }
    return `~${minutes} min`;
  }

  /**
   * Return the icon character for a timer's source type.
   *
   * pending_reveal → hourglass (ordered result in progress)
   * active_timer   → bell     (active diegetic event)
   */
  function sourceIcon(source: VisibleTimer['source']): string {
    return source === 'pending_reveal' ? '⏳' : '🔔';
  }
</script>

<section class="panel pending-results-panel" aria-label="Pending Results">
  <header class="panel-header">
    <h2 class="panel-title">Pending Results</h2>
  </header>

  <div class="panel-body">
    {#if timers.length === 0}
      <p class="empty-state">No pending results.</p>
    {:else}
      <ul class="results-list" role="list">
        {#each timers as timer (timer.node_id)}
          <li class="result-card" class:active-timer={timer.source === 'active_timer'}>
            <span class="card-icon" aria-hidden="true">{sourceIcon(timer.source)}</span>
            <span class="card-label">{timer.label}</span>
            <span class="card-remaining" aria-label="approximately {timer.remaining_minutes} minutes remaining">
              {formatRemaining(timer.remaining_minutes)}
            </span>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</section>

<style>
  .panel {
    background: var(--color-bg-panel);
    border: var(--border-width) solid var(--color-border);
    border-radius: var(--radius);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-shadow: var(--shadow-panel);
  }

  .panel-header {
    padding: var(--space-3) var(--space-4);
    border-bottom: var(--border-width) solid var(--color-border);
    flex-shrink: 0;
  }

  .panel-title {
    font-size: var(--font-size-base);
    font-weight: 600;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 0;
  }

  .panel-body {
    flex: 1;
    overflow-y: auto;
    padding: var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .empty-state {
    font-size: var(--font-size-base);
    color: var(--color-text-dim);
    font-style: italic;
    margin: 0;
    line-height: var(--line-height);
  }

  /* --- Timer cards --- */

  .results-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .result-card {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    min-height: var(--touch-target-min);
    padding: var(--space-3) var(--space-4);
    background: var(--color-bg-panel-alt);
    border: var(--border-width) solid var(--color-border);
    border-radius: var(--radius);
  }

  /* active_timer cards get a subtle info-colour left accent */
  .result-card.active-timer {
    border-left: var(--space-1) solid var(--color-state-info);
    padding-left: calc(var(--space-4) - var(--space-1));
  }

  .card-icon {
    font-size: var(--font-size-lg);
    flex-shrink: 0;
    line-height: 1;
  }

  .card-label {
    flex: 1;
    font-size: var(--font-size-base);
    color: var(--color-text);
    line-height: var(--line-height);
  }

  .card-remaining {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    white-space: nowrap;
    flex-shrink: 0;
  }
</style>
