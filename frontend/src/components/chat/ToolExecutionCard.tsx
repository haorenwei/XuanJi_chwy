import type { ToolExecution } from '@/types/chat'
import { CheckCircle, XCircle } from 'lucide-react'

interface ToolExecutionCardProps {
  execution: ToolExecution
}

export function ToolExecutionCard({ execution }: ToolExecutionCardProps) {
  return (
    <div className="rounded-xl border border-plum-200 bg-plum-50 p-3">
      <div className="mb-2 flex items-center gap-2">
        {execution.success ? (
          <CheckCircle size={16} className="text-green-500" />
        ) : (
          <XCircle size={16} className="text-red-500" />
        )}
        <span className="text-xs font-medium text-ink">工具: {execution.tool}</span>
        <span
          className={`rounded-full px-2 py-0.5 text-xs ${
            execution.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}
        >
          {execution.success ? '成功' : '失败'}
        </span>
      </div>
      <pre className="max-h-40 overflow-auto rounded-lg bg-white p-2 text-xs text-ink-light">
        {execution.result}
      </pre>
    </div>
  )
}
