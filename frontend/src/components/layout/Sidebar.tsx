import { Link, useLocation } from 'react-router-dom'
import { MessageSquare, BarChart3, Settings, LogOut, Brain } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useAuthStore } from '@/stores/authStore'
import { useUIStore } from '@/stores/uiStore'

const navItems = [
  { path: '/', label: '对话', icon: MessageSquare },
  { path: '/memory', label: '记忆体', icon: Brain },
  { path: '/dashboard', label: '总览', icon: BarChart3 },
  { path: '/settings', label: '设置', icon: Settings },
]

export function Sidebar() {
  const location = useLocation()
  const logout = useAuthStore((s) => s.logout)
  const sidebarOpen = useUIStore((s) => s.sidebarOpen)

  return (
    <aside
      className={cn(
        'flex h-screen flex-col bg-gradient-to-b from-plum-800 to-plum-900 text-white transition-all duration-300',
        sidebarOpen ? 'w-56' : 'w-16',
      )}
    >
      <div className="flex items-center gap-2 border-b border-plum-700/50 px-4 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-plum-500 text-sm font-bold">
          玄
        </div>
        {sidebarOpen && <span className="text-lg font-semibold tracking-wide">璇玑</span>}
      </div>

      <nav className="mt-4 flex-1 space-y-1 px-2">
        {navItems.map(({ path, label, icon: Icon }) => {
          const active = location.pathname === path
          return (
            <Link
              key={path}
              to={path}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
                active
                  ? 'bg-plum-600/50 text-white'
                  : 'text-plum-200 hover:bg-plum-700/40 hover:text-white',
              )}
            >
              <Icon size={18} />
              {sidebarOpen && <span>{label}</span>}
            </Link>
          )
        })}
      </nav>

      <div className="border-t border-plum-700/50 p-2">
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-plum-300 transition-colors hover:bg-plum-700/40 hover:text-white"
        >
          <LogOut size={18} />
          {sidebarOpen && <span>退出登录</span>}
        </button>
      </div>
    </aside>
  )
}
