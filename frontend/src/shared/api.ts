export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public existingId?: string,
  ) {
    super(message)
  }
}

export const apiBase = (
  import.meta.env.PROD ? '/api' : import.meta.env.VITE_API_BASE_URL || '/api'
).replace(/\/$/, '')

async function response(path: string, options: RequestInit = {}): Promise<Response> {
  let result: Response
  try {
    const headers = new Headers(options.headers)
    if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }
    if (!headers.has('X-QA-Request')) headers.set('X-QA-Request', '1')
    result = await fetch(`${apiBase}${path}`, {
      ...options,
      credentials: 'include',
      headers,
    })
  } catch {
    throw new ApiError('Server tidak terjangkau. Periksa koneksi dan coba kembali.', 0)
  }
  if (!result.ok) {
    const body: unknown = await result.json().catch(() => null)
    const detail =
      body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string'
        ? body.detail
        : 'Permintaan gagal. Silakan coba kembali.'
    const existingId =
      body &&
      typeof body === 'object' &&
      'existing_id' in body &&
      typeof body.existing_id === 'string'
        ? body.existing_id
        : undefined
    if (result.status === 401 && !path.startsWith('/auth/')) {
      window.dispatchEvent(new Event('qa:session-expired'))
    }
    throw new ApiError(detail, result.status, existingId)
  }
  return result
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const result = await response(path, options)
  return result.status === 204 ? (undefined as T) : (result.json() as Promise<T>)
}

export async function apiFile(path: string, options?: RequestInit): Promise<Blob> {
  return (await response(path, options)).blob()
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Terjadi kesalahan. Silakan coba kembali.'
}

export function downloadFile(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
