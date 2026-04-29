export async function apiFetch<T>(
  path: string,
  params?: Record<string, unknown>,
  method = 'GET',
  timeoutMs = 15_000,
): Promise<T> {
  const url = new URL(path, window.location.origin)
  if (params && method === 'GET') {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === '') continue
      if (Array.isArray(value)) {
        value.forEach((v) => url.searchParams.append(key, String(v)))
      } else {
        url.searchParams.set(key, String(value))
      }
    }
  }

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(url.toString(), { method, signal: controller.signal })
    if (!res.ok) throw new Error(`API error ${res.status}: ${url.pathname}`)
    return res.json()
  } finally {
    clearTimeout(timer)
  }
}
