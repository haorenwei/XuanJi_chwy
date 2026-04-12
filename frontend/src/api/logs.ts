import { request } from './client'
import type { LogListResponse, LogStatsResponse } from '@/types/log'

export async function getLogs(params?: {
  limit?: number
  offset?: number
  level?: string
  source?: string
}) {
  const query = new URLSearchParams()
  if (params?.limit) query.set('limit', String(params.limit))
  if (params?.offset !== undefined) query.set('offset', String(params.offset))
  if (params?.level) query.set('level', params.level)
  if (params?.source) query.set('source', params.source)
  return request<LogListResponse>(`/v1/logs/?${query}`)
}

export async function getLogStats() {
  return request<LogStatsResponse>('/v1/logs/stats')
}
