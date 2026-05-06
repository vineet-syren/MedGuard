import { proxy } from '../../../utils/proxy'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  return await proxy(`/api/input-bundles/${id}`)
})
