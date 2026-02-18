<!--
  Root page — the entire Ho 05 game UI lives here.

  Three views:
    start   → Load Case button
    play    → Patient header + vitals + action menu + event log
    outcome → Outcome screen with tier + reset

  All state is driven by the game store (gameStore.svelte.ts).
  This page never calls the API directly.
-->
<script lang="ts">
  import PatientHeader from '$lib/components/PatientHeader.svelte';
  import VitalsPanel from '$lib/components/VitalsPanel.svelte';
  import ActionMenu from '$lib/components/ActionMenu.svelte';
  import EventLog from '$lib/components/EventLog.svelte';
  import OutcomeScreen from '$lib/components/OutcomeScreen.svelte';
  import { game, DEFAULT_CASE_PATH } from '$lib/stores/gameStore.svelte';
</script>

<div class="app-shell">
  <!-- ------------------------------------------------------------------ -->
  <!-- Start view                                                           -->
  <!-- ------------------------------------------------------------------ -->
  {#if game.view === 'start'}
    <div class="start-view">
      <div class="start-card">
        <h1 class="game-title">Internal Affairs</h1>
        <p class="game-subtitle">Medical Mystery Simulator — Phase 1</p>

        {#if game.error}
          <div class="error-banner">{game.error}</div>
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
  <!-- Play view                                                            -->
  <!-- ------------------------------------------------------------------ -->
  {:else if game.view === 'play' && game.gameState && game.patient}
    <div class="play-view">
      <!-- Top bar: patient identity -->
      <header class="play-header">
        <PatientHeader patient={game.patient} />
      </header>

      <!-- Main content area -->
      <div class="play-body">
        <!-- Left sidebar: vitals + actions -->
        <aside class="left-sidebar">
          <VitalsPanel
            vitals={game.gameState.current_vitals}
            condition={game.patientCondition}
            elapsed_minutes={game.gameState.current_time_minutes}
          />

          <ActionMenu
            actions={game.availableActions}
            loading={game.isLoading}
            onAction={(action) => game.performAction(action)}
          />
        </aside>

        <!-- Main: event log -->
        <main class="event-log-area">
          {#if game.error}
            <div class="error-banner">{game.error}</div>
          {/if}

          {#if game.isLoading}
            <div class="loading-indicator">Processing…</div>
          {/if}

          <EventLog entries={game.eventLog} />
        </main>
      </div>
    </div>

  <!-- ------------------------------------------------------------------ -->
  <!-- Outcome view                                                         -->
  <!-- ------------------------------------------------------------------ -->
  {:else if game.view === 'outcome' && game.gameState}
    <OutcomeScreen
      outcome_tier={game.gameState.outcome_tier}
      end_reason={game.gameState.end_reason}
      onReset={() => game.reset()}
    />
  {/if}
</div>

<style>
  /* Reset + base */
  :global(*, *::before, *::after) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f1420;
    color: #c0c8da;
    min-height: 100vh;
  }

  .app-shell {
    min-height: 100vh;
  }

  /* ---- Start view ---- */
  .start-view {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 24px;
  }

  .start-card {
    background: #1e2330;
    border: 1px solid #2e3447;
    border-radius: 10px;
    padding: 48px 52px;
    text-align: center;
    max-width: 440px;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
  }

  .game-title {
    font-size: 2rem;
    font-weight: 700;
    color: #e8ecf4;
    margin: 0;
  }

  .game-subtitle {
    font-size: 0.9rem;
    color: #7a89a8;
    margin: 0;
  }

  .start-btn {
    background: #2d4a7a;
    border: 1px solid #3d5e9a;
    border-radius: 6px;
    color: #c8d8f8;
    cursor: pointer;
    font-size: 1rem;
    font-weight: 600;
    padding: 12px 36px;
    margin-top: 8px;
    transition: background 0.1s;
  }

  .start-btn:hover:not(:disabled) {
    background: #3860a0;
  }

  .start-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .case-hint {
    font-size: 0.78rem;
    color: #4a5470;
    margin: 0;
  }

  /* ---- Play view ---- */
  .play-view {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    padding: 12px;
    gap: 12px;
  }

  .play-header {
    width: 100%;
  }

  .play-body {
    display: flex;
    gap: 12px;
    flex: 1;
    align-items: flex-start;
  }

  .left-sidebar {
    display: flex;
    flex-direction: column;
    gap: 10px;
    width: 240px;
    flex-shrink: 0;
  }

  .event-log-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }

  /* ---- Shared ---- */
  .error-banner {
    background: #3a1010;
    border: 1px solid #5a1a1a;
    border-radius: 5px;
    color: #eb9090;
    font-size: 0.88rem;
    padding: 8px 12px;
  }

  .loading-indicator {
    font-size: 0.85rem;
    color: #7a89a8;
    padding: 4px 0;
    font-style: italic;
  }
</style>
