<template>
  <main class="page">
    <SiteHeader />
    <section class="site-hero">
      <div><p class="eyebrow">Reach out</p><h1 class="site-title">Book The Room</h1></div>
      <p class="site-copy">A direct contact page for sales, pilots, stakeholder walkthroughs, and enterprise configuration conversations.</p>
    </section>
    <section class="split">
      <form class="form panel-light" @submit.prevent="status = 'Demo request captured locally for this prototype.'">
        <div><p class="eyebrow">Contact form</p><h2 class="section-title">Tell us what launch flow to show.</h2></div>
        <label>Work email</label>
        <input type="email" value="work.email@example.com">
        <label>Market scope</label>
        <select>
          <option>Single brand pilot</option>
          <option>Multi-market launch</option>
          <option>Medical affairs workflow</option>
          <option>Enterprise content operations</option>
        </select>
        <label>Message</label>
        <textarea rows="5">We want to evaluate Proofline for a regulated HCP launch.</textarea>
        <button class="btn" type="submit">Send request</button>
        <p class="muted">{{ status }}</p>
      </form>
      <div class="panel-dark">
        <div><p class="eyebrow">Next steps</p><h2 class="section-title">Map. Configure. Pilot.</h2></div>
        <div>
          <p><strong>01</strong> Map current campaign and approval bottlenecks.</p>
          <p><strong>02</strong> Configure personas, markets, model routing, and policy packs.</p>
          <p><strong>03</strong> Run a pilot campaign through the console with realistic data.</p>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
const status = ref('')
</script>
