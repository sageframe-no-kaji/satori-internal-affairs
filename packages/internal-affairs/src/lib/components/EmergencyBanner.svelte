<!--
  EmergencyBanner — the emergency state signature (P2-H05, visual decision 1).

  Top-anchored crimson banner rendered while state.emergency_active is true.
  Carries the crisis label (server-supplied via emergency_timer.label — the
  frontend never names the crisis itself) and the countdown in exact minutes,
  large and centered: the player is racing this clock.

  Universal Design:
  - role="alert" announces the crisis to assistive tech the moment it renders
  - Countdown at --font-size-2xl, tabular numerals, AA contrast on crimson
  - Slide-down entry is suppressed under prefers-reduced-motion
  - Non-interactive: the banner demands attention but the action stays in the
    action bar, which never moves (visual decision 2 pairing)

  Props:
    label             — crisis name from the emergency timer channel
    remaining_minutes — exact minutes left on the active crisis clock
-->
<script lang="ts">
  let {
    label,
    remaining_minutes,
  }: {
    label: string;
    remaining_minutes: number;
  } = $props();
</script>

<div class="emergency-banner" role="alert">
  <span class="emergency-label">{label} — Intervene</span>
  <span class="emergency-countdown" aria-label="{remaining_minutes} minutes remaining">
    {remaining_minutes}&nbsp;min
  </span>
</div>

<style>
  .emergency-banner {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-6);
    flex-wrap: wrap;
    background: var(--color-emergency-bg);
    border: var(--border-width) solid var(--color-state-critical);
    border-radius: var(--radius);
    padding: var(--space-3) var(--space-5);
    animation: banner-enter 0.2s ease-out;
  }

  .emergency-label {
    font-size: var(--font-size-xl);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--color-emergency-text);
  }

  .emergency-countdown {
    font-size: var(--font-size-2xl);
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: var(--color-emergency-text);
    white-space: nowrap;
  }

  @keyframes banner-enter {
    from {
      transform: translateY(-100%);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .emergency-banner {
      animation: none;
    }
  }
</style>
