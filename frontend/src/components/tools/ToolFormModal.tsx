import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import type { Tool } from '@/types/tool'
import { createTool, updateTool } from '@/api/tools'
import { showToast } from '@/components/shared/Toast'

interface ToolFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  tool?: Tool | null
}

export function ToolFormModal({ isOpen, onClose, onSuccess, tool }: ToolFormModalProps) {
  const isEdit = !!tool
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [descriptionZh, setDescriptionZh] = useState('')
  const [language, setLanguage] = useState('python')
  const [code, setCode] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (isOpen) {
      if (tool) {
        setName(tool.name)
        setDescription(tool.description)
        setDescriptionZh(tool.description_zh ?? '')
        setLanguage(tool.language)
        setCode(tool.code)
      } else {
        setName('')
        setDescription('')
        setDescriptionZh('')
        setLanguage('python')
        setCode('')
      }
    }
  }, [isOpen, tool])

  useEffect(() => {
    if (!isOpen) return
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [isOpen, onClose])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      showToast('warning', '请输入工具名称')
      return
    }
    if (!code.trim()) {
      showToast('warning', '请输入工具代码')
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        name,
        description,
        description_zh: descriptionZh || undefined,
        code,
        language,
      }
      if (isEdit && tool) {
        await updateTool(tool.id, payload)
        showToast('success', '工具更新成功')
      } else {
        await createTool(payload)
        showToast('success', '工具创建成功')
      }
      onSuccess()
      onClose()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '操作失败'
      showToast('error', message)
    } finally {
      setSubmitting(false)
    }
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="mx-4 w-full max-w-2xl overflow-hidden rounded-2xl bg-white shadow-2xl">
        {/* 头部 */}
        <div className="flex items-center justify-between border-b border-plum-100 px-6 py-4">
          <h3 className="text-lg font-semibold text-ink">
            {isEdit ? '编辑工具' : '新建工具'}
          </h3>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-ink-light hover:bg-plum-50 hover:text-ink"
          >
            <X size={18} />
          </button>
        </div>

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="p-6">
          <div className="space-y-4">
            {/* 名称 */}
            <div>
              <label className="mb-1 block text-sm font-medium text-ink">
                名称 <span className="text-plum-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：get_weather"
                className="w-full rounded-xl border border-plum-200 bg-white px-4 py-2.5 text-sm text-ink outline-none transition-colors focus:border-plum-400 focus:ring-1 focus:ring-plum-200"
              />
            </div>

            {/* 描述 */}
            <div>
              <label className="mb-1 block text-sm font-medium text-ink">描述</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="工具的功能描述..."
                rows={2}
                className="w-full resize-none rounded-xl border border-plum-200 bg-white px-4 py-2.5 text-sm text-ink outline-none transition-colors focus:border-plum-400 focus:ring-1 focus:ring-plum-200"
              />
            </div>

            {/* 中文描述 */}
            <div>
              <label className="mb-1 block text-sm font-medium text-ink">中文描述</label>
              <textarea
                value={descriptionZh}
                onChange={(e) => setDescriptionZh(e.target.value)}
                placeholder="输入工具的中文描述（面向用户展示）"
                rows={2}
                className="w-full resize-none rounded-xl border border-plum-200 bg-white px-4 py-2.5 text-sm text-ink outline-none transition-colors focus:border-plum-400 focus:ring-1 focus:ring-plum-200"
              />
            </div>

            {/* 语言 */}
            <div>
              <label className="mb-1 block text-sm font-medium text-ink">语言</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full rounded-xl border border-plum-200 bg-white px-4 py-2.5 text-sm text-ink outline-none transition-colors focus:border-plum-400 focus:ring-1 focus:ring-plum-200"
              >
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="shell">Shell</option>
              </select>
            </div>

            {/* 代码 */}
            <div>
              <label className="mb-1 block text-sm font-medium text-ink">
                代码 <span className="text-plum-500">*</span>
              </label>
              <textarea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="输入工具代码..."
                rows={12}
                className="w-full resize-y rounded-xl border border-plum-200 bg-white px-4 py-2.5 font-mono text-sm text-ink outline-none transition-colors focus:border-plum-400 focus:ring-1 focus:ring-plum-200"
              />
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="mt-6 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-plum-200 px-5 py-2.5 text-sm text-ink-light transition-colors hover:bg-plum-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-xl bg-plum-500 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-plum-600 disabled:opacity-50"
            >
              {submitting ? '提交中...' : isEdit ? '保存' : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
