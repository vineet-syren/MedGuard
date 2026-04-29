export function apiBase() {
  const config = useRuntimeConfig()
  return config.aiApiBase.replace(/\/$/, '')
}

export async function proxy<T>(path: string, options: any = {}) {
  return await $fetch<T>(`${apiBase()}${path}`, options)
}
