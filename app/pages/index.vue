<template>
  <main class="page">
    <SiteHeader />

    <section class="hero">
      <div class="hero-main">
        <div>
          <p class="eyebrow">AI content creation platform</p>
          <h1 class="hero-title">Launch compliant content without the chaos.</h1>
          <p class="hero-copy">
            Proofline is a commercial AI workspace for regulated teams to plan, create,
            govern, review, localise, and measure promotional and medical content.
          </p>
          <div class="hero-actions">
            <NuxtLink class="btn inverse" to="/console">Open console</NuxtLink>
            <NuxtLink class="btn ghost" to="/buy-now">View plans</NuxtLink>
            <NuxtLink class="btn ghost" to="/offerings">Explore product</NuxtLink>
          </div>
        </div>

        <div class="kpi-grid">
          <div class="kpi"><span class="eyebrow">MLR cycle target</span><strong>7.8d</strong></div>
          <div class="kpi"><span class="eyebrow">Content reuse</span><strong>68%</strong></div>
          <div class="kpi"><span class="eyebrow">First-pass checks</span><strong>94%</strong></div>
          <div class="kpi"><span class="eyebrow">Assets governed</span><strong>2.8k</strong></div>
        </div>
      </div>

      <div class="hero-visual">
        <div class="window">
          <p class="eyebrow">Live pipeline</p>
          <h2>Q2 respiratory launch</h2>
          <div class="window-row"><span class="dot" /><span>Content Lab assembled 14 modules</span><strong>Ready</strong></div>
          <div class="window-row"><span class="dot" /><span>Evidence links validated for 9 claims</span><strong>92%</strong></div>
          <div class="window-row"><span class="dot" /><span>MLR pre-screen flagged 3 edits</span><strong>Review</strong></div>
          <div class="window-row"><span class="dot" /><span>India localisation in progress</span><strong>03 May</strong></div>
        </div>
      </div>
    </section>

    <MarqueeStrip text="modular content · DAM governance · medical narratives · evidence synthesis · email QA · MLR pre-screening · localisation · analytics" />

    <section class="band">
      <div class="intro">
        <div>
          <p class="eyebrow">Product preview</p>
          <h2 class="section-title">A campaign room, evidence desk, review desk, and launch console.</h2>
        </div>
        <p class="muted">
          Scroll the product screenshots. These placeholders describe what the full console is doing
          without relying on decorative stock imagery.
        </p>
      </div>
      <div class="screenshot-rail">
        <article class="screenshot-card">
          <MockScreen title="Offering / Content Lab" index="01" primary="Module Library" primary-detail="Claims, safety, references, CTA blocks" metric-label="MLR readiness" metric="86%" detail="Reusable campaign canvas for HCP email, eDA, congress, and leave-behind assets." />
          <div><p class="eyebrow">Screenshot placeholder</p><h3>Offerings are shown as production surfaces.</h3></div>
        </article>
        <article class="screenshot-card">
          <MockScreen title="Solution / Review readiness" index="02" primary="3 risks found" primary-detail="Fair balance, substantiation, missing reference" metric-label="Owner" metric="Compliance" detail="Risk-aware review preparation with owner assignment and next actions." />
          <div><p class="eyebrow">Screenshot placeholder</p><h3>Solutions explain the workflow outcome.</h3></div>
        </article>
        <article class="screenshot-card">
          <MockScreen title="Industry / Affiliate launch" index="03" primary="India adaptation" primary-detail="In progress" metric-label="UK pack" metric="Ready" detail="Market-specific notes, cultural adaptation, and approved master content lineage." />
          <div><p class="eyebrow">Screenshot placeholder</p><h3>Industry pages show use-case depth.</h3></div>
        </article>
      </div>
    </section>

    <section class="band">
      <div class="intro">
        <div>
          <p class="eyebrow">Customers</p>
          <h2 class="section-title">Teams use it to make review feel less brittle.</h2>
        </div>
        <p class="muted">Illustrative testimonials from realistic content operations, medical affairs, and compliance buyer personas.</p>
      </div>
      <div class="split">
        <div class="panel-dark">
          <h2>“We finally see where content slows down before the review meeting starts.”</h2>
          <p>Maya Rao · Director, Content Operations</p>
        </div>
        <div class="panel-light">
          <h2>“The evidence prompts save our writers from starting with an empty page.”</h2>
          <p>Dr. Elena Voss · Medical Affairs Lead</p>
        </div>
      </div>
    </section>

    <section class="demo-panel">
      <div class="panel-dark">
        <div>
          <p class="eyebrow">Book a demo</p>
          <h2 class="section-title">See the product with your launch data.</h2>
          <p>Use this homepage section for demo conversion. The full reach-out page gives a deeper enterprise contact flow.</p>
        </div>
        <NuxtLink class="btn inverse" to="/reach-out">Open reach-out page</NuxtLink>
      </div>
      <form class="form" @submit.prevent="demoStatus = 'Demo request captured locally for this prototype.'">
        <label>Work email</label>
        <input type="email" value="work.email@example.com">
        <label>Team type</label>
        <select>
          <option>Brand / Marketing</option>
          <option>Medical Affairs</option>
          <option>MLR / Compliance</option>
          <option>Regional Affiliate</option>
          <option>Enterprise Content Ops</option>
        </select>
        <label>What should the demo show?</label>
        <textarea rows="4">Show a Q2 HCP campaign moving from brief to MLR-ready content and localisation.</textarea>
        <button class="btn" type="submit">Book demo</button>
        <p class="muted">{{ demoStatus }}</p>
      </form>
    </section>
  </main>
</template>

<script setup lang="ts">
const demoStatus = ref('')
</script>

