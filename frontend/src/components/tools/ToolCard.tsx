import type { ToolBrief } from '@/types/tool'
import { Wrench, Star, Pencil, Trash2 } from 'lucide-react'
import { formatRelative } from '@/utils/formatDate'

interface ToolCardProps {
  tool: ToolBrief
  onClick: () => void
  onEdit: () => void
  onDelete: () => void
}

export function ToolCard({ tool, onClick, onEdit, onDelete }: ToolCardProps) {
  return (
    <div className="group relative w-full rounded-xl border border-plum-100 bg-white p-4 shadow-sm transition-all hover:border-plum-300 hover:shadow-md">
      {/* 操作按钮 - 非内置工具才显示 */}
      {!tool.is_builtin && (
        <div className="absolute right-3 top-3 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onEdit()
            }}
            title="编辑"
            className="rounded-lg p-1.5 text-ink-light hover:bg-plum-50 hover:text-plum-500"
          >
            <Pencil size={14} />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
            title="删除"
            className="rounded-lg p-1.5 text-ink-light hover:bg-red-50 hover:text-red-500"
          >
            <Trash2 size={14} />
          </button>
        </div>
      )}

      <button onClick={onClick} className="w-full text-left">
        <div className="mb-2 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-plum-100">
            <Wrench size={14} className="text-plum-500" />
          </div>
          <div className="flex-1 truncate text-sm font-medium text-ink">{tool.name}</div>
          {tool.is_builtin && <Star size={14} className="text-amber-400" />}
        </div>
        <p className="line-clamp-2 text-xs text-ink-light">
          {tool.description_zh || tool.description}
        </p>
        <div className="mt-3 flex items-center gap-2 text-xs text-ink-light/70">
          <span className="rounded bg-plum-50 px-1.5 py-0.5">{tool.language}</span>
          <span>v{tool.version}</span>
          <span className="ml-auto">{formatRelative(tool.created_at)}</span>
        </div>
      </button>
    </div>
  )
}
