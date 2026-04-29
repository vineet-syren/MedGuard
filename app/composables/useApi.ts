export function useApi() {
  const request = async <T>(path: string, options: any = {}) => {
    return await $fetch<T>(path, options)
  }

  return { request }
}
