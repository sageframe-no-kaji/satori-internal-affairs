<!--
  ActiveConcernsPanel — the evidence board (P2-H03).

  Every revealed clinical finding accumulates here as a bordered card,
  grouped under category section headers (visual decision 1: bordered cards
  with per-category sections). Findings arrive server-composed and
  chronological; this component only groups and renders — the frontend never
  decides what counts as evidence (Truth Line).

  Card anatomy: label, authored finding text, flag chips from structured
  data (the skim-reading layer), and the T+N min reveal timestamp.

  Universal Design:
  - 18px body text, AA contrast on card backgrounds
  - Cards are non-interactive; the panel scrolls, nothing collapses or hides
  - Flag chips carry text — no information by color alone
  - Stable category regions: the player knows where to look when new
    evidence arrives, and re-finding a fact is spatial, not a search

  Props:
    findings — server-composed findings from the game state, chronological
-->
<script lang="ts">
  import type { Finding } from '$lib/types';

  let { findings }: { findings: Finding[] } = $props();

  /** Display sections in fixed order; unknown categories fall through to Other. */
  const CATEGORY_SECTIONS: Array<{ key: string; label: string }> = [
    { key: 'history', label: 'History' },
    { key: 'medical_finding', label: 'Exam' },
    { key: 'lab_result', label: 'Labs' },
    { key: 'imaging', label: 'Imaging' },
    { key: 'relational', label: 'Family' },
    { key: 'emotional', label: 'Emotional' },
  ];

  interface Section {
    key: string;
    label: string;
    items: Finding[];
  }

  function buildSections(list: Finding[]): Section[] {
    const known = new Set(CATEGORY_SECTIONS.map((s) => s.key));
    const sections: Section[] = CATEGORY_SECTIONS.map((s) => ({
      ...s,
      items: list.filter((f) => f.category === s.key),
    }));
    sections.push({
      key: 'other',
      label: 'Other',
      items: list.filter((f) => !known.has(f.category)),
    });
    return sections.filter((s) => s.items.length > 0);
  }

  let sections = $derived(buildSections(findings));

  /** Convert a snake_case key to Title Case. */
  function humanise(key: string): string {
    return key
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  }

  /** Flag chips: structured_data entries whose key ends in "_flag". */
  function flagChips(finding: Finding): string[] {
    return Object.entries(finding.structured_data ?? {})
      .filter(([key]) => key.endsWith('_flag'))
      .map(([key, value]) => `${humanise(key.slice(0, -'_flag'.length))}: ${String(value)}`);
  }
</script>

<section class="panel active-concerns-panel" aria-label="Active Concerns">
  <header class="panel-header">
    <h2 class="panel-title">Active Concerns</h2>
  </header>

  <div class="panel-body">
    {#if findings.length === 0}
      <p class="empty-state">No findings yet.</p>
    {:else}
      {#each sections as section (section.key)}
        <div class="category-section">
          <h3 class="category-header">{section.label}</h3>
          {#each section.items as finding (finding.node_id)}
            <article class="finding-card">
              <h4 class="finding-label">{finding.label}</h4>
              <p class="finding-text">{finding.narrative_text}</p>
              {#if flagChips(finding).length > 0}
                <div class="finding-chips">
                  {#each flagChips(finding) as chip}
                    <span class="finding-chip">{chip}</span>
                  {/each}
                </div>
              {/if}
              <span class="finding-time">T+{finding.revealed_at_minutes}&nbsp;min</span>
            </article>
          {/each}
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
    gap: var(--space-5);
  }

  .empty-state {
    font-size: var(--font-size-base);
    color: var(--color-text-dim);
    font-style: italic;
    margin: 0;
    line-height: var(--line-height);
  }

  .category-section {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .category-section + .category-section {
    border-top: var(--border-width) solid var(--color-border);
    padding-top: var(--space-4);
  }

  .category-header {
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 0;
  }

  .finding-card {
    background: var(--color-bg-panel-alt);
    border: var(--border-width) solid var(--color-border);
    border-radius: var(--radius);
    padding: var(--space-3) var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .finding-label {
    font-size: var(--font-size-base);
    font-weight: 600;
    color: var(--color-text);
    margin: 0;
  }

  .finding-text {
    font-size: var(--font-size-base);
    color: var(--color-text-muted);
    line-height: var(--line-height);
    margin: 0;
  }

  .finding-chips {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }

  .finding-chip {
    background: var(--color-badge-bg-warning);
    border-radius: var(--radius-sm);
    color: var(--color-state-warning);
    font-size: var(--font-size-sm);
    font-weight: 600;
    padding: var(--space-1) var(--space-2);
  }

  .finding-time {
    font-size: var(--font-size-sm);
    color: var(--color-text-dim);
    font-variant-numeric: tabular-nums;
  }
</style>
