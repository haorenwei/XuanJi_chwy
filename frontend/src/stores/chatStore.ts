import { create } from 'zustand'
import type { ChatMessage, AgentEvent, EmotionSnapshot } from '@/types/chat'
import { sendMessage, getRecentMessages } from '@/api/chat'
import { getSettings } from '@/api/settings'

interface ChatState {
  messages: ChatMessage[]
  isStreaming: boolean
  isGenerating: boolean
  agentStatus: string
  currentEmotion: EmotionSnapshot | null
  abortController: AbortController | null
  showCollaboration: boolean
  currentConversationId: number | null
  currentStreamId: string | null
  addMessage: (msg: ChatMessage) => void
  clearMessages: () => void
  sendUserMessage: (content: string) => Promise<void>
  cancelStream: () => void
  setShowCollaboration: (value: boolean) => void
  loadShowCollaboration: () => Promise<void>
  loadConversation: () => Promise<void>
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isStreaming: false,
  isGenerating: false,
  agentStatus: '',
  currentEmotion: null,
  abortController: null,
  showCollaboration: true,
  currentConversationId: null,
  currentStreamId: null,

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  clearMessages: () => set({ messages: [] }),

  setShowCollaboration: (value) => set({ showCollaboration: value }),

  loadShowCollaboration: async () => {
    try {
      const res = await getSettings()
      if (res.data) {
        const val = res.data.show_collaboration
        set({ showCollaboration: val != null ? val : true })
      }
    } catch {
      // keep default
    }
  },

  loadConversation: async () => {
    try {
      // 如果当前正在流式传输，跳过重新加载，保留流式状态和 placeholder 消息
      if (get().isStreaming) {
        console.log('[chatStore] loadConversation skipped: streaming in progress')
        return
      }
      console.log('[chatStore] loadConversation called')
      const recentRes = await getRecentMessages(3)
      // 后端直接返回数组，不包装在 ApiResponse 中
      const messages = Array.isArray(recentRes) ? recentRes : (recentRes as any)?.data
      console.log('[chatStore] getRecentMessages returned:', messages?.length, 'messages')
      if (!messages || messages.length === 0) {
        console.log('[chatStore] No messages found')
        return
      }

      const chatMessages: ChatMessage[] = messages.map((m: any) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
        timestamp: m.created_at,
        created_at: m.created_at,
        // 解析 metadata_json 中的 toolExecution 信息（如果有）
        ...(m.metadata_json ? (() => {
          try {
            const meta = JSON.parse(m.metadata_json)
            const extras: Partial<ChatMessage> = {}
            if (meta.type === 'task_result' && meta.tool_name) {
              extras.toolExecution = {
                tool: meta.tool_name,
                success: meta.success ?? true,
                result: '',
              }
            }
            if (meta.collaboration) {
              extras.collaboration = meta.collaboration
            }
            return extras
          } catch {}
          return {}
        })() : {}),
      }))

      // 使用最后一条消息的 conversation_id
      const lastMsg = messages[messages.length - 1]
      const convId = lastMsg.conversation_id ?? null

