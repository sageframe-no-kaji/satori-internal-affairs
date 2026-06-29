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
  .outcome-screen {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
  }

  .outcome-card {
    background: #1e2330;
    border-radius: 10px;
    border: 2px solid #2e3447;
    padding: 36px 40px;
    text-align: center;
    max-width: 480px;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
  }

  .tier-label {
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: 0.02em;
  }

  .end-reason {
    font-size: 0.95rem;
    color: #8a96b4;
    line-height: 1.6;
    max-width: 360px;
  }

  .outcome-narrative {
    font-size: 0.95rem;
    color: #b0bcd8;
    line-height: 1.7;
    max-width: 380px;
    text-align: left;
  }

  .reset-btn {
    margin-top: 8px;
    background: #2e3a52;
    border: 1px solid #3e4f72;
    border-radius: 6px;
    color: #c0cce8;
    cursor: pointer;
    font-size: 0.95rem;
    font-weight: 600;
    padding: 10px 28px;
    transition: background 0.1s;
  }

  .reset-btn:hover {
    background: #364460;
  }

  /* Tier colour overrides */
  .tier-optimal .tier-label  { color: #6fcf97; }
  .tier-good .tier-label     { color: #56ccf2; }
  .tier-partial .tier-label  { color: #f2c94c; }
  .tier-failure .tier-label  { color: #eb5757; }

  .tier-optimal  { border-color: #1a4a30; }
  .tier-good     { border-color: #0d3040; }
  .tier-partial  { border-color: #3a3010; }
  .tier-failure  { border-color: #3a1010; }
</style>
