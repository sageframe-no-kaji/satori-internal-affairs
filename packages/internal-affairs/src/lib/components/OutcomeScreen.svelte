<!--
  OutcomeScreen — displayed when case_ended is true.
  Shows the outcome tier, end reason, and a "Play Again" reset button.
-->
<script lang="ts">
  let {
    outcome_tier,
    end_reason,
    outcome_narrative,
    onReset,
  }: {
    outcome_tier: string | null;
    end_reason: string | null;
    outcome_narrative: string | null;
    onReset: () => void;
  } = $props();

  const tierLabel: Record<string, string> = {
    optimal: 'Optimal Outcome',
    good: 'Good Outcome',
    partial: 'Partial Success',
    failure: 'Case Failed',
  };

  const tierClass: Record<string, string> = {
    optimal: 'tier-optimal',
    good: 'tier-good',
    partial: 'tier-partial',
    failure: 'tier-failure',
  };

  let tier = $derived(outcome_tier?.toLowerCase() ?? 'failure');
  let label = $derived(tierLabel[tier] ?? 'Case Ended');
  let cls = $derived(tierClass[tier] ?? 'tier-failure');
</script>

<div class="outcome-screen">
  <div class="outcome-card {cls}">
    <div class="tier-label">{label}</div>

    {#if outcome_narrative}
      <div class="outcome-narrative">{outcome_narrative}</div>
    {:else if end_reason}
      <div class="end-reason">{end_reason}</div>
    {/if}

    <button class="reset-btn" onclick={onReset}>
      Play Again
    </button>
  </div>
</div>

<style>
  /* Tokenized in P2-H11 — this component predated the token rule. Tier
     colors map onto the state tokens; tier borders use the light tints. */
  .outcome-screen {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--space-7) var(--space-5);
  }

  .outcome-card {
    background: var(--color-bg-panel);
    border-radius: var(--radius-lg);
    border: 2px solid var(--color-border);
    padding: var(--space-7) var(--space-7);
    text-align: center;
    max-width: 480px;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-4);
    box-shadow: var(--shadow-panel);
  }

  .tier-label {
    font-size: var(--font-size-xl);
    font-weight: 700;
    letter-spacing: 0.02em;
  }

  .end-reason {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: var(--line-height);
    max-width: 360px;
  }

  .outcome-narrative {
    font-size: var(--font-size-base);
    color: var(--color-text);
    line-height: var(--line-height);
    max-width: 380px;
    text-align: left;
  }

  .reset-btn {
    margin-top: var(--space-2);
    background: var(--color-bg-panel);
    border: var(--border-width) solid var(--color-accent);
    border-radius: var(--radius);
    color: var(--color-accent);
    cursor: pointer;
    font-family: var(--font-stack);
    font-size: var(--font-size-base);
    font-weight: 600;
    /* Sole control at case end — must meet the ataxia touch floor (audit UD-1) */
    min-height: var(--touch-target-pref);
    padding: var(--space-2) var(--space-6);
    transition: background 0.1s, color 0.1s;
  }

  .reset-btn:hover {
    background: var(--color-bg-panel-alt);
    color: var(--color-accent-hover);
  }

  .reset-btn:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }

  /* Tier colour overrides */
  .tier-optimal .tier-label  { color: var(--color-state-normal); }
  .tier-good .tier-label     { color: var(--color-state-info); }
  .tier-partial .tier-label  { color: var(--color-state-warning); }
  .tier-failure .tier-label  { color: var(--color-state-critical); }

  .tier-optimal  { border-color: var(--color-tint-normal); }
  .tier-good     { border-color: var(--color-tint-info); }
  .tier-partial  { border-color: var(--color-tint-warning); }
  .tier-failure  { border-color: var(--color-tint-critical); }
</style>
