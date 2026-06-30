<!--
  Root page — mission-control dashboard (Phase 2).

  Three views:
    start   → Load Case card
    play    → Full dashboard (header + vitals strip + three-column body + action bar)
    outcome → OutcomeScreen overlays the dashboard (dashboard visible beneath)

  All state is driven by the game store (gameStore.svelte.ts).
  This page never calls the API directly.
-->
<script lang="ts">
  import PatientHeader from '$lib/components/PatientHeader.svelte';
  import VitalsStrip from '$lib/components/VitalsStrip.svelte';
  import ActiveConcernsPanel from '$lib/components/ActiveConcernsPanel.svelte';
  import NarrativeFeedPanel from '$lib/components/NarrativeFeedPanel.svelte';
  import PendingResultsPanel from '$lib/components/PendingResultsPanel.svelte';
  import ActionBar from '$lib/components/ActionBar.svelte';
  import OutcomeScreen from '$lib/components/OutcomeScreen.svelte';
  import { game, DEFAULT_CASE_PATH } from '$lib/stores/gameStore.svelte';
</script>

<!-- ------------------------------------------------------------------ -->
<!-- Start view                                                           -->
<!-- ------------------------------------------------------------------ -->
{#if game.view === 'start'}
  <div class="start-view">
    <div class="start-card">
      <h1 class="game-title">Internal Affairs</h1>
      <p class="game-subtitle">Medical Mystery Simulator</p>

      {#if game.error}
        <div class="error-banner" role="alert">{game.error}</div>
      {/if}

      <button
        class="start-btn"
        disabled={game.isLoading}
        onclick={() => game.startSession(DEFAULT_CASE_PATH)}
      >
        {game.isLoading ? 'Loading case…' : 'Load Case'}
      </button>

      <p class="case-hint">Case: neurocysticercosis (Maria Santos, 28F)</p>
    </div>
  </div>

<!-- ------------------------------------------------------------------ -->
<!-- Play view + outcome overlay                                          -->
<!-- ------------------------------------------------------------------ -->
{:else if (game.view === 'play' || game.view === 'outcome') && game.gameState && game.patient}
  <main class="dashboard">
    <!-- Row 1: patient header -->
    <div class="dashboard-header">
      <PatientHeader patient={game.patient} />
    </div>

    <!-- Row 2: vitals strip -->
    <div class="dashboard-vitals">
      <VitalsStrip
        vitals={game.gameState.current_vitals}
        condition={game.patientCondition}
        elapsed_minutes={game.gameState.current_time_minutes}
      />
    </div>

    <!-- Row 3: three-column body -->
    <div class="dashboard-body">
      <ActiveConcernsPanel findings={[]} />
      <NarrativeFeedPanel events={game.eventLog} />
      <PendingResultsPanel timers={[]} />
    </div>

    <!-- Row 4: action bar -->
    <div class="dashboard-actions">
      {#if game.error}
        <div class="error-banner inline-error" role="alert">{game.error}</div>
      {/if}
      <ActionBar
        actions={game.availableActions}
        loading={game.isLoading}
        elapsed_minutes={game.gameState.current_time_minutes}
        onAction={(action) => game.performAction(action)}
      />
    </div>
  </main>

  <!-- Outcome overlay — fixed over the dashboard when case ends -->
  {#if game.view === 'outcome'}
    <div class="outcome-overlay" role="dialog" aria-modal="true" aria-label="Case outcome">
      <OutcomeScreen
        outcome_tier={game.gameState.outcome_tier}
        end_reason={game.gameState.end_reason}
        outcome_narrative={game.outcomeNarrative}
        onReset={() => game.reset()}
      />
    </div>
  {/if}
{/if}

<style>
  /* ---- Global reset (scoped here so it doesn't require a global file) ---- */
  :global(*, *::before, *::after) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    font-family: var(--font-stack);
    font-size: var(--font-size-base);
    line-height: var(--line-height);
    background: var(--color-bg-app);
    color: var(--color-text);
    min-height: 100vh;
  }

  /* ---- Start view ---- */
  .start-view {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: var(--space-5);
  }

  .start-card {
    background: var(--color-bg-panel-alt);
    border: var(--border-width) solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-7) var(--space-6);
    text-align: center;
    max-width: 440px;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-4);
    box-shadow: var(--shadow-panel);
  }

  .game-title {
    font-size: var(--font-size-2xl);
    font-weight: 700;
    color: var(--color-text);
    margin: 0;
  }

  .game-subtitle {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    margin: 0;
  }

  .start-btn {
    background: var(--color-bg-panel-alt);
    border: var(--border-width) solid var(--color-accent);
    border-radius: var(--radius);
    color: var(--color-accent);
    cursor: pointer;
    font-family: var(--font-stack);
    font-size: var(--font-size-base);
    font-weight: 600;
    min-height: var(--touch-target-pref);
    padding: 0 var(--space-6);
    margin-top: var(--space-2);
    transition: background 0.1s, color 0.1s;
  }

  .start-btn:hover:not(:disabled),
  .start-btn:focus-visible {
    background: var(--color-bg-panel);
    color: var(--color-accent-hover);
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }

  .start-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .case-hint {
    font-size: var(--font-size-sm);
    color: var(--color-text-dim);
    margin: 0;
  }

  /* ---- Dashboard layout ---- */
  .dashboard {
    display: grid;
    grid-template-rows: auto auto 1fr auto;
    grid-template-areas:
      "header"
      "vitals"
      "body"
      "actions";
    min-height: 100vh;
    gap: var(--space-4);
    padding: var(--space-4);
    background: var(--color-bg-app);
  }

  .dashboard-header  { grid-area: header; }
  .dashboard-vitals  { grid-area: vitals; }
  .dashboard-body    { grid-area: body; }
  .dashboard-actions { grid-area: actions; display: flex; flex-direction: column; gap: var(--space-2); }

  .dashboard-body {
    display: grid;
    grid-template-columns: 1fr 2fr 1fr;
    gap: var(--space-4);
    min-height: 0;   /* allow children to scroll independently */
  }

  @media (max-width: 1100px) {
    .dashboard-body {
      grid-template-columns: 1fr;
    }
  }

  /* ---- Outcome overlay ---- */
  .outcome-overlay {
    position: fixed;
    inset: 0;
    background: var(--color-overlay-bg);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 200;
    padding: var(--space-5);
  }

  /* ---- Shared ---- */
  .error-banner {
    background: var(--color-error-bg);
    border: var(--border-width) solid var(--color-error-border);
    border-radius: var(--radius-sm);
    color: var(--color-state-critical);
    font-size: var(--font-size-sm);
    padding: var(--space-2) var(--space-3);
  }

  /* .inline-error — no additional style needed; inherits from .error-banner */
</style>
