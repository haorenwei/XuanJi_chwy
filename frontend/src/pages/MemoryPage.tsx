import { useEffect, useState, useCallback } from 'react'
import {
  MessageSquare,
  Wrench,
  Sparkles,
  Heart,
  FileText,
  Eye,
  EyeOff,
  X,
  CheckCircle,
  AlertCircle,
  Pencil,
} from 'lucide-react'
import { getSettings, updateSettings } from '@/api/settings'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { showToast } from '@/components/shared/Toast'
import type { SettingUpdate } from '@/types/setting'

/* ── 类型定义 ─────────────────────────────────────────── */

interface AICardConfig {
  name: string
  role: string
  icon: React.ReactNode
  colorClass: {
    border: string
    headerBg: string
    headerBorder: string
    iconBg: string
    iconText: string
    button: string
    buttonHover: string
    nameText: string
    badge: string
    badgeBg: string
  }
  providerKey: string
  apiKeyKey: string
  modelKey: string
  baseUrlKey: string
}

interface CardData {
  provider: string
  apiKey: string
  modelName: string
  baseUrl: string
}

const PROVIDER_OPTIONS = [
  { value: 'online', label: '在线 API' },
  { value: 'ollama', label: 'Ollama 本地' },
]

const AI_CARDS: AICardConfig[] = [
  {
    name: '玄',
    role: '对话 AI',
    icon: <MessageSquare size={22} />,
    colorClass: {
      border: 'border-blue-200',
      headerBg: 'bg-blue-50',
      headerBorder: 'border-blue-100',
      iconBg: 'bg-blue-100',
      iconText: 'text-blue-600',
      button: 'bg-blue-500 hover:bg-blue-600',
      buttonHover: 'hover:border-blue-300 hover:shadow-blue-100/50',
      nameText: 'text-blue-700',
      badge: 'text-blue-600',
      badgeBg: 'bg-blue-50',
    },
    providerKey: 'llm_provider',
    apiKeyKey: 'llm_api_key',
    modelKey: 'llm_model_name',
    baseUrlKey: 'llm_api_base_url',
  },
  {
    name: '机',
    role: '工具 AI',
    icon: <Wrench size={22} />,
    colorClass: {
      border: 'border-green-200',
      headerBg: 'bg-green-50',
      headerBorder: 'border-green-100',
      iconBg: 'bg-green-100',
      iconText: 'text-green-600',
      button: 'bg-green-500 hover:bg-green-600',
      buttonHover: 'hover:border-green-300 hover:shadow-green-100/50',
      nameText: 'text-green-700',
      badge: 'text-green-600',
      badgeBg: 'bg-green-50',
    },
    providerKey: 'tool_llm_provider',
    apiKeyKey: 'tool_llm_api_key',
    modelKey: 'tool_llm_model_name',
    baseUrlKey: 'tool_llm_api_base_url',
  },
  {
    name: '晴',
    role: '意图解析 AI',
    icon: <Sparkles size={22} />,
    colorClass: {
      border: 'border-purple-200',
      headerBg: 'bg-purple-50',
      headerBorder: 'border-purple-100',
      iconBg: 'bg-purple-100',
      iconText: 'text-purple-600',
      button: 'bg-purple-500 hover:bg-purple-600',
      buttonHover: 'hover:border-purple-300 hover:shadow-purple-100/50',
      nameText: 'text-purple-700',
      badge: 'text-purple-600',
      badgeBg: 'bg-purple-50',
    },
    providerKey: 'intent_llm_provider',
    apiKeyKey: 'intent_llm_api_key',
    modelKey: 'intent_llm_model_name',
    baseUrlKey: 'intent_llm_api_base_url',
  },
  {
    name: '焕',
    role: '情绪管理 AI',
    icon: <Heart size={22} />,
    colorClass: {
      border: 'border-rose-200',
      headerBg: 'bg-rose-50',
      headerBorder: 'border-rose-100',
      iconBg: 'bg-rose-100',
      iconText: 'text-rose-600',
      button: 'bg-rose-500 hover:bg-rose-600',
      buttonHover: 'hover:border-rose-300 hover:shadow-rose-100/50',
      nameText: 'text-rose-700',
      badge: 'text-rose-600',
      badgeBg: 'bg-rose-50',
    },
    providerKey: 'emotion_llm_provider',
    apiKeyKey: 'emotion_llm_api_key',
    modelKey: 'emotion_llm_model_name',
    baseUrlKey: 'emotion_llm_api_base_url',
  },
  {
    name: '遥',
    role: '格式管理 AI',
    icon: <FileText size={22} />,
    colorClass: {
      border: 'border-amber-200',
      headerBg: 'bg-amber-50',
      headerBorder: 'border-amber-100',
      iconBg: 'bg-amber-100',
      iconText: 'text-amber-600',
      button: 'bg-amber-500 hover:bg-amber-600',
      buttonHover: 'hover:border-amber-300 hover:shadow-amber-100/50',
      nameText: 'text-amber-700',
      badge: 'text-amber-600',
      badgeBg: 'bg-amber-50',
    },
    providerKey: 'format_llm_provider',
    apiKeyKey: 'format_llm_api_key',
    modelKey: 'format_llm_model_name',
    baseUrlKey: 'format_llm_api_base_url',
  },
]

