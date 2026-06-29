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
  .patient-header {
    background: #1e2330;
    border: 1px solid #2e3447;
    border-radius: 6px;
    padding: 14px 18px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .patient-identity {
    display: flex;
    align-items: baseline;
    gap: 12px;
  }

  .patient-name {
    font-size: 1.15rem;
    font-weight: 600;
    color: #e8ecf4;
  }

  .patient-meta {
    font-size: 0.85rem;
    color: #7a89a8;
  }

  .chief-complaint,
  .appearance,
  .triage-note {
    font-size: 0.9rem;
    color: #c0c8da;
    line-height: 1.5;
  }

  .label {
    font-weight: 600;
    color: #8a96b4;
    margin-right: 6px;
  }
</style>
