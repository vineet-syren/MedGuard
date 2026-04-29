<template>
  <main class="page">
    <SiteHeader />
    <section class="site-hero">
      <div><p class="eyebrow">Solutions</p><h1 class="site-title">Launch Systems</h1></div>
      <p class="site-copy">Each solution is a complete operating path: plan the work, create the asset, prepare review, localise safely, and measure the outcome.</p>
    </section>
    <OptionRail :items="items" />
  </main>
</template>

<script setup lang="ts">
const items = [
  { number: '01', title: 'Campaign Command', copy: 'Turn a brief into channel-specific HCP assets with modular content, owner tracking, and readiness scoring.', to: '/console' },
  { number: '02', title: 'Evidence-To-Claim', copy: 'Connect claims to evidence plans, narrative structure, references, and medical review watchpoints.', to: '/console?module=evidence' },
  { number: '03', title: 'MLR Rework Cutdown', copy: 'Catch preventable review issues before submission and give writers precise revision guidance.', to: '/console?module=compliance' },
  { number: '04', title: 'Global-To-Local', copy: 'Adapt master assets for India, UK, US, and Saudi Arabia with regulatory and cultural context intact.', to: '/console?module=localization' }
]
</script>

