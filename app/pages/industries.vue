<template>
  <main class="page">
    <SiteHeader />
    <section class="site-hero">
      <div><p class="eyebrow">Industries</p><h1 class="site-title">Regulated Teams</h1></div>
      <p class="site-copy">The same black-and-white operating model flexes across pharma, vaccines, medtech, diagnostics, consumer health, and affiliate organisations.</p>
    </section>
    <OptionRail :items="items" />
  </main>
</template>

<script setup lang="ts">
const items = [
  { number: 'Rx', title: 'Pharma', copy: 'Promotional HCP campaigns, MLR preparation, claim lineage, safety balance, and modular reuse.' },
  { number: 'Vx', title: 'Vaccines', copy: 'Education platforms, congress decks, phase-data summaries, audience segmentation, and local launch packs.' },
  { number: 'Dx', title: 'Diagnostics', copy: 'Testing pathways, evidence-based education, biomarker journeys, and clinical proof communication.' },
  { number: 'Md', title: 'MedTech', copy: 'Device education, indication-safe messaging, workflow content, product training, and proof points.' },
  { number: 'Af', title: 'Affiliates', copy: 'Local review packs, market adaptation, translation context, approval ownership, and go-live tracking.' }
]
</script>