      set({ messages: chatMessages, currentConversationId: convId })
      console.log('[chatStore] Loaded', chatMessages.length, 'messages, conversationId:', convId)
    } catch (err) {
      console.error('[chatStore] loadConversation failed:', err)
    }
  },

  cancelStream: () => {
    const { abortController } = get()
    if (abortController) {
      abortController.abort()
    }
    set({ isStreaming: false, isGenerating: false, agentStatus: '', abortController: null })
  },

  sendUserMessage: async (content) => {
    const userMsg: ChatMessage = {
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
      created_at: new Date().toISOString(),
    }

    const abortController = new AbortController()
    const streamId = `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

    set((s) => ({
      messages: [...s.messages, userMsg],
      isStreaming: true,
      agentStatus: '',
      abortController,
    }))

    // Add placeholder for assistant response
    const assistantMsg: ChatMessage = {
      role: 'assistant',
      content: '',
      id: streamId,
    }
    set((s) => ({ messages: [...s.messages, assistantMsg], currentStreamId: streamId }))

    const allMessages = [...get().messages.slice(0, -1)]

    try {
      await sendMessage(
        allMessages.map((m) => ({ role: m.role, content: m.content })),
        (event: Record<string, unknown>) => {
          const e = event as unknown as AgentEvent

          // conversation_id 校验：防止切换对话时旧 SSE 响应串话
          const eventConvId = (e as any).conversation_id
          if (eventConvId !== undefined) {
            const currentId = get().currentConversationId
            if (currentId && currentId !== eventConvId) {
              console.warn('[chatStore] 事件被忽略! conversation_id 不匹配:', eventConvId, '!==', currentId, '事件类型:', e.type)
              return
            }
            if (!currentId) {
              // 新对话，更新 ID
              set({ currentConversationId: eventConvId })
            }
          }

          if (e.type === 'metadata') {
            // metadata 事件仅用于传递 conversation_id，已在上方处理
            return
          }

          if (e.type === 'message') {
            set((s) => {
              const msgs = [...s.messages]
              const sid = s.currentStreamId

              // 优先按 ID 查找目标消息
              let targetIdx = -1
              if (sid) {
                targetIdx = msgs.findIndex((m) => m.id === sid)
              }
              // fallback：倒序查找最后一条 assistant 消息
              if (targetIdx === -1) {
                for (let i = msgs.length - 1; i >= 0; i--) {
                  if (msgs[i].role === 'assistant') { targetIdx = i; break }
                }
              }

              if (targetIdx >= 0) {
                const target = msgs[targetIdx]
                const now = new Date().toISOString()
                msgs[targetIdx] = {
                  ...target,
                  content: (target.content || '') + (e.content || ''),
                  ...(!target.created_at ? { timestamp: now, created_at: now } : {}),
                }
              }
              // 收到第一个 message 文本块时才标记为正在生成，此前为 AI 协作阶段
              return { messages: msgs, agentStatus: '', isGenerating: true }
            })
          } else if (e.type === 'thinking') {
            set({ agentStatus: e.content })
          } else if (e.type === 'emotion_update') {
            try {
              const emotionData = JSON.parse(e.content) as EmotionSnapshot
              // Attach to the latest user message and update current emotion
              set((s) => {
                const msgs = [...s.messages]
                for (let i = msgs.length - 1; i >= 0; i--) {
                  if (msgs[i].role === 'user' && !msgs[i].emotionSnapshot) {
                    msgs[i] = { ...msgs[i], emotionSnapshot: emotionData }
                    break
                  }
                }
                return { messages: msgs, currentEmotion: emotionData }
              })
            } catch {
              // skip
            }
          } else if (e.type === 'collaboration') {
            // 协作日志异步处理，不阻塞用户交互
            const collabData = (e as any).collaboration
            if (collabData) {
              const applyCollab = () => {
                set((s) => {
                  const msgs = [...s.messages]
                  const sid = s.currentStreamId
                  let targetIdx = -1
                  if (sid) {
                    targetIdx = msgs.findIndex((m) => m.id === sid)
                  }
                  if (targetIdx === -1) {
                    for (let i = msgs.length - 1; i >= 0; i--) {
                      if (msgs[i].role === 'assistant') { targetIdx = i; break }
                    }
                  }
                  if (targetIdx >= 0) {
                    msgs[targetIdx] = { ...msgs[targetIdx], collaboration: collabData }
                  }
                  return { messages: msgs }
                })
              }
              if (typeof requestIdleCallback !== 'undefined') {
                requestIdleCallback(applyCollab)
              } else {
                setTimeout(applyCollab, 0)
              }
            }
          } else if (e.type === 'done') {
            console.log('[chatStore] done 事件到达, 当前 isStreaming:', get().isStreaming, 'conversation_id 匹配:', (e as any).conversation_id, '===', get().currentConversationId)
            set({ isStreaming: false, isGenerating: false, agentStatus: '' })
            console.log('[chatStore] done 事件处理完毕, isStreaming 已设为:', get().isStreaming)
          } else if (e.type === 'error') {
            set((s) => {
              const msgs = [...s.messages]
              const last = msgs[msgs.length - 1]
              if (last && last.role === 'assistant') {
                msgs[msgs.length - 1] = { ...last, content: last.content + `\n\n错误：${e.content}` }
              }
              return { messages: msgs, isStreaming: false, isGenerating: false, agentStatus: '' }
            })
          }
        },
        undefined,
        abortController.signal,
        get().currentConversationId,
      )
    } catch (err) {
      // 用户主动取消时不显示错误信息
      if (err instanceof DOMException && err.name === 'AbortError') {
        return
      }
      set((s) => {
        const msgs = [...s.messages]
        const last = msgs[msgs.length - 1]
        if (last && last.role === 'assistant') {
          msgs[msgs.length - 1] = { ...last, content: '连接出错，请检查网络后重试' }
        }
        return { messages: msgs, isStreaming: false, isGenerating: false, agentStatus: '' }
      })
    } finally {
      // 安全网：流结束后强制恢复状态，防止 done 事件丢失导致 UI 卡死
      console.log('[chatStore] sendUserMessage finally 块执行, 当前 isStreaming:', get().isStreaming)
      set({
        isStreaming: false,
        isGenerating: false,
        agentStatus: '',
        abortController: null,
        currentStreamId: null,
      })
    }
  },
}))
