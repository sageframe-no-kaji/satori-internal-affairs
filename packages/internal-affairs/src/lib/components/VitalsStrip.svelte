<!--
  VitalsStrip — horizontal strip of all five vital signs.

  Replaces VitalsPanel (vertical card layout). Each vital is a labelled
  cell with value, unit, and colour-state indicator drawn from token
  --color-state-* values. No motion — colour is the only signal.

  Thresholds match compute_patient_condition heuristics:
    critical → O2 < 88, HR > 150 or < 40, systolic < 90, temp > 104 or < 95
    warning  → moderate deviation from normal
    normal   → everything else

  Universal Design:
  - 18px base font
  - Colour contrasts meet WCAG AA against --color-bg-panel
  - No hover-only behaviours
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

<div class="vitals-strip" role="region" aria-label="Vital signs">
  <!-- Vitals cells -->
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

  <div class="vital vital-{tempStatus(vitals.temperature)}">
    <span class="vital-label">Temp</span>
    <span class="vital-value">{vitals.temperature?.toFixed(1) ?? '—'}</span>
    <span class="vital-unit">&deg;F</span>
  </div>

  <div class="vital vital-{rrStatus(vitals.respiratory_rate)}">
    <span class="vital-label">RR</span>
    <span class="vital-value">{vitals.respiratory_rate ?? '—'}</span>
    <span class="vital-unit">/min</span>
  </div>

  <div class="vital vital-{o2Status(vitals.o2_saturation)}">
    <span class="vital-label">SpO&sub2;</span>
    <span class="vital-value">{vitals.o2_saturation ?? '—'}</span>
    <span class="vital-unit">%</span>
  </div>

  <!-- Condition badge + clock, right-aligned -->
  <div class="strip-meta">
    <span class="condition-badge {conditionClass[condition]}">{conditionLabel[condition]}</span>
    <span class="clock">T+{elapsed_minutes}&nbsp;min</span>
  </div>
</div>

<style>
  .vitals-strip {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    background: var(--color-bg-panel);
    border: var(--border-width) solid var(--color-border);
    border-radius: var(--radius);
    padding: var(--space-3) var(--space-4);
    flex-wrap: wrap;
  }

  .vital {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-sm);
    background: var(--color-bg-app);
    min-width: 80px;
  }

  .vital-label {
    font-size: var(--font-size-sm);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    line-height: 1.2;
  }

  .vital-value {
    font-size: var(--font-size-lg);
    font-weight: 700;
    line-height: 1.2;
  }

  .vital-unit {
    font-size: var(--font-size-sm);
    color: var(--color-text-dim);
    line-height: 1.2;
  }

  /* State colours */
  .vital-normal .vital-label { color: var(--color-text-muted); }
  .vital-normal .vital-value { color: var(--color-state-normal); }

  .vital-warn .vital-label   { color: var(--color-state-warning); }
  .vital-warn .vital-value   { color: var(--color-state-warning); }

  .vital-critical .vital-label { color: var(--color-state-critical); }
  .vital-critical .vital-value { color: var(--color-state-critical); }

  /* Strip meta (condition + clock) */
  .strip-meta {
    margin-left: auto;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: var(--space-1);
  }

  .clock {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    font-variant-numeric: tabular-nums;
  }

  /* Condition badge */
  .condition-badge {
    font-size: var(--font-size-sm);
    font-weight: 600;
    padding: 2px var(--space-3);
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .badge-stable       { background: var(--color-badge-bg-normal);    color: var(--color-state-normal); }
  .badge-compensating { background: var(--color-badge-bg-warning);   color: var(--color-state-warning); }
  .badge-decompensating { background: var(--color-badge-bg-decomp);  color: var(--color-state-warning); }
  .badge-critical     { background: var(--color-badge-bg-critical);  color: var(--color-state-critical); }
  .badge-dead         { background: var(--color-badge-bg-dead);      color: var(--color-text-muted); }
  .badge-recovered    { background: var(--color-badge-bg-recovered); color: var(--color-state-info); }
</style>
