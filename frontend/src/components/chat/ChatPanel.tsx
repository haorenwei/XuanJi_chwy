import React, { useEffect, useRef } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { MessageBubble } from './MessageBubble'
import { ChatInput } from './ChatInput'
import { StreamingIndicator } from './StreamingIndicator'
import { formatDateHeader, isSameDay } from '@/utils/formatDate'

export function ChatPanel() {
  const { messages, isStreaming, agentStatus, sendUserMessage, cancelStream } = useChatStore()
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, agentStatus])

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-auto p-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-4 text-5xl">🌸</div>
            <h2 className="text-xl font-semibold text-ink">欢迎使用璇玑</h2>
            <p className="mt-2 max-w-md text-sm text-ink-light">
              我可以帮你执行任务、生成工具和管理文件。输入消息开始对话。
            </p>
          </div>
        )}

        {messages.map((msg, i) => {
          const msgDate = msg.created_at || msg.timestamp
          // 只在两条都有有效 created_at 的消息间比较日期，placeholder 消息不触发分隔符
          const prevDate = i > 0 ? (messages[i - 1].created_at || messages[i - 1].timestamp) : null
          const showDateSeparator = i === 0
            ? !!msgDate
            : (msgDate && prevDate ? !isSameDay(msgDate, prevDate) : false)

          return (
            <React.Fragment key={msg.id || `msg-${i}`}>
              {showDateSeparator && msgDate && (
                <div className="flex items-center gap-3 my-4">
                  <div className="h-px flex-1 bg-plum-200/60 dark:bg-plum-700/40" />
                  <span className="text-xs font-medium text-plum-400 dark:text-plum-300 whitespace-nowrap">
                    {formatDateHeader(msgDate)}
                  </span>
                  <div className="h-px flex-1 bg-plum-200/60 dark:bg-plum-700/40" />
                </div>
              )}
              <MessageBubble message={msg} />
            </React.Fragment>
          )
        })}

        {isStreaming && <StreamingIndicator status={agentStatus} />}
      </div>

      <ChatInput
        onSend={(msg) => sendUserMessage(msg)}
        disabled={isStreaming}
        isStreaming={isStreaming}
        onCancel={cancelStream}
      />
    </div>
  )
}
