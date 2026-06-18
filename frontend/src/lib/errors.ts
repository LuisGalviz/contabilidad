export function apiError(e: any): string {
  const detail = e?.response?.data?.detail
  if (!detail) return 'Error inesperado. Intenta de nuevo.'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg ?? JSON.stringify(d)).join(' · ')
  }
  return JSON.stringify(detail)
}
