import { request } from './client'

// Dashboard Token 概览
interface DashboardTokenOverview {
  today_tokens: number
  month_tokens: number
  total_tokens: number
  monthly_budget: number | null
}

export async function getDashboardStats() {
  return request<DashboardTokenOverview>('/v1/stats/dashboard')
}

// Token by role
export interface TokenByRoleItem {
  role_name: string
  model: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  call_count: number
}

export async function getTokenByRole(days: number = 30) {
  return request<TokenByRoleItem[]>(`/v1/stats/token-by-role?days=${days}`)
}

// Token daily trend
export interface TokenDailyItem {
  date: string
  role_name: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

export async function getTokenDaily(days: number = 30) {
  return request<TokenDailyItem[]>(`/v1/stats/token-daily?days=${days}`)
}

// Token by model
export interface TokenByModelItem {
  model: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  call_count: number
}

export async function getTokenByModel(days: number = 30) {
  return request<TokenByModelItem[]>(`/v1/stats/token-by-model?days=${days}`)
}
