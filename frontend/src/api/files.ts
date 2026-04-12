import { request } from './client'

interface FileEntry {
  name: string
  is_dir: boolean
  size: number | null
  path: string
}

export async function browseDirectory(path?: string) {
  const query = path ? `?path=${encodeURIComponent(path)}` : ''
  return request<{ current: string; entries: FileEntry[] }>(`/v1/files/browse${query}`)
}
