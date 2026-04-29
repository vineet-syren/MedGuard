<template>
  <main class="page">
    <SiteHeader />
    <section class="site-hero">
      <div><p class="eyebrow">Buy Now</p><h1 class="site-title">Choose Access</h1></div>
      <p class="site-copy">Pricing cards are scrollable and intentionally stark: type first, utility next, no distracting palette.</p>
    </section>
    <OptionRail :items="items" />
  </main>
</template>

<script setup lang="ts">
const items = [
  { number: '$9k', title: 'Content Desk', copy: 'One brand team, content lab, DAM basics, review prompts, and analytics preview.', to: '/console' },
  { number: '$24k', title: 'Launch Suite', copy: 'Cross-functional campaign operations with MLR, medical, localisation, DAM, and analytics.', to: '/console' },
  { number: 'Custom', title: 'Global Ops', copy: 'Tenant policy, super-admin governance, audit, market configuration, and enterprise onboarding.', to: '/reach-out' }
]
</script>

