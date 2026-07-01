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
  economic_activity: string
  ciiu_code: string
  is_active: boolean
  created_at: string
}

export type ReportType = 'sazon' | 'tlg' | 'mensualizados' | 'purchases_general' | 'purchases_sector'
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

// ─── Purchases / causación DIAN ─────────────────────────────────────────────

export type ImportBatchStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface ImportBatch {
  id: string
  client_id: string
  tenant_id: string
  original_name: string
  status: ImportBatchStatus
  total_rows: number
  new_invoices: number
  duplicate_invoices: number
  error_rows: number
  error_message: string | null
  created_at: string
  updated_at: string
}

export type InvoiceStatus = 'pending_review' | 'classified' | 'caused' | 'rejected' | 'error'
export type ClassificationSource = 'auto_high_confidence' | 'auto_low_confidence' | 'manual'

export interface SupplierInvoice {
  id: string
  client_id: string
  import_batch_id: string
  cufe: string
  supplier_nit: string
  supplier_name: string
  issue_date: string
  concept_description: string
  subtotal: number
  vat_amount: number
  total_amount: number
  status: InvoiceStatus
  suggested_account_code: string | null
  suggested_cost_center_id: string | null
  suggested_confidence: number
  classification_source: ClassificationSource | null
  final_account_code: string | null
  final_cost_center_id: string | null
  rejection_reason: string | null
}

export interface CausationEntryLine {
  account_code: string
  debit: number
  credit: number
  description: string
  cost_center_id: string | null
}

export interface CausationEntry {
  id: string
  client_id: string
  invoice_id: string
  entry_date: string
  status: string
  external_reference: string | null
  lines: CausationEntryLine[]
}

export interface MappingRule {
  id: string
  client_id: string
  supplier_nit: string
  concept_keywords: string[]
  account_code: string
  cost_center_id: string | null
  confidence: number
  times_confirmed: number
  times_corrected: number
  is_active: boolean
}

export interface ClassificationHistoryEntry {
  id: string
  invoice_id: string
  action: 'auto_suggested' | 'confirmed' | 'corrected' | 'rejected'
  account_code_before: string | null
  account_code_after: string | null
  rule_id: string | null
  user_id: string | null
  created_at: string
}

export interface PUCAccount {
  code: string
  name: string
  account_class: string
  requires_cost_center: boolean
}

export const SECTOR_KEYS = ['restaurante', 'generico'] as const
export type SectorKey = (typeof SECTOR_KEYS)[number]
