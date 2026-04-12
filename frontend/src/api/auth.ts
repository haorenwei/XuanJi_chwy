import type { User } from '@/types/user'
import { request } from './client'

export async function login(username: string, password: string) {
  return request<{ token: string; user: User }>('/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export async function register(username: string, email: string, password: string) {
  return request<{ token: string; user: User }>('/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, email, password }),
  })
}

export async function getMe() {
  return request<User>('/v1/auth/me')
}
