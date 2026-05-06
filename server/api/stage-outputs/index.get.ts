import { proxy } from '../../utils/proxy'

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  return await proxy('/api/stage-outputs', { query })
})
