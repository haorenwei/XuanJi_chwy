import { useEffect, useState } from 'react'
import { Zap, TrendingUp, Database } from 'lucide-react'
import { getDashboardStats, getTokenByRole, getTokenDaily, getTokenByModel } from '@/api/stats'
import type { TokenByRoleItem, TokenDailyItem, TokenByModelItem } from '@/api/stats'
import { EChart } from '@/components/charts/EChart'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import type * as echarts from 'echarts'

interface TokenOverview {
  today_tokens: number
  month_tokens: number
  total_tokens: number
  monthly_budget: number | null
}

const fmt = (n: number) => (n >= 10000 ? (n / 10000).toFixed(1) + '万' : n.toLocaleString())

const ROLE_COLOR: Record<string, string> = {
  玄: '#E8366D',
  晴: '#67e0e3',
  焕: '#FF8FAB',
  机: '#37a2da',
  遥: '#9b8bba',
}

export default function DashboardPage() {
  const [overview, setOverview] = useState<TokenOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [tokenByRole, setTokenByRole] = useState<TokenByRoleItem[]>([])
  const [tokenDaily, setTokenDaily] = useState<TokenDailyItem[]>([])
  const [tokenByModel, setTokenByModel] = useState<TokenByModelItem[]>([])

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [dashRes, roleRes, dailyRes, modelRes] = await Promise.allSettled([
        getDashboardStats(),
        getTokenByRole(),
        getTokenDaily(),
        getTokenByModel(),
      ])
      if (dashRes.status === 'fulfilled' && dashRes.value.data) setOverview(dashRes.value.data)
      if (roleRes.status === 'fulfilled' && roleRes.value.data) setTokenByRole(roleRes.value.data)
      if (dailyRes.status === 'fulfilled' && dailyRes.value.data)
        setTokenDaily(dailyRes.value.data)
      if (modelRes.status === 'fulfilled' && modelRes.value.data)
        setTokenByModel(modelRes.value.data)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <LoadingSpinner />
  if (!overview) return <div className="p-6 text-ink-light">加载统计数据失败</div>

  const statCards = [
    {
      label: '今日 Token 用量',
      value: fmt(overview.today_tokens),
      icon: Zap,
      color: 'text-plum-500',
      bg: 'bg-plum-50',
    },
    {
      label: '本月 Token 用量',
      value: fmt(overview.month_tokens),
      icon: TrendingUp,
      color: 'text-blue-500',
      bg: 'bg-blue-50',
    },
    {
      label: '累计 Token 用量',
      value: fmt(overview.total_tokens),
      icon: Database,
      color: 'text-green-500',
      bg: 'bg-green-50',
    },
  ]

  // ── Token Daily Trend Line Chart ──
  const dailyDates = [...new Set(tokenDaily.map((d) => d.date))].sort()
  const dailyRoles = [...new Set(tokenDaily.map((d) => d.role_name))]

  const dailyLineOption: echarts.EChartsOption = {
    title: { text: 'Token 每日趋势', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: dailyRoles, bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
    xAxis: { type: 'category', data: dailyDates },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: (v: number) => (v >= 10000 ? (v / 10000).toFixed(1) + '万' : String(v)),
      },
    },
    series: dailyRoles.map((role) => ({
      name: role,
      type: 'line' as const,
      smooth: true,
      data: dailyDates.map(
        (date) => tokenDaily.find((d) => d.date === date && d.role_name === role)?.total_tokens ?? 0,
      ),
      itemStyle: { color: ROLE_COLOR[role] || '#999' },
      areaStyle: { opacity: 0.08 },
    })),
  }

  // ── Token by Role — Pie Chart ──
  const roleAgg = tokenByRole.reduce<Record<string, number>>((acc, item) => {
    acc[item.role_name] = (acc[item.role_name] ?? 0) + item.total_tokens
    return acc
  }, {})

  const tokenPieOption: echarts.EChartsOption = {
    title: { text: 'AI 角色 Token 占比', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [
      {
        type: 'pie',
        radius: ['35%', '65%'],
        data: Object.entries(roleAgg).map(([name, value]) => ({
          name,
          value,
          itemStyle: { color: ROLE_COLOR[name] || '#999' },
        })),
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { formatter: '{b}\n{d}%' },
      },
    ],
  }

  // ── Token by Role — Stacked Bar Chart ──
  const roleNames = [...new Set(tokenByRole.map((t) => t.role_name))]
  const promptByRole = roleNames.map((r) =>
    tokenByRole.filter((t) => t.role_name === r).reduce((s, t) => s + t.prompt_tokens, 0),
  )
  const completionByRole = roleNames.map((r) =>
    tokenByRole.filter((t) => t.role_name === r).reduce((s, t) => s + t.completion_tokens, 0),
  )

  const tokenBarOption: echarts.EChartsOption = {
    title: { text: 'AI 角色 Token 用量明细', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['Prompt Tokens', 'Completion Tokens'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
    xAxis: { type: 'category', data: roleNames },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: (v: number) => (v >= 10000 ? (v / 10000).toFixed(1) + '万' : String(v)),
      },
    },
    series: [
      {
        name: 'Prompt Tokens',
        type: 'bar',
        stack: 'total',
        data: promptByRole,
        itemStyle: { color: '#E8366D' },
      },
      {
        name: 'Completion Tokens',
        type: 'bar',
        stack: 'total',
        data: completionByRole,
        itemStyle: { color: '#FF8FAB' },
      },
    ],
  }

  // ── Token by Model — Stacked Bar Chart ──
  const modelNames = tokenByModel.map((m) => m.model)
  const modelPrompt = tokenByModel.map((m) => m.prompt_tokens)
  const modelCompletion = tokenByModel.map((m) => m.completion_tokens)

  const modelBarOption: echarts.EChartsOption = {
    title: { text: '各模型 Token 用量', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['Prompt Tokens', 'Completion Tokens'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      data: modelNames,
      axisLabel: { rotate: modelNames.length > 4 ? 20 : 0 },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: (v: number) => (v >= 10000 ? (v / 10000).toFixed(1) + '万' : String(v)),
      },
    },
    series: [
      {
        name: 'Prompt Tokens',
        type: 'bar',
        stack: 'total',
        data: modelPrompt,
        itemStyle: { color: '#37a2da' },
      },
      {
        name: 'Completion Tokens',
        type: 'bar',
        stack: 'total',
        data: modelCompletion,
        itemStyle: { color: '#67e0e3' },
      },
    ],
  }

  const hasDaily = tokenDaily.length > 0
  const hasRole = tokenByRole.length > 0
  const hasModel = tokenByModel.length > 0

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-xl font-semibold text-ink">Token 数据中心</h1>

      {/* Overview Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {statCards.map(({ label, value, icon: Icon, color, bg }) => (
          <div
            key={label}
            className="flex items-center gap-4 rounded-xl border border-plum-100 bg-white p-4 shadow-sm"
          >
            <div className={`rounded-lg ${bg} p-2.5 ${color}`}>
              <Icon size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-ink">{value}</p>
              <p className="text-xs text-ink-light">{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Daily Trend (full width) */}
      {hasDaily ? (
        <div className="rounded-xl border border-plum-100 bg-white p-4 shadow-sm">
          <EChart option={dailyLineOption} className="h-72 w-full" />
        </div>
      ) : (
        <div className="rounded-xl border border-plum-100 bg-white p-6 text-center text-sm text-ink-light shadow-sm">
          暂无每日趋势数据
        </div>
      )}

      {/* Role Pie + Role Bar (2-col) */}
      {hasRole ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-plum-100 bg-white p-4 shadow-sm">
            <EChart option={tokenPieOption} className="h-72 w-full" />
          </div>
          <div className="rounded-xl border border-plum-100 bg-white p-4 shadow-sm">
            <EChart option={tokenBarOption} className="h-72 w-full" />
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-plum-100 bg-white p-6 text-center text-sm text-ink-light shadow-sm">
          暂无角色 Token 用量数据
        </div>
      )}

      {/* Model Bar (full width) */}
      {hasModel ? (
        <div className="rounded-xl border border-plum-100 bg-white p-4 shadow-sm">
          <EChart option={modelBarOption} className="h-72 w-full" />
        </div>
      ) : (
        <div className="rounded-xl border border-plum-100 bg-white p-6 text-center text-sm text-ink-light shadow-sm">
          暂无模型 Token 用量数据
        </div>
      )}
    </div>
  )
}
