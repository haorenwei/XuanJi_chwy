import type { ApiResponse } from '@/types/api'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

export class ApiError extends Error {
  status: number
  constructor(
    status: number,
    message: string,
  ) {
    super(message)
    this.status = status
  }
}

function getToken(): string | null {
  return localStorage.getItem('token')
}

export async function request<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<ApiResponse<T>> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options?.headers as Record<string, string>) ?? {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({ message: res.statusText }))
    throw new ApiError(res.status, body.message ?? body.detail ?? res.statusText)
  }

  return res.json()
}

export async function streamRequest(
  endpoint: string,
  body: unknown,
  onEvent: (event: Record<string, unknown>) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = getToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${endpoint}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    signal,
  })

  if (!res.ok) {
    const data = await res.json().catch(() => ({ message: res.statusText }))
    throw new ApiError(res.status, data.message ?? data.detail ?? res.statusText)
  }

  const reader = res.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()
  let buffer = ''
  let parseErrors = 0

  const processLine = (line: string) => {
    if (!line.startsWith('data: ')) return
    try {
      const data = JSON.parse(line.slice(6))
      console.log('[SSE] 收到事件:', data.type, data.type === 'done' ? '✓ DONE' : '', data.type === 'collaboration' ? '✓ COLLAB' : '')
      onEvent(data)
      console.log('[SSE] onEvent 回调完成, type:', data.type)
      parseErrors = 0
    } catch (parseErr) {
      parseErrors++
      console.error(`SSE parse error (${parseErrors}):`, parseErr, 'Line:', line.slice(0, 200))
      if (parseErrors > 10) {
        throw new Error('Too many consecutive SSE parse errors')
      }
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // 按 \n\n 分割完整的 SSE 事件，最后一个可能不完整，保留到下次
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''

    for (const part of parts) {
      if (!part.trim()) continue
      for (const line of part.split('\n')) {
        processLine(line)
      }
    }
  }

  // 流结束后处理 buffer 中剩余的数据（防止最后一个事件缺少尾部 \n\n）
  if (buffer.trim()) {
    for (const line of buffer.split('\n')) {
      processLine(line)
    }
  }
}
