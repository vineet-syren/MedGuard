export function apiBase() {
  const config = useRuntimeConfig()
  const base = String(config.aiApiBase || '').trim()
  if (!base) {
    throw createError({
      statusCode: 503,
      statusMessage: 'MedGuard backend is not configured',
      message: 'Set NUXT_AI_API_BASE in Vercel to the deployed FastAPI backend URL.'
    })
  }
  return base.replace(/\/$/, '')
}

export async function proxy<T>(path: string, options: any = {}) {
  const target = `${apiBase()}${path}`
  try {
    return await $fetch<T>(target, options)
  } catch (error: any) {
    if (error?.statusCode && error.statusCode < 500) {
      throw error
    }
    throw createError({
      statusCode: error?.statusCode || 502,
      statusMessage: 'MedGuard backend request failed',
      message: `Could not reach the configured FastAPI backend at ${apiBase()}. Check NUXT_AI_API_BASE and the backend deployment.`
    })
  }
}
