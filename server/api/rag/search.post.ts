import { proxy } from '../../utils/proxy'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  return await proxy('/api/rag/search', { method: 'POST', body })
})

