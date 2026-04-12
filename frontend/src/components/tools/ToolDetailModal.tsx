import { useEffect, useState } from 'react'
import { X, Pencil, RotateCcw, Loader2 } from 'lucide-react'
import type { Tool, ToolVersion } from '@/types/tool'
import { getToolVersions, rollbackToolVersion } from '@/api/tools'
import { showToast } from '@/components/shared/Toast'
import { formatRelative } from '@/utils/formatDate'

interface ToolDetailModalProps {
  tool: Tool | null
  onClose: () => void
  onEdit?: (tool: Tool) => void
  onRefresh?: () => void
}

type TabKey = 'code' | 'versions'

export function ToolDetailModal({ tool, onClose, onEdit, onRefresh }: ToolDetailModalProps) {
  const [activeTab, setActiveTab] = useState<TabKey>('code')
  const [versions, setVersions] = useState<ToolVersion[]>([])
  const [versionsLoading, setVersionsLoading] = useState(false)
  const [rollingBack, setRollingBack] = useState<number | null>(null)

  // Reset tab when tool changes
  useEffect(() => {
    if (tool) {
      setActiveTab('code')
      setVersions([])
    }
  }, [tool?.id])

  // Load data when tab changes
  useEffect(() => {
    if (!tool) return
    if (activeTab === 'versions' && versions.length === 0) {
      loadVersions()
    }
  }, [activeTab, tool?.id])

  const loadVersions = async () => {
    if (!tool) return
    setVersionsLoading(true)
    try {
      const res = await getToolVersions(tool.id)
      setVersions(res.data ?? [])
    } catch {
      showToast('error', '获取版本历史失败')
    } finally {
      setVersionsLoading(false)
    }
  }

  const handleRollback = async (version: number) => {
    if (!tool) return
    if (!window.confirm(`确定要回退到版本 v${version} 吗？当前版本的更改将被覆盖。`)) return
    setRollingBack(version)
    try {
      await rollbackToolVersion(tool.id, version)
      showToast('success', `已回退到版本 v${version}`)
      await loadVersions()
      onRefresh?.()
    } catch {
      showToast('error', '版本回退失败')
    } finally {
      setRollingBack(null)
    }
  }

  if (!tool) return null

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'code', label: '代码' },
    { key: 'versions', label: '版本历史' },
  ]

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="mx-4 max-h-[80vh] w-full max-w-2xl overflow-hidden rounded-2xl bg-white shadow-2xl">
        {/* 头部 */}
        <div className="border-b border-plum-100 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-semibold text-ink truncate">{tool.name}</h3>
              </div>
              <p className="mt-1 text-sm text-ink-light">
                {tool.description_zh || tool.description}
              </p>
              {tool.description_zh && tool.description && (
                <p className="mt-0.5 text-xs text-ink-light/60">{tool.description}</p>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0 ml-4">
              {!tool.is_builtin && onEdit && (
                <button
                  onClick={() => {
                    onEdit(tool)
                    onClose()
                  }}
                  className="rounded-lg p-2 text-ink-light hover:bg-plum-50 hover:text-plum-500"
                  title="编辑"
                >
                  <Pencil size={18} />
                </button>
              )}
              <button
                onClick={onClose}
                className="rounded-lg p-2 text-ink-light hover:bg-plum-50 hover:text-ink"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* 元信息 */}
          <div className="mt-3 flex gap-3 text-xs text-ink-light">
            <span className="rounded bg-plum-50 px-2 py-1">语言: {tool.language}</span>
            <span className="rounded bg-plum-50 px-2 py-1">v{tool.version}</span>
            <span className="rounded bg-plum-50 px-2 py-1">
              {tool.is_builtin ? '内置' : '生成'}
            </span>
          </div>

          {/* Tab 切换 */}
          <div className="mt-4 flex gap-4 -mb-[1px]">
            {tabs.map((t) => (
              <button
                key={t.key}
                onClick={() => setActiveTab(t.key)}
                className={`pb-2 text-sm font-medium transition-colors border-b-2 ${
                  activeTab === t.key
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab 内容 */}
        <div className="max-h-[60vh] overflow-auto p-6">
          {activeTab === 'code' && <CodeTab tool={tool} />}
          {activeTab === 'versions' && (
            <VersionsTab
              versions={versions}
              loading={versionsLoading}
              currentVersion={tool.version}
              rollingBack={rollingBack}
              onRollback={handleRollback}
            />
          )}
        </div>
      </div>
    </div>
  )
}

/* ---------- 代码 Tab ---------- */
function CodeTab({ tool }: { tool: Tool }) {
  return (
    <pre className="overflow-auto rounded-xl bg-gray-900 p-4 text-xs text-gray-100">
      <code>{tool.code}</code>
    </pre>
  )
}

/* ---------- 版本历史 Tab ---------- */
function VersionsTab({
  versions,
  loading,
  currentVersion,
  rollingBack,
  onRollback,
}: {
  versions: ToolVersion[]
  loading: boolean
  currentVersion: number
  rollingBack: number | null
  onRollback: (version: number) => void
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-10">
        <Loader2 size={20} className="animate-spin text-plum-400" />
        <span className="ml-2 text-sm text-ink-light">加载中...</span>
      </div>
    )
  }

  if (versions.length === 0) {
    return (
      <div className="py-10 text-center text-sm text-ink-light">
        暂无版本历史
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {versions.map((v) => {
        const isCurrent = v.version === currentVersion
        return (
          <div
            key={v.id}
            className={`flex items-center gap-4 rounded-xl border p-3 ${
              isCurrent
                ? 'border-indigo-200 bg-indigo-50/50'
                : 'border-plum-100 bg-white'
            }`}
          >
            <div className="flex items-center gap-2 shrink-0">
              <span
                className={`text-sm font-semibold ${isCurrent ? 'text-indigo-600' : 'text-ink'}`}
              >
                v{v.version}
              </span>
              {isCurrent && (
                <span className="text-xs px-1.5 py-0.5 rounded-full bg-indigo-100 text-indigo-600">
                  当前
                </span>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-ink truncate">
                {v.change_summary || '无变更说明'}
              </p>
              <p className="text-xs text-ink-light mt-0.5">{formatRelative(v.created_at)}</p>
            </div>
            {!isCurrent && (
              <button
                onClick={() => onRollback(v.version)}
                disabled={rollingBack !== null}
                className="flex items-center gap-1 shrink-0 rounded-lg border border-plum-200 px-2.5 py-1.5 text-xs text-ink-light transition-colors hover:bg-plum-50 hover:text-plum-500 disabled:opacity-50"
              >
                {rollingBack === v.version ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <RotateCcw size={12} />
                )}
                回退
              </button>
            )}
          </div>
        )
      })}
    </div>
  )
}
