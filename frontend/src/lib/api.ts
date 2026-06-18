import axios, { AxiosError } from 'axios'
import type { Client, Report, ReportType, Tenant, TokenResponse, User } from '@/types'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  register: (data: { name: string; email: string; password: string; tenant_name: string }) =>
    api.post<TokenResponse>('/auth/register', data).then((r) => r.data),

  login: (data: { email: string; password: string }) =>
    api.post<TokenResponse>('/auth/login', data).then((r) => r.data),

  me: () => api.get<User>('/auth/me').then((r) => r.data),
}

export const tenantApi = {
  getMyTenant: () => api.get<Tenant>('/tenants/me').then((r) => r.data),
}

export const clientApi = {
  list: () => api.get<{ items: Client[]; total: number }>('/clients').then((r) => r.data),

  create: (data: {
    name: string
    nit: string
    contact_email: string
    contact_name?: string
    contact_phone?: string
  }) => api.post<Client>('/clients', data).then((r) => r.data),

  deactivate: (id: string) => api.delete(`/clients/${id}`),
}

export const reportApi = {
  list: (params?: { limit?: number; offset?: number }) =>
    api.get<{ items: Report[]; total: number }>('/reports', { params }).then((r) => r.data),

  get: (id: string) => api.get<Report>(`/reports/${id}`).then((r) => r.data),

  create: (data: {
    client_id: string
    report_type: ReportType
    period?: string
    files: File[]
  }) => {
    const form = new FormData()
    form.append('client_id', data.client_id)
    form.append('report_type', data.report_type)
    form.append('period', data.period ?? '')
    data.files.forEach((f) => form.append('files', f))
    return api
      .post<Report>('/reports', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      .then((r) => r.data)
  },

  downloadUrl: (reportId: string, fileId: string) =>
    `${BASE_URL}/api/v1/reports/${reportId}/download/${fileId}`,
}

export async function downloadFile(reportId: string, fileId: string, fileName: string) {
  const url = reportApi.downloadUrl(reportId, fileId)
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
  const response = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new Error(`Download failed: ${response.status}`)
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objectUrl
  a.download = fileName
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(objectUrl)
}
