<template>
  <main class="page">
    <SiteHeader />
    <section class="site-hero">
      <div><p class="eyebrow">Offerings</p><h1 class="site-title">Product Surfaces</h1></div>
      <p class="site-copy">A scrollable set of workspaces for regulated content creation, review preparation, evidence handling, localisation, and performance intelligence.</p>
    </section>
    <OptionRail :items="items" />
  </main>
</template>

<script setup lang="ts">
const items = [
  { number: '01', title: 'Content Lab', copy: 'Modular assembly, channel briefs, approved claims, safety blocks, CTAs, and campaign handoff.', to: '/console?module=content-lab' },
  { number: '02', title: 'DAM Governance', copy: 'Metadata, lifecycle, usage rights, expiry control, duplicate detection, and searchable asset records.', to: '/console?module=dam' },
  { number: '03', title: 'Medical Narrative', copy: 'SCP and IMCP planning with evidence-aware narrative support and reference placeholders.', to: '/console?module=scp' },
  { number: '04', title: 'Evidence Desk', copy: 'PICO plans, literature screening, extraction tables, evidence grading, and study gap detection.', to: '/console?module=evidence' },
  { number: '05', title: 'MLR Pre-Screen', copy: 'Fair balance, substantiation, reference, safety, superlative, and market watchout checks before formal review.', to: '/console?module=compliance' },
  { number: '06', title: 'Analytics', copy: 'Cycle time, reuse, engagement, approval quality, cost-to-produce, and launch readiness intelligence.', to: '/console?module=analytics' }
]
</script>

