import { proxy } from '../../utils/proxy'

export default defineEventHandler(async () => {
  return await proxy('/api/rule-engine/stages')
})
