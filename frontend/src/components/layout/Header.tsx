import { Menu } from 'lucide-react'
import { useUIStore } from '@/stores/uiStore'
import { useAuthStore } from '@/stores/authStore'

export function Header() {
  const toggleSidebar = useUIStore((s) => s.toggleSidebar)
  const user = useAuthStore((s) => s.user)

  return (
    <header className="flex h-14 items-center justify-between border-b border-plum-100 bg-white/80 px-4 backdrop-blur-sm">
      <button
        onClick={toggleSidebar}
        className="rounded-lg p-2 text-ink-light transition-colors hover:bg-plum-50 hover:text-ink"
      >
        <Menu size={20} />
      </button>

      <div className="flex items-center gap-3">
        {user && (
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-plum-100 text-sm font-medium text-plum-600">
              {user.username[0].toUpperCase()}
            </div>
            <span className="text-sm text-ink-light">{user.username}</span>
          </div>
        )}
      </div>
    </header>
  )
}
