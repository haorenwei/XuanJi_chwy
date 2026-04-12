// 版本记录
export interface ToolVersion {
  id: number
  tool_id: number
  version: number
  code?: string
  description?: string
  description_zh?: string
  change_summary?: string
  created_at: string
}

export interface Tool {
  id: number
  name: string
  description: string
  description_zh?: string
  code: string
  language: string
  version: number
  tool_type?: string
  is_builtin: boolean
  created_by: number | null
  created_at: string
  updated_at: string
}

export interface ToolBrief {
  id: number
  name: string
  description: string
  description_zh?: string
  language: string
  version: number
  tool_type?: string
  is_builtin: boolean
  sub_tool_count?: number
  created_at: string
}

export interface ToolCreate {
  name: string
  description: string
  description_zh?: string
  code: string
  language: string
}

export interface ToolUpdate {
  name?: string
  description?: string
  description_zh?: string
  code?: string
  language?: string
}

export interface ToolImportResult {
  created: number
  updated: number
  skipped: number
}

export interface ToolExportItem {
  name: string
  description: string
  description_zh?: string
  code: string
  language: string
  version: number
}
