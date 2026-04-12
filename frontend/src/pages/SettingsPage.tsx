import { useEffect, useState, useCallback } from 'react'
import {
  Save,
  RotateCcw,
  CheckCircle,
  AlertCircle,
  Activity,
  CalendarDays,
  TrendingUp,
  Brain,
  FileText,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  Filter,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getSettings, updateSettings, getTokenUsage } from '@/api/settings'
import { getLogs } from '@/api/logs'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { useChatStore } from '@/stores/chatStore'
import { formatDate } from '@/utils/formatDate'
import type { SettingUpdate, TokenUsageSummary } from '@/types/setting'
import type { LogEntry } from '@/types/log'

interface Feedback {
  type: 'success' | 'error'
  message: string
}

/* ── 主页面 ──────────────────────────────────────────── */
export default function SettingsPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState<Feedback | null>(null)

  const [monthlyBudget, setMonthlyBudget] = useState('')
  const [tokenUsage, setTokenUsage] = useState<TokenUsageSummary | null>(null)
  const [showCollaboration, setShowCollaboration] = useState(true)

  const [initialBudget, setInitialBudget] = useState('')
  const [initialShowCollaboration, setInitialShowCollaboration] = useState(true)

  // ── 日志状态 ──
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [logTotal, setLogTotal] = useState(0)
  const [logOffset, setLogOffset] = useState(0)
  const [logLevel, setLogLevel] = useState('')
  const [logSource, setLogSource] = useState('')
  const [logLoading, setLogLoading] = useState(false)
  const [expandedLogId, setExpandedLogId] = useState<number | null>(null)
  const LOG_LIMIT = 50

  const showFeedback = useCallback((fb: Feedback) => {
    setFeedback(fb)
    const timer = setTimeout(() => setFeedback(null), 3000)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    loadSettings()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadSettings = async () => {
    try {
      const res = await getSettings()
      if (res.data) {
        const s = res.data
        const budget =
          s.token_monthly_budget != null ? String(s.token_monthly_budget) : ''

        setMonthlyBudget(budget)
        setInitialBudget(budget)

        const collaborationVal = s.show_collaboration != null ? s.show_collaboration : true
        setShowCollaboration(collaborationVal)
        setInitialShowCollaboration(collaborationVal)
      }
      // Load token usage
      try {
        const usageRes = await getTokenUsage()
        if (usageRes.data) setTokenUsage(usageRes.data)
      } catch {
        // token usage is non-critical
      }
    } catch {
      showFeedback({ type: 'error', message: '加载设置失败' })
    } finally {
      setLoading(false)
    }
  }

  // ── 加载日志 ──
  const loadLogs = useCallback(async (offset = 0, level = logLevel, source = logSource) => {
    setLogLoading(true)
    try {
      const res = await getLogs({
        limit: LOG_LIMIT,
        offset,
        level: level || undefined,
        source: source || undefined,
      })
      if (res.data) {
        setLogs(res.data.items)
        setLogTotal(res.data.total)
        setLogOffset(offset)
      }
    } catch {
      // non-critical
    } finally {
      setLogLoading(false)
    }
  }, [logLevel, logSource])

  useEffect(() => {
    loadLogs(0, logLevel, logSource)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [logLevel, logSource])

  const handleSave = async () => {
    setSaving(true)
    try {
      const data: SettingUpdate = {
        token_monthly_budget: monthlyBudget ? Number(monthlyBudget) : null,
        show_collaboration: showCollaboration,
      }
      await updateSettings(data)
      showFeedback({ type: 'success', message: '设置已保存' })
      setInitialBudget(monthlyBudget)
      // Sync to chatStore
      useChatStore.getState().setShowCollaboration(showCollaboration)
      // Refresh token usage after save
      try {
        const usageRes = await getTokenUsage()
        if (usageRes.data) setTokenUsage(usageRes.data)
      } catch {
        // non-critical
      }
    } catch {
      showFeedback({ type: 'error', message: '保存失败，请重试' })
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setMonthlyBudget(initialBudget)
    setShowCollaboration(initialShowCollaboration)
  }

  if (loading) return <LoadingSpinner />

  const inputClass =
    'w-full rounded-lg border border-plum-200 bg-white px-4 py-2.5 text-sm text-ink outline-none transition-colors focus:border-plum-400 focus:ring-2 focus:ring-plum-200'

  const formatTokens = (n: number): string => {
    if (n >= 1_000_000) return `${(n / 10_000).toFixed(0)}万`
    if (n >= 10_000) return `${(n / 10_000).toFixed(1)}万`
    return n.toLocaleString()
  }

  const getProgressColor = (pct: number) => {
    if (pct > 100) return 'bg-rose-500 animate-pulse'
    if (pct > 80) return 'bg-rose-500'
    if (pct >= 60) return 'bg-amber-400'
    return 'bg-plum-400'
  }

  return (
    <div className="p-6">
      <div className="mx-auto max-w-2xl space-y-6">
        <h1 className="text-xl font-semibold text-ink">设置</h1>

        {/* Feedback */}
        {feedback && (
          <div
            className={`flex items-center gap-2 rounded-lg px-4 py-3 text-sm ${
              feedback.type === 'success'
                ? 'bg-green-50 text-green-700'
                : 'bg-red-50 text-red-700'
            }`}
          >
            {feedback.type === 'success' ? (
              <CheckCircle size={16} />
            ) : (
              <AlertCircle size={16} />
            )}
            {feedback.message}
          </div>
        )}

        {/* AI 配置入口提示 */}
        <Link
          to="/memory"
          className="flex items-center gap-3 rounded-2xl border border-plum-100 bg-white p-5 shadow-sm transition-colors hover:border-plum-300 hover:bg-plum-50/30"
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-plum-100 text-plum-600">
            <Brain size={20} />
          </span>
          <div className="flex-1">
            <h2 className="text-sm font-semibold text-ink">AI 模型配置</h2>
            <p className="mt-0.5 text-xs text-ink-light">
              前往「记忆体」管理 玄、机、晴 的 AI 配置
            </p>
          </div>
          <span className="text-xs text-plum-400">→</span>
        </Link>

        {/* 聊天偏好 */}
        <div className="rounded-2xl border border-plum-100 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-ink">聊天偏好</h2>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-ink">显示 AI 协作过程</p>
              <p className="mt-0.5 text-xs text-ink-light">
                在对话中展示 AI 团队的协作细节
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={showCollaboration}
              onClick={() => setShowCollaboration(!showCollaboration)}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-plum-400 focus:ring-offset-2 ${
                showCollaboration ? 'bg-plum-500' : 'bg-gray-200'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                  showCollaboration ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>

        {/* 区块 3: Token 用量管理 */}
        <div className="rounded-2xl border border-plum-100 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-ink">Token 用量管理</h2>
          <div className="space-y-5">
            {/* 月度预算设置 */}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-ink-light">
                月度 Token 预算
              </label>
              <input
                type="number"
                value={monthlyBudget}
                onChange={(e) => setMonthlyBudget(e.target.value)}
                placeholder="留空表示不限制"
                min={0}
                className={inputClass}
              />
            </div>

            {/* Token 用量进度条 */}
            {tokenUsage && (
              <>
                {tokenUsage.monthly_budget != null && tokenUsage.monthly_budget > 0 && (() => {
                  const pct = (tokenUsage.month_tokens / tokenUsage.monthly_budget) * 100
                  const clampedPct = Math.min(pct, 100)
                  return (
                    <div>
                      <div className="mb-1.5 flex items-center justify-between text-xs">
                        <span className="font-medium text-ink-light">本月用量进度</span>
                        <span className={`font-semibold ${pct > 100 ? 'text-rose-500' : pct > 80 ? 'text-rose-500' : pct >= 60 ? 'text-amber-500' : 'text-ink'}`}>
                          {pct.toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-3 w-full overflow-hidden rounded-full bg-plum-50">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ease-out ${getProgressColor(pct)}`}
                          style={{ width: `${clampedPct}%` }}
                        />
                      </div>
                      <div className="mt-1 flex justify-between text-xs text-ink-light">
                        <span>{formatTokens(tokenUsage.month_tokens)} 已用</span>
                        <span>预算 {formatTokens(tokenUsage.monthly_budget)}</span>
                      </div>
                      {pct > 100 && (
                        <div className="mt-2 flex items-center gap-1.5 rounded-lg bg-rose-50 px-3 py-2 text-xs font-medium text-rose-600">
                          <AlertCircle size={14} />
                          本月用量已超出预算 {(pct - 100).toFixed(1)}%
                        </div>
                      )}
                    </div>
                  )
                })()}

                {/* 统计卡片 */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="rounded-xl border border-plum-100 bg-plum-50/40 p-3">
                    <div className="mb-1 flex items-center gap-1.5 text-xs text-ink-light">
                      <Activity size={13} />
                      今日用量
                    </div>
                    <div className="text-lg font-semibold text-ink">
                      {formatTokens(tokenUsage.today_tokens)}
                    </div>
                  </div>
                  <div className="rounded-xl border border-plum-100 bg-plum-50/40 p-3">
                    <div className="mb-1 flex items-center gap-1.5 text-xs text-ink-light">
                      <CalendarDays size={13} />
                      本月用量
                    </div>
                    <div className="text-lg font-semibold text-ink">
                      {formatTokens(tokenUsage.month_tokens)}
                    </div>
                  </div>
                  <div className="rounded-xl border border-plum-100 bg-plum-50/40 p-3">
                    <div className="mb-1 flex items-center gap-1.5 text-xs text-ink-light">
                      <TrendingUp size={13} />
                      累计总量
                    </div>
                    <div className="text-lg font-semibold text-ink">
                      {formatTokens(tokenUsage.total_tokens)}
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 rounded-lg bg-plum-500 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-plum-600 disabled:opacity-60"
          >
            <Save size={16} />
            {saving ? '保存中...' : '保存设置'}
          </button>
          <button
            onClick={handleReset}
            className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-5 py-2.5 text-sm font-medium text-ink-light transition-colors hover:bg-gray-50"
          >
            <RotateCcw size={16} />
            重置
          </button>
        </div>

        {/* ── 系统日志 ── */}
        <div className="rounded-2xl border border-plum-100 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <FileText size={18} className="text-plum-500" />
            <h2 className="text-sm font-semibold text-ink">系统日志</h2>
          </div>

          {/* 筛选栏 */}
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5">
              <Filter size={14} className="text-ink-light" />
              <select
                value={logLevel}
                onChange={(e) => setLogLevel(e.target.value)}
                className="rounded-lg border border-plum-200 bg-white px-3 py-1.5 text-sm text-ink outline-none focus:border-plum-400 focus:ring-2 focus:ring-plum-200"
              >
                <option value="">全部级别</option>
                <option value="info">Info</option>
                <option value="warn">Warn</option>
                <option value="error">Error</option>
                <option value="debug">Debug</option>
              </select>
            </div>
            <input
              type="text"
              placeholder="按来源筛选，如 agent.format"
              value={logSource}
              onChange={(e) => setLogSource(e.target.value)}
              className="rounded-lg border border-plum-200 bg-white px-3 py-1.5 text-sm text-ink outline-none focus:border-plum-400 focus:ring-2 focus:ring-plum-200"
            />
            <span className="ml-auto text-xs text-ink-light">
              共 {logTotal} 条
            </span>
          </div>

          {/* 日志表格 */}
          {logLoading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : logs.length === 0 ? (
            <div className="py-8 text-center text-sm text-ink-light">暂无日志记录</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-plum-100 text-xs text-ink-light">
                    <th className="pb-2 pr-3 font-medium">时间</th>
                    <th className="pb-2 pr-3 font-medium">来源</th>
                    <th className="pb-2 pr-3 font-medium">级别</th>
                    <th className="pb-2 pr-3 font-medium">消息</th>
                    <th className="pb-2 font-medium">状态码</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <LogRow
                      key={log.id}
                      log={log}
                      expanded={expandedLogId === log.id}
                      onToggle={() => setExpandedLogId(expandedLogId === log.id ? null : log.id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 分页 */}
          {logTotal > LOG_LIMIT && (
            <div className="mt-4 flex items-center justify-between border-t border-plum-50 pt-3">
              <button
                disabled={logOffset === 0}
                onClick={() => loadLogs(Math.max(0, logOffset - LOG_LIMIT))}
                className="flex items-center gap-1 rounded-lg border border-plum-200 px-3 py-1.5 text-xs font-medium text-ink-light transition-colors hover:bg-plum-50 disabled:opacity-40"
              >
                <ChevronLeft size={14} />
                上一页
              </button>
              <span className="text-xs text-ink-light">
                {logOffset + 1}-{Math.min(logOffset + LOG_LIMIT, logTotal)} / {logTotal}
              </span>
              <button
                disabled={logOffset + LOG_LIMIT >= logTotal}
                onClick={() => loadLogs(logOffset + LOG_LIMIT)}
                className="flex items-center gap-1 rounded-lg border border-plum-200 px-3 py-1.5 text-xs font-medium text-ink-light transition-colors hover:bg-plum-50 disabled:opacity-40"
              >
                下一页
                <ChevronRight size={14} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ── 日志行组件 ── */
function LogRow({ log, expanded, onToggle }: { log: LogEntry; expanded: boolean; onToggle: () => void }) {
  const levelColors: Record<string, string> = {
    info: 'bg-blue-100 text-blue-700',
    debug: 'bg-gray-100 text-gray-700',
    warn: 'bg-amber-100 text-amber-700',
    error: 'bg-red-100 text-red-700',
  }

  return (
    <>
      <tr
        className="cursor-pointer border-b border-plum-50 transition-colors hover:bg-plum-50/30"
        onClick={onToggle}
      >
        <td className="whitespace-nowrap py-2 pr-3 text-xs text-ink-light">
          {formatDate(log.created_at)}
        </td>
        <td className="py-2 pr-3 text-xs text-ink-light">{log.source ?? '-'}</td>
        <td className="py-2 pr-3">
          <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${levelColors[log.level] ?? 'bg-gray-100 text-gray-600'}`}>
            {log.level}
          </span>
        </td>
        <td className="max-w-xs truncate py-2 pr-3 text-xs text-ink">{log.message}</td>
        <td className="py-2 text-xs text-ink-light">{log.status_code ?? '-'}</td>
      </tr>
      {expanded && log.details && (
        <tr className="border-b border-plum-50">
          <td colSpan={5} className="bg-plum-50/40 px-4 py-3">
            <div className="flex items-start gap-2">
              <ChevronDown size={14} className="mt-0.5 shrink-0 text-ink-light" />
              <pre className="max-h-48 overflow-auto whitespace-pre-wrap text-xs text-ink-light">
                {JSON.stringify(log.details, null, 2)}
              </pre>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
