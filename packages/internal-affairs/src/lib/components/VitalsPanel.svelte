<!--
  VitalsPanel — displays current vital signs with colour-coded status
  and a patient condition badge.

  Thresholds match compute_patient_condition heuristics:
    CRITICAL → O2 < 88, HR > 150 or < 40, systolic BP < 90, temp > 104 or < 95
    WARN     → moderate deviation from normal
    NORMAL   → everything else
-->
<script lang="ts">
  import type { PatientCondition, VitalSigns } from '$lib/types';

  let {
    vitals,
    condition,
    elapsed_minutes,
  }: {
    vitals: VitalSigns;
    condition: PatientCondition;
    elapsed_minutes: number;
  } = $props();

  type VitalStatus = 'normal' | 'warn' | 'critical';

  function hrStatus(v: number | null): VitalStatus {
    if (v === null) return 'normal';
    if (v > 150 || v < 40) return 'critical';
    if (v > 120 || v < 50) return 'warn';
    return 'normal';
  }

  function bpStatus(systolic: number | null): VitalStatus {
    if (systolic === null) return 'normal';
    if (systolic < 90) return 'critical';
    if (systolic > 180 || systolic < 100) return 'warn';
    return 'normal';
  }

  function tempStatus(v: number | null): VitalStatus {
    if (v === null) return 'normal';
    if (v > 104 || v < 95) return 'critical';
    if (v > 101 || v < 96.5) return 'warn';
    return 'normal';
  }

  function rrStatus(v: number | null): VitalStatus {
    if (v === null) return 'normal';
    if (v > 30 || v < 8) return 'critical';
    if (v > 24 || v < 10) return 'warn';
    return 'normal';
  }

  function o2Status(v: number | null): VitalStatus {
    if (v === null) return 'normal';
    if (v < 88) return 'critical';
    if (v < 94) return 'warn';
    return 'normal';
  }

  const conditionLabel: Record<PatientCondition, string> = {
    stable: 'Stable',
    compensating: 'Compensating',
    decompensating: 'Decompensating',
    critical: 'Critical',
    dead: 'Deceased',
    recovered: 'Recovered',
  };

  const conditionClass: Record<PatientCondition, string> = {
    stable: 'badge-stable',
    compensating: 'badge-compensating',
    decompensating: 'badge-decompensating',
    critical: 'badge-critical',
    dead: 'badge-dead',
    recovered: 'badge-recovered',
  };
</script>

<div class="vitals-panel">
  <div class="panel-header">
    <span class="panel-title">Vitals</span>
    <span class="condition-badge {conditionClass[condition]}">{conditionLabel[condition]}</span>
  </div>

  <div class="vitals-grid">
    <div class="vital vital-{hrStatus(vitals.heart_rate)}">
      <span class="vital-label">HR</span>
      <span class="vital-value">{vitals.heart_rate ?? '—'}</span>
      <span class="vital-unit">bpm</span>
    </div>

    <div class="vital vital-{bpStatus(vitals.blood_pressure_systolic)}">
      <span class="vital-label">BP</span>
      <span class="vital-value">
        {vitals.blood_pressure_systolic ?? '—'}/{vitals.blood_pressure_diastolic ?? '—'}
      </span>
      <span class="vital-unit">mmHg</span>
    </div>

    <div class="vital vital-{o2Status(vitals.o2_saturation)}">
      <span class="vital-label">SpO₂</span>
      <span class="vital-value">{vitals.o2_saturation ?? '—'}</span>
      <span class="vital-unit">%</span>
    </div>

    <div class="vital vital-{tempStatus(vitals.temperature)}">
      <span class="vital-label">Temp</span>
      <span class="vital-value">{vitals.temperature?.toFixed(1) ?? '—'}</span>
      <span class="vital-unit">°F</span>
    </div>

    <div class="vital vital-{rrStatus(vitals.respiratory_rate)}">
      <span class="vital-label">RR</span>
      <span class="vital-value">{vitals.respiratory_rate ?? '—'}</span>
      <span class="vital-unit">/min</span>
    </div>

    <div class="vital vital-normal">
      <span class="vital-label">Time</span>
      <span class="vital-value">{elapsed_minutes}</span>
      <span class="vital-unit">min</span>
    </div>
  </div>
</div>

<style>
  .vitals-panel {
    background: #1e2330;
    border: 1px solid #2e3447;
    border-radius: 6px;
    padding: 12px 14px;
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .panel-title {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #7a89a8;
  }

  /* Condition badge */
  .condition-badge {
    font-size: 0.75rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .badge-stable       { background: #1a3a2a; color: #6fcf97; }
  .badge-compensating { background: #2d3312; color: #f2c94c; }
  .badge-decompensating { background: #3a2810; color: #f2994a; }
  .badge-critical     { background: #3a1010; color: #eb5757; }
  .badge-dead         { background: #282828; color: #828282; }
  .badge-recovered    { background: #0d2d3a; color: #56ccf2; }

  /* Vitals grid */
  .vitals-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }

  .vital {
    display: flex;
    flex-direction: column;
    padding: 6px 8px;
    border-radius: 4px;
    background: #161b27;
  }

  .vital-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .vital-value {
    font-size: 1.1rem;
    font-weight: 600;
    line-height: 1.2;
  }

  .vital-unit {
    font-size: 0.68rem;
    color: #5a6480;
  }

  .vital-normal .vital-label  { color: #7a89a8; }
  .vital-normal .vital-value  { color: #c0c8da; }

  .vital-warn .vital-label    { color: #b09040; }
  .vital-warn .vital-value    { color: #f2c94c; }

  .vital-critical .vital-label { color: #a03030; }
  .vital-critical .vital-value { color: #eb5757; }
</style>
