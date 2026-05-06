export default defineNuxtConfig({
  compatibilityDate: '2026-04-29',
  devtools: { enabled: true },
  css: ['~/assets/css/main.css', '~/assets/css/overrides.css'],
  runtimeConfig: {
    aiApiBase: process.env.AI_API_BASE || 'http://127.0.0.1:8000',
    public: {
      appName: 'MedGuard'
    }
  },
  app: {
    head: {
      title: 'MedGuard',
      meta: [
        { name: 'description', content: 'Agentic AI compliance orchestration for regulated content authorization.' }
      ]
    }
  }
})
