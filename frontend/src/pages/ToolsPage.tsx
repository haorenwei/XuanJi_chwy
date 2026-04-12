import { useEffect, useRef, useState } from 'react'
import { Search, Plus, Upload, Download } from 'lucide-react'
import { listTools, getTool, deleteTool, exportTools, importTools } from '@/api/tools'
import type { Tool, ToolBrief } from '@/types/tool'
import type { ToolCreate } from '@/types/tool'
import { ToolCard } from '@/components/tools/ToolCard'
import { ToolDetailModal } from '@/components/tools/ToolDetailModal'
import { ToolFormModal } from '@/components/tools/ToolFormModal'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { showToast } from '@/components/shared/Toast'

export default function ToolsPage() {
  const [tools, setTools] = useState<ToolBrief[]>([])
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  // 表单弹窗状态
  const [formOpen, setFormOpen] = useState(false)
  const [editingTool, setEditingTool] = useState<Tool | null>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadTools()
  }, [])

  const loadTools = async () => {
    setLoading(true)
    try {
      const res = await listTools()
      setTools(res.data ?? [])
    } catch {
      // handle error
    } finally {
      setLoading(false)
    }
  }

  const handleToolClick = async (id: number) => {
    try {
      const res = await getTool(id)
      setSelectedTool(res.data)
    } catch {
      // handle error
    }
  }

  // 新建工具
  const handleCreate = () => {
    setEditingTool(null)
    setFormOpen(true)
  }

  // 编辑工具（从卡片或详情页触发）
  const handleEdit = async (toolOrBrief: Tool | ToolBrief) => {
    try {
      // 如果是 ToolBrief（没有 code 字段），需要获取完整数据
      if (!('code' in toolOrBrief)) {
        const res = await getTool(toolOrBrief.id)
        setEditingTool(res.data)
      } else {
        setEditingTool(toolOrBrief as Tool)
      }
      setFormOpen(true)
    } catch {
      showToast('error', '获取工具详情失败')
    }
  }

  // 删除工具
  const handleDelete = async (tool: ToolBrief) => {
    if (!window.confirm(`确定要删除工具「${tool.name}」吗？此操作不可撤销。`)) return
    try {
      await deleteTool(tool.id)
      showToast('success', '工具已删除')
      loadTools()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '删除失败'
      showToast('error', message)
    }
  }

  // 导出全部工具
  const handleExport = async () => {
    try {
      const res = await exportTools()
      const json = JSON.stringify(res.data, null, 2)
      const blob = new Blob([json], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      const date = new Date().toISOString().slice(0, 10)
      a.href = url
      a.download = `xuanji-tools-export-${date}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      showToast('success', '导出成功')
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '导出失败'
      showToast('error', message)
    }
  }

  // 导入工具
  const handleImportClick = () => {
    fileInputRef.current?.click()
  }

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    // 重置 input 以便重复选择同一文件
    e.target.value = ''

    if (!file.name.endsWith('.json')) {
      showToast('warning', '请选择 .json 格式文件')
      return
    }

    try {
      const text = await file.text()
      const data: ToolCreate[] = JSON.parse(text)
      if (!Array.isArray(data)) {
        showToast('error', '文件格式错误，需要 JSON 数组')
        return
      }
      const res = await importTools(data)
      const result = res.data
      if (result) {
        showToast(
          'success',
          `导入完成：新建 ${result.created}，更新 ${result.updated}，跳过 ${result.skipped}`,
        )
      }
      loadTools()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '导入失败'
      showToast('error', message)
    }
  }

  const filtered = tools.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.description.toLowerCase().includes(search.toLowerCase()) ||
      (t.description_zh ?? '').toLowerCase().includes(search.toLowerCase()),
  )

  if (loading) return <LoadingSpinner />

  return (
    <div className="p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-ink">工具管理</h1>
        <div className="flex items-center gap-2">
          {/* 搜索框 */}
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-light" />
            <input
              type="text"
              placeholder="搜索工具..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-52 rounded-xl border border-plum-200 bg-white py-2 pl-9 pr-4 text-sm text-ink outline-none focus:border-plum-400 lg:w-64"
            />
          </div>

          {/* 新建工具 */}
          <button
            onClick={handleCreate}
            title="新建工具"
            className="flex items-center gap-1.5 rounded-xl bg-plum-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-plum-600"
          >
            <Plus size={16} />
            <span className="hidden sm:inline">新建工具</span>
          </button>

          {/* 导入 */}
          <button
            onClick={handleImportClick}
            title="导入工具"
            className="rounded-xl border border-plum-200 p-2 text-ink-light transition-colors hover:bg-plum-50 hover:text-plum-500"
          >
            <Upload size={16} />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={handleImportFile}
          />

          {/* 导出 */}
          <button
            onClick={handleExport}
            title="导出全部"
            className="rounded-xl border border-plum-200 p-2 text-ink-light transition-colors hover:bg-plum-50 hover:text-plum-500"
          >
            <Download size={16} />
          </button>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="py-20 text-center text-sm text-ink-light">
          暂无已注册的工具。与 Agent 对话即可自动生成工具。
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((tool) => (
            <ToolCard
              key={tool.id}
              tool={tool}
              onClick={() => handleToolClick(tool.id)}
              onEdit={() => handleEdit(tool)}
              onDelete={() => handleDelete(tool)}
            />
          ))}
        </div>
      )}

      {/* 工具详情弹窗 */}
      <ToolDetailModal
        tool={selectedTool}
        onClose={() => setSelectedTool(null)}
        onEdit={(tool) => handleEdit(tool)}
        onRefresh={loadTools}
      />

      {/* 新建/编辑工具弹窗 */}
      <ToolFormModal
        isOpen={formOpen}
        onClose={() => {
          setFormOpen(false)
          setEditingTool(null)
        }}
        onSuccess={loadTools}
        tool={editingTool}
      />
    </div>
  )
}
