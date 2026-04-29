import { proxy } from '../../utils/proxy'

export default defineEventHandler(async (event) => {
  const module = getRouterParam(event, 'module')
  return await proxy(`/api/quick-prompts/${module}`)
})

