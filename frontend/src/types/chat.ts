export interface CollaborationStep {
  role: string        // 晴/焕/机/遥/玄
  action: string      // 操作描述
  result: string      // 结果摘要
  next?: string[] | null  // 决策传递给谁
}

export interface ChatMessage {
  id?: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
  created_at?: string
  toolExecution?: ToolExecution
  /** Emotion snapshot from 焕 */
  emotionSnapshot?: EmotionSnapshot
  /** AI collaboration steps */
  collaboration?: CollaborationStep[]
}

export interface ToolExecution {
  tool: string
  success: boolean
  result: string
}

export interface EmotionSnapshot {
  primary_emotion: string
  emotion_intensity: string
  deep_need: string
  risk_level: string
}

export interface AgentEvent {
  type:
    | 'thinking'
    | 'message'
    | 'error'
    | 'done'
    | 'emotion_update'
    | 'metadata'
    | 'collaboration'
  content: string
  /** Collaboration steps from done event */
  collaboration?: CollaborationStep[]
}
