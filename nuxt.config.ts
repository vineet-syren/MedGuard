export default defineNuxtConfig({
  compatibilityDate: '2026-04-29',
  devtools: { enabled: true },
  modules: ['@vercel/analytics'],
  css: ['~/assets/css/main.css', '~/assets/css/overrides.css'],
  runtimeConfig: {
    aiApiBase: process.env.NUXT_AI_API_BASE || process.env.AI_API_BASE || (process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000'),
    public: {
      appName: 'MedGuard'
    }
  },
  app: {
    baseURL: process.env.NUXT_APP_BASE_URL || '/',
    head: {
      title: 'MedGuard',
      meta: [
        { name: 'description', content: 'Agentic AI compliance orchestration for regulated content authorization.' }
      ]
    }
  }
})
