<template>
  <main class="console-grid">
    <aside class="console-sidebar">
      <NuxtLink class="wordmark" to="/">
        <span class="wordmark-symbol">P/L</span>
        <span class="wordmark-text">Proofline</span>
      </NuxtLink>
      <p class="muted">AI content operations console</p>
      <nav class="nav-links" style="justify-self:start; flex-direction:column; align-items:stretch; margin-top:24px">
        <button v-for="item in modules" :key="item.id" class="nav-link" :class="{ btn: activeModule === item.id }" @click="activeModule = item.id">
          {{ item.label }}
        </button>
      </nav>
    </aside>

    <section class="console-main">
      <div class="console-card">
        <p class="eyebrow">Console</p>
        <h1 class="section-title">Agentic content workspace</h1>
        <p class="muted">
          Nuxt owns the product shell and BFF routes. FastAPI + Pydantic owns AI orchestration,
          schemas, RAG, MCP tools, and multi-agent workflows.
        </p>
      </div>

      <div class="console-card" v-if="health">
        <p class="eyebrow">Backend health</p>
        <pre>{{ health }}</pre>
      </div>

      <div class="split">
        <section class="chat-card">
          <p class="eyebrow">Assistant</p>
          <h2>{{ currentLabel }}</h2>
          <div class="chat-log">
            <div v-for="(message, index) in messages" :key="index" class="chat-message" :class="message.role">
              {{ message.content }}
            </div>
          </div>
          <form class="form" style="padding:0; margin-top:14px" @submit.prevent="send">
            <textarea v-model="draft" rows="4" placeholder="Ask the selected assistant..."></textarea>
            <button class="btn" :disabled="loading" type="submit">{{ loading ? 'Sending...' : 'Send' }}</button>
          </form>
        </section>

        <section class="chat-card">
          <p class="eyebrow">Agentic plan</p>
          <button class="btn" @click="createPlan">Generate plan</button>
          <pre v-if="agentPlan">{{ agentPlan }}</pre>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
type ChatMessage = { role: 'user' | 'assistant'; content: string }

const route = useRoute()
const modules = [
  { id: 'admin', label: 'Ops Orchestrator' },
  { id: 'content-lab', label: 'Content Lab' },
  { id: 'dam', label: 'DAM' },
  { id: 'scp', label: 'Sci Comm' },
  { id: 'evidence', label: 'Evidence' },
  { id: 'email-qa', label: 'Email QA' },
  { id: 'compliance', label: 'Compliance' },
  { id: 'localization', label: 'Localisation' },
  { id: 'analytics', label: 'Analytics' },
  { id: 'media', label: 'Visual Concept Studio' }
]

const activeModule = ref(String(route.query.module || 'admin'))
const currentLabel = computed(() => modules.find(item => item.id === activeModule.value)?.label || 'Assistant')
const draft = ref('Review the current pipeline and list the top risks, owners, and next actions.')
const loading = ref(false)
const messages = ref<ChatMessage[]>([
  { role: 'assistant', content: 'Select a module and ask a question. Responses are routed through Nuxt server APIs to FastAPI.' }
])

const { data: health } = await useFetch('/api/health')
const agentPlan = ref(null)

async function send() {
  const message = draft.value.trim()
  if (!message) return
  messages.value.push({ role: 'user', content: message })
  draft.value = ''
  loading.value = true
  try {
    const result = await $fetch<{ text: string }>(`/api/chat/${activeModule.value}`, {
      method: 'POST',
      body: { message, module: activeModule.value, history: messages.value.slice(-8) }
    })
    messages.value.push({ role: 'assistant', content: result.text })
  } catch (error: any) {
    messages.value.push({ role: 'assistant', content: error?.message || 'Request failed.' })
  } finally {
    loading.value = false
  }
}

async function createPlan() {
  agentPlan.value = await $fetch('/api/agents/plan', {
    method: 'POST',
    body: {
      objective: 'Prepare AsterResp COPD campaign for MLR-ready launch',
      market: 'India',
      modules: ['content-lab', 'dam', 'evidence', 'compliance', 'localization']
    }
  })
}
</script>

