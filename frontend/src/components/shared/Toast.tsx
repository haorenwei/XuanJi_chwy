import { useEffect, useState } from 'react'
import { CheckCircle2, XCircle, Info, AlertTriangle, X } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

interface ToastItem {
  id: number
  type: ToastType
  message: string
}

const icons = {
  success: CheckCircle2,
  error: XCircle,
  info: Info,
  warning: AlertTriangle,
}

const borderColors = {
  success: 'border-l-green-500',
  error: 'border-l-red-500',
  info: 'border-l-[#FF5C8A]',
  warning: 'border-l-amber-500',
}

const iconColors = {
  success: 'text-green-500',
  error: 'text-red-500',
  info: 'text-[#FF5C8A]',
  warning: 'text-amber-500',
}

/* -------- 全局 Toast 管理 -------- */
type Listener = (items: ToastItem[]) => void
let toasts: ToastItem[] = []
let listeners: Listener[] = []
let nextId = 0

function emit() {
  listeners.forEach((l) => l([...toasts]))
}

// eslint-disable-next-line react-refresh/only-export-components
export function showToast(type: ToastType, message: string, duration = 3000) {
  const id = nextId++
  toasts = [...toasts, { id, type, message }]
  emit()
  if (duration > 0) {
    setTimeout(() => removeToast(id), duration)
  }
  return id
}

// eslint-disable-next-line react-refresh/only-export-components
export function removeToast(id: number) {
  toasts = toasts.filter((t) => t.id !== id)
  emit()
}

/* -------- 单条 Toast 渲染 -------- */
function ToastCard({ item, onClose }: { item: ToastItem; onClose: () => void }) {
  const [visible, setVisible] = useState(false)
  const Icon = icons[item.type]

  useEffect(() => {
    // 触发入场动画
    const raf = requestAnimationFrame(() => setVisible(true))
    return () => cancelAnimationFrame(raf)
  }, [])

  return (
    <div
      className={`pointer-events-auto flex w-80 items-center gap-3 rounded-xl border-l-4 bg-[#FFF5F7] px-4 py-3 shadow-lg transition-all duration-300 ${
        borderColors[item.type]
      } ${visible ? 'translate-y-0 opacity-100' : '-translate-y-4 opacity-0'}`}
    >
      <Icon className={`h-5 w-5 shrink-0 ${iconColors[item.type]}`} />
      <span className="flex-1 text-sm text-[#2D1B25]">{item.message}</span>
      <button
        onClick={onClose}
        className="shrink-0 rounded-md p-0.5 text-[#2D1B25]/40 transition-colors hover:text-[#2D1B25]"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}

/* -------- Toast 容器（挂载在页面顶部） -------- */
export function ToastContainer() {
  const [items, setItems] = useState<ToastItem[]>([])

  useEffect(() => {
    listeners.push(setItems)
    return () => {
      listeners = listeners.filter((l) => l !== setItems)
    }
  }, [])

  if (items.length === 0) return null

  return (
    <div className="pointer-events-none fixed left-1/2 top-4 z-50 flex -translate-x-1/2 flex-col items-center gap-2">
      {items.map((item) => (
        <ToastCard key={item.id} item={item} onClose={() => removeToast(item.id)} />
      ))}
    </div>
  )
}
