import { proxy } from '../../../../utils/proxy'

export default defineEventHandler(async (event) => {
  const provider = getRouterParam(event, 'provider')
  return await proxy(`/api/auth/sso/${provider}/start`, {
    method: 'GET',
    query: getQuery(event)
  })
})
