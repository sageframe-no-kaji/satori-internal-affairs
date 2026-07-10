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
  - Cards are non-interactive; category headers are windowshade toggles
    (practitioner request, P2-H11) — full-width targets at the 60px floor,
    keyboard-operable, with the finding count always visible so a collapsed
    section never hides that new evidence arrived
  - Flag chips carry text — no information by color alone
  - Stable category regions: the player knows where to look when new
    evidence arrives, and re-finding a fact is spatial, not a search

  Props:
    findings — server-composed findings from the game state, chronological
-->
<script lang="ts">
  import { tick } from 'svelte';
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

  // Windowshade state (practitioner request, P2-H11): each category header
  // toggles its section closed/open. Default open; collapsed headers keep
  // the finding count visible so arriving evidence is never silent.
  let collapsed = $state<Record<string, boolean>>({});

  function toggleSection(key: string) {
    collapsed[key] = !collapsed[key];
  }

  // Fresh-evidence highlight (practitioner request, P2-H11): findings that
  // arrived on the latest turn tint their section header and card light
  // green. When they land, sections WITHOUT fresh evidence roll their
  // shades up and the fresh section opens and scrolls to the top of the
  // pane — new evidence is never buried, section order never changes, and
  // everything else is one tap away with its count still showing.
  // Self-clearing — the next turn's findings replace the set. Visual
  // attention only: keyboard focus stays wherever the player left it
  // (moving it mid-flow would cost an ataxia player their place in the
  // action bar).
  let panelBody = $state<HTMLDivElement | null>(null);
  let freshIds = $state<Set<string>>(new Set());
  let prevIds = new Set<string>();

  $effect(() => {
    const current = new Set(findings.map((f) => f.node_id));
    const fresh = new Set([...current].filter((id) => !prevIds.has(id)));
    prevIds = current;
    freshIds = fresh;
    if (fresh.size > 0) {
      const next: Record<string, boolean> = {};
      for (const section of sections) {
        next[section.key] = !section.items.some((f) => fresh.has(f.node_id));
      }
      collapsed = next;
      void tick().then(() => {
        panelBody?.querySelector('.is-fresh')?.scrollIntoView({ block: 'start' });
      });
    }
  });

  function sectionFresh(section: Section): boolean {
    return section.items.some((f) => freshIds.has(f.node_id));
  }

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

  <div class="panel-body" bind:this={panelBody}>
    {#if findings.length === 0}
      <p class="empty-state">No findings yet.</p>
    {:else}
      {#each sections as section (section.key)}
        <div class="category-section">
          <h3 class="category-header">
            <button
              class="category-toggle"
              class:is-fresh={sectionFresh(section)}
              type="button"
              aria-expanded={!collapsed[section.key]}
              onclick={() => toggleSection(section.key)}
            >
              <span>{section.label} ({section.items.length})</span>
              <span class="toggle-arrow" aria-hidden="true">{collapsed[section.key] ? '▸' : '▾'}</span>
            </button>
          </h3>
          {#if !collapsed[section.key]}
            {#each section.items as finding (finding.node_id)}
              <article class="finding-card" class:is-fresh={freshIds.has(finding.node_id)}>
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
    padding: var(--space-3);
    display: flex;
    flex-direction: column;
    /* Tight, but the gap between adjacent interactive headers stays at the
       16px touch-gap floor (gap + separator padding below). */
    gap: var(--space-2);
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
    gap: var(--space-2);
  }

  .category-section + .category-section {
    border-top: var(--border-width) solid var(--color-border);
    padding-top: var(--space-2);
  }

  .category-header {
    margin: 0;
  }

  /* Windowshade toggle — a full-width interactive header at the ataxia
     touch floor; the whole row is the target. */
  .category-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    min-height: var(--touch-target-min);
    padding: 0 var(--space-2);
    background: transparent;
    border: none;
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-family: var(--font-stack);
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    transition: background 0.1s;
  }

  .category-toggle:hover,
  .category-toggle:focus-visible {
    background: var(--color-bg-panel-alt);
    color: var(--color-text);
    outline: 2px solid var(--color-accent);
    outline-offset: -2px;
  }

  /* Fresh evidence: light green marks where the latest turn's findings
     landed — header and card both, count always visible. */
  .category-toggle.is-fresh {
    background: var(--color-fresh-bg);
    color: var(--color-fresh-text);
  }

  .category-toggle.is-fresh .toggle-arrow {
    color: var(--color-fresh-text);
  }

  .finding-card.is-fresh {
    background: var(--color-fresh-bg);
    border-color: var(--color-state-normal);
  }

  /* The windowshade affordance — oversized on purpose (ataxia: the state
     of the shade must read at a glance, from arm's length). */
  .toggle-arrow {
    color: var(--color-text-muted);
    font-size: var(--font-size-xl);
    line-height: 1;
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
    background: var(--color-chip-bg);
    border-radius: var(--radius-sm);
    color: var(--color-chip-text);
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
