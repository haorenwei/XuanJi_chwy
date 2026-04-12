import type { ChatMessage } from '@/types/chat'
import { request, streamRequest } from './client'

/** 获取用户的会话列表 */
export async function getConversations() {
  return request<Array<{ id: number; title: string | null; created_at: string; updated_at: string }>>('/v1/conversations/')
}

/** 获取指定会话的消息列表 */
export async function getConversationMessages(conversationId: number) {
  return request<Array<{
    id: number
    role: string
    content: string
    metadata_json: string | null
    created_at: string
  }>>(`/v1/conversations/${conversationId}/messages`)
}

/** 获取最近 N 天的消息 */
export async function getRecentMessages(days: number = 3) {
  return request<Array<{
    id: number
    conversation_id: number
    user_id: number
    role: string
    content: string
    metadata_json: string | null
    emotion_snapshot: string | null
    is_summarized: boolean
    created_at: string
  }>>(`/v1/conversations/recent-messages?days=${days}`)
}

export async function sendMessage(
  messages: ChatMessage[],
  onEvent: (event: Record<string, unknown>) => void,
  workingDir?: string,
  signal?: AbortSignal,
  conversationId?: number | null,
) {
  await streamRequest(
    '/v1/chat/',
    { messages, stream: true, working_dir: workingDir, conversation_id: conversationId ?? undefined },
    onEvent,
    signal,
  )
}
