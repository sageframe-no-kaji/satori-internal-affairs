<!--
  EventLog — chronological feed of turns, newest first.

  Each entry shows the narration text for each event. Raw event data is
  available in a <details> block for debugging.
-->
<script lang="ts">
  import type { EventLogEntry } from '$lib/types';

  let { entries }: { entries: EventLogEntry[] } = $props();

  /** Convert an action key to a readable label (same as ActionMenu). */
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

  /** Format simulated minutes as a readable clock string (e.g. "1h 20min"). */
  function formatTime(minutes: number): string {
    if (minutes < 60) return `${minutes} min`;
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return m > 0 ? `${h}h ${m}min` : `${h}h`;
  }

  /** Classify an event type string as displayable or internal. */
  function isSignificant(type: string): boolean {
    const background = new Set(['flag_set', 'flag_cleared', 'action_unlocked', 'action_locked']);
    return !background.has(type);
  }
</script>

<div class="event-log">
  <div class="log-header">Turn log</div>

  {#if entries.length === 0}
    <p class="empty-log">No actions taken yet.</p>
  {:else}
    {#each entries as entry}
      <div class="log-entry">
        <div class="entry-header">
          <span class="action-label">{humanise(entry.action)}</span>
          <span class="entry-time">{formatTime(entry.timestamp_minutes)}</span>
        </div>

        <!-- Show narration for significant events -->
        {#each entry.events as event, i}
          {#if isSignificant(event.type)}
            <div class="narration-line">
              <span class="event-dot"></span>
              <span class="narration-text">{entry.narrations[i]}</span>
            </div>
          {/if}
        {/each}

        <!-- Raw event data for debugging -->
        <details class="raw-events">
          <summary>Raw events ({entry.events.length})</summary>
          <pre>{JSON.stringify(entry.events, null, 2)}</pre>
        </details>
      </div>
    {/each}
  {/if}
</div>

<style>
  .event-log {
    background: #161b27;
    border: 1px solid #2e3447;
    border-radius: 6px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    overflow-y: auto;
    max-height: 60vh;
  }

  .log-header {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #7a89a8;
    margin-bottom: 2px;
    position: sticky;
    top: 0;
    background: #161b27;
    padding-bottom: 6px;
    border-bottom: 1px solid #252d3e;
  }

  .empty-log {
    font-size: 0.85rem;
    color: #4a5470;
    font-style: italic;
    margin: 0;
  }

  .log-entry {
    border-left: 2px solid #2e3a52;
    padding-left: 10px;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .entry-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
  }

  .action-label {
    font-size: 0.88rem;
    font-weight: 600;
    color: #8fa8e8;
  }

  .entry-time {
    font-size: 0.75rem;
    color: #5a6480;
    flex-shrink: 0;
  }

  .narration-line {
    display: flex;
    align-items: flex-start;
    gap: 7px;
  }

  .event-dot {
    display: inline-block;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #4a5470;
    margin-top: 7px;
    flex-shrink: 0;
  }

  .narration-text {
    font-size: 0.87rem;
    color: #a0aac0;
    line-height: 1.55;
  }

  .raw-events {
    margin-top: 4px;
  }

  .raw-events summary {
    font-size: 0.72rem;
    color: #4a5470;
    cursor: pointer;
    user-select: none;
  }

  .raw-events pre {
    font-size: 0.7rem;
    color: #5a6480;
    margin-top: 4px;
    white-space: pre-wrap;
    word-break: break-all;
    background: #101420;
    border-radius: 4px;
    padding: 6px 8px;
  }
</style>
