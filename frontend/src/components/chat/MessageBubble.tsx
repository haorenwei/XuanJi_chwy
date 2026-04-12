import { useState, useMemo } from 'react'
import { cn } from '@/utils/cn'
import type { ChatMessage, CollaborationStep } from '@/types/chat'
import { useChatStore } from '@/stores/chatStore'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { formatTime } from '@/utils/formatDate'

interface MessageBubbleProps {
  message: ChatMessage
}

interface ParsedContent {
  segments: Array<{ type: 'text'; text: string } | { type: 'think'; text: string }>
}

function parseThinkTags(content: string): ParsedContent {
  const segments: ParsedContent['segments'] = []
  const regex = /<think>([\s\S]*?)<\/think>/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(content)) !== null) {
    // Text before this think block
    if (match.index > lastIndex) {
      segments.push({ type: 'text', text: content.slice(lastIndex, match.index) })
    }
    // Only add think segment if it has non-empty content
    const thinkContent = match[1].trim()
    if (thinkContent) {
      segments.push({ type: 'think', text: thinkContent })
    }
    lastIndex = regex.lastIndex
  }

  // Remaining text
  if (lastIndex < content.length) {
    segments.push({ type: 'text', text: content.slice(lastIndex) })
  }

  return { segments }
}

function ThinkBlock({ text }: { text: string }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="my-1.5 rounded-lg border border-plum-100 bg-plum-50/60">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-1.5 px-3 py-2 text-xs font-medium text-plum-500 transition-colors hover:text-plum-600"
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        AI 思考过程
      </button>
      {open && (
        <div className="border-t border-plum-100 px-3 py-2 text-xs leading-relaxed text-ink-light whitespace-pre-wrap">
          {text}
        </div>
      )}
    </div>
  )
}

/* ── 角色配色映射 ── */
const ROLE_CONFIG: Record<string, { bg: string; text: string; dot: string; darkBg: string; labelColor: string }> = {
  '晴': { bg: 'bg-plum-400', text: 'text-white', dot: 'bg-plum-400', darkBg: 'dark:bg-plum-400', labelColor: 'text-plum-400' },
  '焕': { bg: 'bg-amber-400', text: 'text-white', dot: 'bg-amber-400', darkBg: 'dark:bg-amber-400', labelColor: 'text-amber-500' },
  '机': { bg: 'bg-emerald-400', text: 'text-white', dot: 'bg-emerald-400', darkBg: 'dark:bg-emerald-400', labelColor: 'text-emerald-500' },
  '遥': { bg: 'bg-sky-400', text: 'text-white', dot: 'bg-sky-400', darkBg: 'dark:bg-sky-400', labelColor: 'text-sky-500' },
  '玄': { bg: 'bg-plum-500', text: 'text-white', dot: 'bg-plum-500', darkBg: 'dark:bg-plum-500', labelColor: 'text-plum-500' },
}

const DEFAULT_ROLE_CFG = { bg: 'bg-plum-300', text: 'text-white', dot: 'bg-plum-300', darkBg: 'dark:bg-plum-300', labelColor: 'text-plum-300' }

function getRoleCfg(role: string) {
  for (const [key, cfg] of Object.entries(ROLE_CONFIG)) {
    if (role.includes(key)) return cfg
  }
  return DEFAULT_ROLE_CFG
}

/* ── 气泡：可展开的决策内容 ── */
function StepBubble({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false)
  const needsTruncate = text.length > 80

  return (
    <div
      onClick={() => needsTruncate && setExpanded(!expanded)}
      className={cn(
        'mt-1.5 w-[148px] rounded-lg border border-plum-200 bg-white px-2.5 py-1.5 text-[11px] leading-relaxed text-ink dark:border-plum-700/50 dark:bg-plum-900/30 dark:text-plum-200',
        needsTruncate && 'cursor-pointer',
      )}
    >
      <div
        className={cn(
          'break-words',
          !expanded && 'line-clamp-3',
        )}
      >
        {text}
      </div>
      {needsTruncate && !expanded && (
        <span className="text-[10px] text-plum-300 dark:text-plum-500">…点击展开</span>
      )}
    </div>
  )
}

/* ── 连接箭头 SVG ── */
function ArrowConnector({ targets }: { targets: string[] }) {
  const label = targets.join(', ')
  return (
    <div className="flex shrink-0 flex-col items-center justify-center px-0.5">
      <svg width="32" height="16" viewBox="0 0 32 16" className="text-plum-200 transition-colors hover:text-plum-300 dark:text-plum-700/50 dark:hover:text-plum-600">
        <line x1="0" y1="8" x2="24" y2="8" stroke="currentColor" strokeWidth="1.5" />
        <polyline points="22,4 28,8 22,12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {label && (
        <span className="mt-0.5 text-[9px] leading-none text-plum-300 dark:text-plum-500">
          → {label}
        </span>
      )}
    </div>
  )
}

