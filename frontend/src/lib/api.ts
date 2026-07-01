import axios, { AxiosError } from 'axios'
import type {
  CausationEntry,
  Client,
  ClassificationHistoryEntry,
  ImportBatch,
  MappingRule,
  PUCAccount,
  Report,
  ReportType,
  SupplierInvoice,
  Tenant,
  TokenResponse,
  User,
} from '@/types'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || ''

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

  update: (id: string, data: { economic_activity?: string; ciiu_code?: string }) =>
    api.patch<Client>(`/clients/${id}`, data).then((r) => r.data),
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

export const purchaseApi = {
  listBatches: (params?: { limit?: number; offset?: number }) =>
    api.get<{ items: ImportBatch[]; total: number }>('/purchases/import-batches', { params }).then((r) => r.data),

  getBatch: (id: string) => api.get<ImportBatch>(`/purchases/import-batches/${id}`).then((r) => r.data),

  uploadBatch: (data: { client_id: string; file: File }) => {
    const form = new FormData()
    form.append('client_id', data.client_id)
    form.append('file', data.file)
    return api
      .post<ImportBatch>('/purchases/import-batches', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      .then((r) => r.data)
  },

  listInvoices: (params: { client_id?: string; status?: string; batch_id?: string }) =>
    api.get<{ items: SupplierInvoice[]; total: number }>('/purchases/invoices', { params }).then((r) => r.data),

  getInvoice: (id: string) => api.get<SupplierInvoice>(`/purchases/invoices/${id}`).then((r) => r.data),

  classifyInvoice: (id: string, data: { account_code: string; cost_center_id?: string | null }) =>
    api.post<SupplierInvoice>(`/purchases/invoices/${id}/classify`, data).then((r) => r.data),

  bulkClassify: (data: { invoice_ids: string[]; account_code: string; cost_center_id?: string | null }) =>
    api.post<{ items: SupplierInvoice[]; total: number }>('/purchases/invoices/bulk-classify', data).then((r) => r.data),

  rejectInvoice: (id: string, reason: string) =>
    api.post<SupplierInvoice>(`/purchases/invoices/${id}/reject`, { reason }).then((r) => r.data),

  generateCausation: (data: { client_id: string; period: string; invoice_ids?: string[] }) =>
    api.post('/purchases/causation/generate', { invoice_ids: [], ...data }).then((r) => r.data),

  listCausationEntries: (params: { client_id: string; period?: string }) =>
    api.get<{ items: CausationEntry[]; total: number }>('/purchases/causation', { params }).then((r) => r.data),
}

export const mappingRuleApi = {
  list: (clientId: string) =>
    api.get<{ items: MappingRule[] }>('/purchases/mapping-rules', { params: { client_id: clientId } }).then((r) => r.data),

  history: (ruleId: string) =>
    api
      .get<{ items: ClassificationHistoryEntry[] }>(`/purchases/mapping-rules/${ruleId}/history`)
      .then((r) => r.data),
}

export const pucApi = {
  listAccounts: (params?: { account_class?: string; search?: string }) =>
    api.get<{ items: PUCAccount[] }>('/puc/accounts', { params }).then((r) => r.data),
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
