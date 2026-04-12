import { request } from './client'
import type { UserSetting, SettingUpdate, TokenUsageSummary } from '@/types/setting'

export function getSettings() {
  return request<UserSetting | null>('/v1/settings/')
}

export function updateSettings(data: SettingUpdate) {
  return request<UserSetting>('/v1/settings/', {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function getTokenUsage() {
  return request<TokenUsageSummary>('/v1/settings/token-usage')
}
