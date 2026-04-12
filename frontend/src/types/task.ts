export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface Task {
  id: number
  user_id: number
  title: string
  description: string | null
  status: TaskStatus
  result: string | null
  created_at: string
  updated_at: string
}
