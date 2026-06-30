<!--
  ActiveConcernsPanel — shell for the evidence board.

  H03 fills this panel with finding cards. For H02 this renders
  the panel chrome and empty state only.

  Props:
    findings — array of finding objects (typed loosely until H03 defines the shape).

  Universal Design:
  - 18px+ font size
  - Sufficient contrast on empty-state text
  - Panel is a scrollable region with ARIA landmark
-->
<script lang="ts">
  let {
    findings = [],
  }: {
    findings: unknown[];
  } = $props();
</script>

<section class="panel active-concerns-panel" aria-label="Active Concerns">
  <header class="panel-header">
    <h2 class="panel-title">Active Concerns</h2>
  </header>

  <div class="panel-body">
    {#if findings.length === 0}
      <p class="empty-state">No findings yet.</p>
    {:else}
      <!-- H03 fills this -->
      {#each findings as finding}
        <div class="finding-placeholder">{JSON.stringify(finding)}</div>
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

  .finding-placeholder {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
  }
</style>
