import { proxy } from '../../../utils/proxy'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  const query = getQuery(event)
  return await proxy(`/api/connections/${id}`, { method: 'DELETE', query })
})
