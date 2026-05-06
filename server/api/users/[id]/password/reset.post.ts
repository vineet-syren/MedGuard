import { proxy } from '../../../../utils/proxy'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  const body = await readBody(event)
  return await proxy(`/api/users/${id}/password/reset`, {
    method: 'POST',
    body
  })
})
