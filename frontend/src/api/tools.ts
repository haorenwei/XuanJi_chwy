import type { Tool, ToolBrief, ToolCreate, ToolUpdate, ToolImportResult, ToolExportItem, ToolVersion } from '@/types/tool'
import { request } from './client'

export async function listTools() {
  return request<ToolBrief[]>(`/v1/tools/`)
}

export async function getTool(id: number) {
  return request<Tool>(`/v1/tools/${id}`)
}

export async function searchTools(q: string) {
  return request<ToolBrief[]>(`/v1/tools/search?q=${encodeURIComponent(q)}`)
}

export async function deleteTool(id: number) {
  return request<null>(`/v1/tools/${id}`, { method: 'DELETE' })
}

export async function createTool(data: ToolCreate) {
  return request<Tool>('/v1/tools/', { method: 'POST', body: JSON.stringify(data) })
}

export async function updateTool(id: number, data: ToolUpdate) {
  return request<Tool>(`/v1/tools/${id}`, { method: 'PUT', body: JSON.stringify(data) })
}

export async function exportTools() {
  return request<ToolExportItem[]>('/v1/tools/export')
}

export async function importTools(items: ToolCreate[]) {
  return request<ToolImportResult>('/v1/tools/import', { method: 'POST', body: JSON.stringify(items) })
}

export async function getToolVersions(toolId: number) {
  return request<ToolVersion[]>(`/v1/tools/${toolId}/versions`)
}

export async function rollbackToolVersion(toolId: number, version: number) {
  return request<Tool>(`/v1/tools/${toolId}/rollback/${version}`, { method: 'POST' })
}
