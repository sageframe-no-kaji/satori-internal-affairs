<!--
  PendingResultsPanel — shell for diegetic countdown timers.

  H04 fills this panel with timer cards from visible_timers. For H02 this
  renders the panel chrome and empty state only.

  Props:
    timers — array of VisibleTimer objects (typed as unknown[] until H01
             adds the VisibleTimer type to the shared types module).

  Universal Design:
  - 18px+ font size
  - Sufficient contrast on empty-state text
  - Panel is a scrollable region with ARIA landmark
-->
<script lang="ts">
  let {
    timers = [],
  }: {
    timers: unknown[];
  } = $props();
</script>

<section class="panel pending-results-panel" aria-label="Pending Results">
  <header class="panel-header">
    <h2 class="panel-title">Pending Results</h2>
  </header>

  <div class="panel-body">
    {#if timers.length === 0}
      <p class="empty-state">No pending results.</p>
    {:else}
      <!-- H04 fills this with timer cards -->
      {#each timers as timer}
        <div class="timer-placeholder">{JSON.stringify(timer)}</div>
      {/each}
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

  .timer-placeholder {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
  }
</style>
