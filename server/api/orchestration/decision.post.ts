import { proxy } from '../../utils/proxy'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  return await proxy('/api/orchestration/decision', { method: 'POST', body })
})
