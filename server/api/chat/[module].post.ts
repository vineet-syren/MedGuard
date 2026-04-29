import { proxy } from '../../utils/proxy'

export default defineEventHandler(async (event) => {
  const module = getRouterParam(event, 'module')
  const body = await readBody(event)
  const response = await proxy<string>(`/api/chat/${module}`, {
    method: 'POST',
    body,
    responseType: 'text'
  })

  const chunks = String(response)
    .split('\n')
    .filter(line => line.startsWith('data: '))
    .map(line => line.slice(6))
    .filter(line => line && line !== '[DONE]')

  const text = chunks.map((line) => {
    try {
      return JSON.parse(line).text || ''
    } catch {
      return ''
    }
  }).join('')

  return { text }
})

