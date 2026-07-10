<!--
  PatientHeader — displays patient identity and chief complaint.
  Always visible during the play view.
-->
<script lang="ts">
  import type { PatientContext } from '$lib/types';

  let { patient }: { patient: PatientContext } = $props();
</script>

<div class="patient-header">
  <div class="patient-identity">
    <span class="patient-name">{patient.name}</span>
    <span class="patient-meta">{patient.age} y/o {patient.sex} — {patient.setting}</span>
  </div>
  <div class="chief-complaint">
    <span class="label">Chief complaint:</span>
    <span>{patient.chief_complaint}</span>
  </div>
  <div class="appearance">
    <span class="label">Appearance:</span>
    <span>{patient.appearance}</span>
  </div>
  {#if patient.triage_note}
    <div class="triage-note">
      <span class="label">Triage note:</span>
      <span>{patient.triage_note}</span>
    </div>
  {/if}
</div>

<style>
  /* Tokenized in P2-H11 — this component predated the token rule. */
  .patient-header {
    background: var(--color-bg-panel);
    border: var(--border-width) solid var(--color-border);
    border-radius: var(--radius);
    padding: var(--space-3) var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    box-shadow: var(--shadow-panel);
  }

  .patient-identity {
    display: flex;
    align-items: baseline;
    gap: var(--space-3);
  }

  .patient-name {
    font-size: var(--font-size-lg);
    font-weight: 700;
    color: var(--color-text);
  }

  .patient-meta {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
  }

  .chief-complaint,
  .appearance,
  .triage-note {
    font-size: var(--font-size-sm);
    color: var(--color-text);
    line-height: var(--line-height);
  }

  .label {
    font-weight: 600;
    color: var(--color-text-muted);
    margin-right: var(--space-1);
  }
</style>
