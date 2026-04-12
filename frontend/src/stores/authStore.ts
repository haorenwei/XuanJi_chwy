import { create } from 'zustand'
import type { User } from '@/types/user'
import * as authApi from '@/api/auth'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => void
  loadUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: !!localStorage.getItem('token'),

  login: async (username, password) => {
    const res = await authApi.login(username, password)
    if (res.data) {
      localStorage.setItem('token', res.data.token)
      set({ user: res.data.user, token: res.data.token, isAuthenticated: true })
    }
  },

  register: async (username, email, password) => {
    const res = await authApi.register(username, email, password)
    if (res.data) {
      localStorage.setItem('token', res.data.token)
      set({ user: res.data.user, token: res.data.token, isAuthenticated: true })
    }
  },

  logout: () => {
    localStorage.removeItem('token')
    set({ user: null, token: null, isAuthenticated: false })
  },

  loadUser: async () => {
    try {
      const res = await authApi.getMe()
      if (res.data) {
        set({ user: res.data, isAuthenticated: true })
      }
    } catch {
      localStorage.removeItem('token')
      set({ user: null, token: null, isAuthenticated: false })
    }
  },
}))
