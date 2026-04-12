import { useState } from 'react'
import { Send, Square } from 'lucide-react'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  isStreaming?: boolean
  onCancel?: () => void
}

export function ChatInput({ onSend, disabled, isStreaming, onCancel }: ChatInputProps) {
  const [input, setInput] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (trimmed && !disabled) {
      onSend(trimmed)
      setInput('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-plum-100 bg-white px-4 pb-4 pt-2">
      {/* 输入框区域 */}
      <div className="flex items-center gap-3 rounded-2xl border border-plum-200 bg-plum-50 px-4 py-2.5 focus-within:border-plum-400 focus-within:ring-2 focus-within:ring-plum-200">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="向璇玑发送消息..."
          rows={1}
          disabled={disabled || isStreaming}
          className="max-h-32 flex-1 resize-none bg-transparent text-sm leading-6 text-ink outline-none placeholder:text-ink-light/60"
        />
        {isStreaming ? (
          <button
            type="button"
            onClick={onCancel}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-500 text-white transition-colors hover:bg-red-600"
            title="取消生成"
          >
            <Square size={12} />
          </button>
        ) : (
          <button
            type="submit"
            disabled={disabled || !input.trim()}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-plum-500 text-white transition-colors hover:bg-plum-600 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send size={14} />
          </button>
        )}
      </div>
    </form>
  )
}
