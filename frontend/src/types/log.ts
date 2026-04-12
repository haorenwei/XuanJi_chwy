export interface LogEntry {
  id: number
  task_id: number | null
  tool_id: number | null
  user_id: number | null
  level: string // "info" | "warn" | "error" | "debug"
  message: string
  details: Record<string, any> | null
  source: string | null
  status_code: number | null
  created_at: string
}

export interface LogListResponse {
  items: LogEntry[]
  total: number
  limit: number
  offset: number
}

export interface LogStatsResponse {
  stats: Record<string, number> // {"info": 10, "warn": 3, "error": 1}
}