/* ── 工具函数 ─────────────────────────────────────────── */

function isMaskedKey(value: string): boolean {
  return value.includes('***')
}

function getProviderLabel(value: string | null): string {
  if (!value) return '未配置'
  const opt = PROVIDER_OPTIONS.find((o) => o.value === value)
  return opt ? opt.label : value
}

/* ── 编辑弹窗组件 ─────────────────────────────────────── */

interface EditModalProps {
  card: AICardConfig
  data: CardData
  onClose: () => void
  onSave: (data: CardData) => Promise<void>
}

function EditModal({ card, data, onClose, onSave }: EditModalProps) {
  const [provider, setProvider] = useState(data.provider || 'online')
  const [apiKey, setApiKey] = useState('')
  const [modelName, setModelName] = useState(data.modelName)
  const [baseUrl, setBaseUrl] = useState(data.baseUrl || '')
  const [showKey, setShowKey] = useState(false)
  const [saving, setSaving] = useState(false)

  const maskedPlaceholder = data.apiKey || 'sk-...'

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave({
        provider,
        apiKey: apiKey.trim(),
        modelName: modelName.trim(),
        baseUrl: baseUrl.trim(),
      })
    } finally {
      setSaving(false)
    }
  }

  const inputClass =
    'w-full rounded-lg border border-plum-200 bg-white px-4 py-2.5 text-sm text-ink outline-none transition-colors focus:border-plum-400 focus:ring-2 focus:ring-plum-200'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 遮罩层 */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* 弹窗 */}
      <div className="relative mx-4 w-full max-w-md rounded-2xl bg-white shadow-2xl">
        {/* 头部 */}
        <div
          className={`flex items-center justify-between rounded-t-2xl border-b px-6 py-4 ${card.colorClass.headerBg} ${card.colorClass.headerBorder}`}
        >
          <div className="flex items-center gap-3">
            <span
              className={`flex h-10 w-10 items-center justify-center rounded-xl ${card.colorClass.iconBg} ${card.colorClass.iconText}`}
            >
              {card.icon}
            </span>
            <div>
              <h3 className="text-base font-semibold text-ink">
                编辑 <span className={card.colorClass.nameText}>{card.name}</span> 配置
              </h3>
              <p className="text-xs text-ink-light">{card.role}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-ink-light transition-colors hover:bg-white/60 hover:text-ink"
          >
            <X size={18} />
          </button>
        </div>

        {/* 表单 */}
        <div className="space-y-4 p-6">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-light">Provider</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className={inputClass}
            >
              {PROVIDER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-light">API Key</label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={maskedPlaceholder}
                className={inputClass + ' pr-10'}
              />
              <button
                type="button"
                onClick={() => setShowKey((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-light transition-colors hover:text-ink"
              >
                {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            <p className="mt-1 text-xs text-ink-light/60">留空则保留当前密钥不变</p>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-light">API Base URL</label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
              className={inputClass}
            />
            <p className="mt-1 text-xs text-ink-light/60">留空则使用全局默认地址</p>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-light">模型名称</label>
            <input
              type="text"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              placeholder="模型标识，如 qwen3-32b"
              className={inputClass}
            />
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex items-center justify-end gap-3 border-t border-plum-50 px-6 py-4">
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-200 bg-white px-5 py-2 text-sm font-medium text-ink-light transition-colors hover:bg-gray-50"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className={`rounded-lg px-5 py-2 text-sm font-medium text-white shadow-sm transition-colors disabled:opacity-60 ${card.colorClass.button}`}
          >
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── AI 卡片组件 ──────────────────────────────────────── */

interface AICardProps {
  card: AICardConfig
  data: CardData
  onEdit: () => void
}

function AICard({ card, data, onEdit }: AICardProps) {
  const { colorClass } = card

  return (
    <div
      className={`group cursor-pointer rounded-xl border ${colorClass.border} bg-white shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-lg ${colorClass.buttonHover}`}
      onClick={onEdit}
    >
      {/* 卡片头部 */}
      <div
        className={`rounded-t-xl border-b px-6 py-5 ${colorClass.headerBg} ${colorClass.headerBorder}`}
      >
        <div className="flex items-center gap-3">
          <span
            className={`flex h-12 w-12 items-center justify-center rounded-xl ${colorClass.iconBg} ${colorClass.iconText} transition-transform duration-300 group-hover:scale-110`}
          >
            {card.icon}
          </span>
          <div>
            <h3 className={`text-2xl font-bold ${colorClass.nameText}`}>{card.name}</h3>
            <p className="text-sm text-ink-light">{card.role}</p>
          </div>
        </div>
      </div>

      {/* 卡片内容 */}
      <div className="space-y-3 px-6 py-5">
        <div className="flex items-center justify-between">
          <span className="text-xs text-ink-light">Provider</span>
          <span className="text-sm font-medium text-ink">{getProviderLabel(data.provider)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-ink-light">模型</span>
          <span className="text-sm font-medium text-ink">{data.modelName || '未配置'}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-ink-light">API Key</span>
          <span className="flex items-center gap-1.5 text-sm font-medium">
            {data.apiKey ? (
              <>
                <CheckCircle size={14} className="text-green-500" />
                <span className="text-green-600">已配置</span>
              </>
            ) : (
              <>
                <AlertCircle size={14} className="text-amber-500" />
                <span className="text-amber-600">未配置</span>
              </>
            )}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-ink-light">Base URL</span>
          <span className="max-w-[60%] truncate text-sm font-medium text-ink">
            {data.baseUrl || '默认'}
          </span>
        </div>
      </div>

      {/* 编辑按钮 */}
      <div className="border-t border-plum-50 px-6 py-4">
        <button
          className={`flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium text-white transition-colors ${colorClass.button}`}
        >
          <Pencil size={14} />
          编辑配置
        </button>
      </div>
    </div>
  )
}

/* ── 主页面 ───────────────────────────────────────────── */

export default function MemoryPage() {
  const [loading, setLoading] = useState(true)
  const [settings, setSettings] = useState<Record<string, string | null>>({})
  const [editingCard, setEditingCard] = useState<AICardConfig | null>(null)

  const loadSettings = useCallback(async () => {
    try {
      const res = await getSettings()
      if (res.data) {
        const s = res.data as unknown as Record<string, unknown>
        const mapped: Record<string, string | null> = {}
        for (const card of AI_CARDS) {
          mapped[card.providerKey] = (s[card.providerKey] as string) ?? null
          mapped[card.apiKeyKey] = (s[card.apiKeyKey] as string) ?? null
          mapped[card.modelKey] = (s[card.modelKey] as string) ?? null
          mapped[card.baseUrlKey] = (s[card.baseUrlKey] as string) ?? null
        }
        setSettings(mapped)
      }
    } catch {
      showToast('error', '加载配置失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSettings()
  }, [loadSettings])

  const getCardData = (card: AICardConfig): CardData => ({
    provider: settings[card.providerKey] ?? '',
    apiKey: settings[card.apiKeyKey] ?? '',
    modelName: settings[card.modelKey] ?? '',
    baseUrl: settings[card.baseUrlKey] ?? '',
  })

  const handleSave = async (card: AICardConfig, data: CardData) => {
    try {
      const payload: SettingUpdate = {}
      const p = payload as Record<string, unknown>

      p[card.providerKey] = data.provider || null
      p[card.modelKey] = data.modelName || null
      p[card.baseUrlKey] = data.baseUrl || null

      // 只有当用户输入了新的 Key 才更新（留空保留原值，掩码值不覆盖）
      if (data.apiKey && !isMaskedKey(data.apiKey)) {
        p[card.apiKeyKey] = data.apiKey
      }

      await updateSettings(payload)
      showToast('success', `${card.name} 配置已保存`)
      setEditingCard(null)
      await loadSettings()
    } catch {
      showToast('error', `保存 ${card.name} 配置失败，请重试`)
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="p-6">
      <div className="mx-auto max-w-7xl">
        {/* 页面标题 */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-ink">记忆体</h1>
          <p className="mt-1 text-sm text-ink-light">管理你的 AI 伙伴配置</p>
        </div>

        {/* AI 卡片 */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {AI_CARDS.map((card) => (
            <AICard
              key={card.name}
              card={card}
              data={getCardData(card)}
              onEdit={() => setEditingCard(card)}
            />
          ))}
        </div>

        {/* 编辑弹窗 */}
        {editingCard && (
          <EditModal
            card={editingCard}
            data={getCardData(editingCard)}
            onClose={() => setEditingCard(null)}
            onSave={(data) => handleSave(editingCard, data)}
          />
        )}
      </div>
    </div>
  )
}