/* ── 横向时间线协作面板 ── */
interface CollaborationPanelProps {
  steps: CollaborationStep[]
}

function CollaborationPanel({ steps }: CollaborationPanelProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="mt-1">
      {/* 折叠按钮 */}
      <button
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-plum-300 transition-colors hover:bg-plum-50 hover:text-plum-400 dark:text-plum-400 dark:hover:bg-plum-900/30 dark:hover:text-plum-300"
      >
        <span>🌸</span>
        <span>AI 协作过程</span>
        <ChevronDown
          size={12}
          className={cn('transition-transform duration-200', !open && '-rotate-90')}
        />
      </button>

      {/* 展开/折叠动画 (CSS Grid trick) */}
      <div
        className={cn(
          'grid transition-[grid-template-rows] duration-200 ease-out',
          open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]',
        )}
      >
        <div className="overflow-hidden">
          {/* 横向滚动容器 */}
          <div className="mt-1.5 overflow-x-auto py-2">
            <div className="inline-flex items-start gap-0">
              {steps.map((step, i) => {
                const cfg = getRoleCfg(step.role)
                const avatarChar = step.role.replace(/[（(].*/g, '').trim().slice(-1) || '?'
                const hasNext = step.next && step.next.length > 0

                return (
                  <div key={i} className="inline-flex items-start">
                    {/* 节点 */}
                    <div className="flex w-[148px] shrink-0 flex-col items-center">
                      {/* 圆形头像 */}
                      <div
                        className={cn(
                          'flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold leading-none shadow-sm',
                          cfg.bg, cfg.text, cfg.darkBg,
                        )}
                      >
                        {avatarChar}
                      </div>
                      {/* 角色名 + 动作 */}
                      <span className={cn('mt-1 text-[11px] font-medium', cfg.labelColor)}>
                        {step.role}
                      </span>
                      <span className="text-[10px] text-ink-light dark:text-plum-300">
                        {step.action}
                      </span>
                      {/* 决策气泡 */}
                      <StepBubble text={step.result || step.action} />
                    </div>

                    {/* 箭头连接线 */}
                    {hasNext && (
                      <div className="mt-2">
                        <ArrowConnector targets={step.next!} />
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const showCollaboration = useChatStore((s) => s.showCollaboration)
  const timeStr = message.created_at || message.timestamp

  const parsed = useMemo(() => {
    if (message.role !== 'assistant') return null
    return parseThinkTags(message.content)
  }, [message.role, message.content])

  const renderContent = () => {
    if (!parsed) {
      return <div className="whitespace-pre-wrap">{message.content}</div>
    }

    // If all segments are text (no think blocks found), render normally
    const hasThink = parsed.segments.some((s) => s.type === 'think')
    if (!hasThink) {
      // Reconstruct text from segments
      const text = parsed.segments.map((s) => s.text).join('')
      return <div className="whitespace-pre-wrap">{text}</div>
    }

    return (
      <>
        {parsed.segments.map((seg, i) =>
          seg.type === 'think' ? (
            <ThinkBlock key={i} text={seg.text} />
          ) : (
            <div key={i} className="whitespace-pre-wrap">
              {seg.text}
            </div>
          ),
        )}
      </>
    )
  }

  return (
    <div className={cn('flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold',
          isUser ? 'bg-plum-500 text-white' : 'bg-plum-100 text-plum-600',
        )}
      >
        {isUser ? 'U' : 'AI'}
      </div>

      <div className={cn('min-w-0 max-w-[75%] space-y-2')}>
        <div
          className={cn(
            'inline-block rounded-2xl px-4 py-3 text-sm leading-relaxed',
            isUser
              ? 'rounded-tr-md bg-plum-500 text-white'
              : 'rounded-tl-md bg-white text-ink shadow-sm',
          )}
        >
          {renderContent()}
        </div>

        {timeStr && (
          <div className={cn('text-xs text-gray-400 dark:text-gray-500 mt-1', isUser ? 'text-right' : 'text-left')}>
            {formatTime(timeStr)}
          </div>
        )}

        {showCollaboration && message.collaboration && message.collaboration.length > 0 && (
          <CollaborationPanel steps={message.collaboration} />
        )}
      </div>
    </div>
  )
}
