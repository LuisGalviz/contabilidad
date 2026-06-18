export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface User {
  id: string
  email: string
  name: string
  role: 'admin' | 'contador' | 'empresa'
  tenant_id: string | null
  status: string
}

export interface Tenant {
  id: string
  name: string
  slug: string
  plan: 'free' | 'professional' | 'enterprise'
  status: string
  max_clients: number
  owner_email: string
  created_at: string
}

export interface Client {
  id: string
  tenant_id: string
  name: string
  nit: string
  contact_email: string
  contact_name: string
  contact_phone: string
  is_active: boolean
  created_at: string
}

export type ReportType = 'sazon' | 'tlg' | 'mensualizados'
export type ReportStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface ReportFile {
  id: string
  file_type: string
  original_name: string
  storage_key: string
}

export interface Report {
  id: string
  client_id: string
  tenant_id: string
  report_type: ReportType
  period: string
  status: ReportStatus
  error_message: string | null
  source_files: ReportFile[]
  output_files: ReportFile[]
  metadata: Record<string, any>
  created_at: string
  updated_at: string
}

export interface ApiError {
  detail: string
}
