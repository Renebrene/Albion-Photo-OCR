// Thin wrapper around the read-only PhotoBAse API.
// In dev, /api is proxied to the FastAPI backend by Vite.

const BASE = import.meta.env.VITE_API_BASE || '/api'

export async function fetchPhotos({ limit = 50, cursor = null, q = null } = {}) {
  const params = new URLSearchParams()
  params.set('limit', String(limit))
  if (cursor) params.set('cursor', cursor)
  if (q) params.set('q', q)

  const response = await fetch(`${BASE}/v1/photos?${params.toString()}`)

  if (!response.ok) {
    throw new Error(`API error ${response.status}`)
  }

  return response.json()
}

export function previewUrl(photoId, size = 'small') {
  return `${BASE}/v1/photos/${photoId}/previews/${size}`
}
