<!--
  NarrativeFeedPanel — the primary reading surface.

  Replaces EventLog. Renders the event log entries in reverse-chronological
  order (newest at top) with generous typography suited to reading at arm's
  length.

  Universal Design:
  - 18px base font, 1.55 line-height (from tokens)
  - Sufficient contrast: narration text on --color-bg-panel background
  - No hover-only behaviours
  - Panel is a scrollable region with ARIA landmark
-->
<script lang="ts">
  import type { EventLogEntry } from '$lib/types';

  let { events }: { events: EventLogEntry[] } = $props();

  /** Convert an action key to a readable label. */
  function humanise(action: string): string {
    const [base, param] = action.split(':', 2);
    const baseLabel = base
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
    if (param) {
      const paramLabel = param
        .split('_')
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
      return `${baseLabel}: ${paramLabel}`;
    }
    return baseLabel;
  }

  /** Format simulated minutes as a readable clock string. */
  function formatTime(minutes: number): string {
    if (minutes < 60) return `${minutes} min`;
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return m > 0 ? `${h}h ${m}min` : `${h}h`;
  }

  /** Filter out background engine events that are not narratable. */
  function isSignificant(type: string): boolean {
    const background = new Set(['flag_set', 'flag_cleared', 'action_unlocked', 'action_locked']);
    return !background.has(type);
  }

  /**
   * Resolve the display text for an event. For Waited events the server
   * narration bridge does not yet produce a player-facing string (P2-H08
   * will bring a real narrator). Render directly from event data instead.
   *
   * For all other event types, fall through to the server-supplied narration.
   */
  function narrateEvent(event: import('$lib/types').GameEvent, serverNarration: string): string {
    if (event.type === 'waited') {
      const dur = event.data['duration_minutes'];
      return typeof dur === 'number' ? `${dur} minutes pass.` : 'Time passes.';
    }
    return serverNarration;
  }
</script>

<section class="panel narrative-feed-panel" aria-label="Narrative Feed">
  <header class="panel-header">
    <h2 class="panel-title">Narrative</h2>
  </header>

  <div class="panel-body">
    {#if events.length === 0}
      <p class="empty-state">No actions taken yet.</p>
    {:else}
      {#each events as entry}
        <div class="log-entry" class:log-entry-emergency={entry.emergency}>
          <div class="entry-header">
            <span class="action-label">{humanise(entry.action)}</span>
            <span class="entry-time">{formatTime(entry.timestamp_minutes)}</span>
          </div>

          {#each entry.events as event, i}
            {#if isSignificant(event.type)}
              <p class="narration-text">{narrateEvent(event, entry.narrations[i])}</p>
            {/if}
          {/each}

          <!-- Raw event data for debugging — opt-in via VITE_DEBUG_EVENTS=1
               (P2-H11: debug chrome stays out of the player surface, even
               in dev, unless explicitly asked for) -->
          {#if import.meta.env.VITE_DEBUG_EVENTS}
            <details class="raw-events">
              <summary>Raw events ({entry.events.length})</summary>
              <pre>{JSON.stringify(entry.events, null, 2)}</pre>
            </details>
          {/if}
        </div>
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
    position: sticky;
    top: 0;
    background: var(--color-bg-panel);
    z-index: 1;
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
    gap: var(--space-4);
  }

  .empty-state {
    font-size: var(--font-size-base);
    color: var(--color-text-dim);
    font-style: italic;
    margin: 0;
    line-height: var(--line-height);
  }

  .log-entry {
    border-left: 2px solid var(--color-border-strong);
    padding-left: var(--space-3);
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  /* Emergency entries (P2-H05): turns taken while a crisis was in progress
     read in the crisis register — including the turn the crisis began. */
  .log-entry-emergency {
    border-left-color: var(--color-state-critical);
    background: var(--color-emergency-entry-bg);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    padding: var(--space-2) var(--space-3);
  }

  .log-entry-emergency .action-label {
    color: var(--color-emergency-label);
  }

  .log-entry-emergency .narration-text {
    color: var(--color-text);
  }

  .entry-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--space-3);
  }

  .action-label {
    font-size: var(--font-size-base);
    font-weight: 600;
    color: var(--color-accent);
  }

  .entry-time {
    font-size: var(--font-size-sm);
    color: var(--color-text-dim);
    flex-shrink: 0;
    font-variant-numeric: tabular-nums;
  }

  .narration-text {
    font-size: var(--font-size-base);
    color: var(--color-text-muted);
    line-height: var(--line-height);
    margin: 0;
  }

  .raw-events {
    margin-top: var(--space-1);
  }

  .raw-events summary {
    font-size: var(--font-size-sm);
    color: var(--color-text-dim);
    cursor: pointer;
    user-select: none;
  }

  .raw-events pre {
    font-size: var(--font-size-sm);
    color: var(--color-text-dim);
    margin-top: var(--space-1);
    white-space: pre-wrap;
    word-break: break-all;
    background: var(--color-bg-app);
    border-radius: var(--radius-sm);
    padding: var(--space-2) var(--space-3);
  }
</style>
