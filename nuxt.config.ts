export default defineNuxtConfig({
  compatibilityDate: '2026-04-29',
  devtools: { enabled: true },
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    aiApiBase: process.env.AI_API_BASE || 'http://127.0.0.1:8000',
    public: {
      appName: 'Proofline'
    }
  },
  app: {
    head: {
      title: 'Proofline',
      meta: [
        { name: 'description', content: 'Proofline is an AI content operating system for regulated content teams.' }
      ]
    }
  }
})

