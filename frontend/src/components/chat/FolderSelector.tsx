import { useState, useEffect, useRef } from 'react'
import { FolderOpen, ChevronRight, ArrowUp, X } from 'lucide-react'
import { browseDirectory } from '@/api/files'

interface FolderSelectorProps {
  value?: string
  onChange: (path: string) => void
}

interface FileEntry {
  name: string
  is_dir: boolean
  size: number | null
  path: string
}

export function FolderSelector({ value, onChange }: FolderSelectorProps) {
  const [open, setOpen] = useState(false)
  const [currentPath, setCurrentPath] = useState('')
  const [entries, setEntries] = useState<FileEntry[]>([])
  const [loading, setLoading] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)

  const loadDir = async (path?: string) => {
    setLoading(true)
    try {
      const res = await browseDirectory(path)
      if (res.data) {
        setCurrentPath(res.data.current)
        setEntries(res.data.entries.filter((e) => e.is_dir))
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open) {
      loadDir(value || undefined)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  const goUp = () => {
    const parent = currentPath.replace(/[\\/][^\\/]+$/, '')
    if (parent && parent !== currentPath) {
      loadDir(parent)
    }
  }

  const selectCurrent = () => {
    onChange(currentPath)
    setOpen(false)
  }

  return (
    <div className="relative" ref={panelRef}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 rounded-lg border border-plum-200 bg-white px-2.5 py-1.5 text-xs text-ink-light transition-colors hover:border-plum-400 hover:text-ink"
        title={value || '选择工作目录'}
      >
        <FolderOpen size={14} />
        <span className="max-w-[200px] truncate">
          {value ? value.split(/[\\/]/).pop() : '工作目录'}
        </span>
      </button>

      {open && (
        <div
          onMouseDown={(e) => e.stopPropagation()}
          className="absolute bottom-full left-0 z-50 mb-2 w-72 rounded-xl border border-plum-200 bg-white shadow-xl"
        >
          <div className="flex items-center justify-between border-b border-plum-100 px-3 py-2">
            <span className="text-xs font-medium text-ink">选择目录</span>
            <button type="button" onClick={() => setOpen(false)} className="text-ink-light hover:text-ink">
              <X size={14} />
            </button>
          </div>

          <div className="flex items-center gap-1 border-b border-plum-100 px-3 py-1.5">
            <button
              type="button"
              onClick={goUp}
              className="rounded p-1 text-ink-light hover:bg-plum-50 hover:text-ink"
              title="返回上级"
            >
              <ArrowUp size={14} />
            </button>
            <span className="flex-1 truncate text-xs text-ink-light" title={currentPath}>
              {currentPath}
            </span>
          </div>

          <div className="max-h-48 overflow-auto p-1">
            {loading ? (
              <div className="py-4 text-center text-xs text-ink-light">加载中...</div>
            ) : entries.length === 0 ? (
              <div className="py-4 text-center text-xs text-ink-light">无子目录</div>
            ) : (
              entries.map((entry) => (
                <button
                  key={entry.path}
                  type="button"
                  onClick={() => loadDir(entry.path)}
                  className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs text-ink hover:bg-plum-50"
                >
                  <FolderOpen size={14} className="shrink-0 text-plum-400" />
                  <span className="flex-1 truncate">{entry.name}</span>
                  <ChevronRight size={12} className="shrink-0 text-ink-light" />
                </button>
              ))
            )}
          </div>

          <div className="border-t border-plum-100 p-2">
            <button
              type="button"
              onClick={selectCurrent}
              className="w-full rounded-lg bg-plum-500 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-plum-600"
            >
              选择此目录
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
