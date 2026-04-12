import type { Task } from '@/types/task'
import { request } from './client'

export async function listTasks() {
  return request<Task[]>('/v1/tasks/')
}

export async function getTask(id: number) {
  return request<Task>(`/v1/tasks/${id}`)
}

export function listRunningTasks() {
  return request<Task[]>('/v1/tasks/running')
}

export function cancelTask(id: number) {
  return request<Task>(`/v1/tasks/${id}/cancel`, { method: 'PATCH' })
}

export function restartTask(id: number) {
  return request<Task>(`/v1/tasks/${id}/restart`, { method: 'PATCH' })
}
