'use client'

import React, { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { useTranslations } from 'next-intl'
import { reportApi, downloadFile } from '@/lib/api'
import { ArrowLeft, Download, FileSpreadsheet, FileText, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

// ─── helpers ────────────────────────────────────────────────────────────────

function cop(v: number) {
  if (!v && v !== 0) return '—'
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v)
}
function pct(v: number) {
  if (!v && v !== 0) return '—'
  return `${(v * 100).toFixed(1)} %`
}
function num(v: number) {
  return new Intl.NumberFormat('es-CO').format(v)
}

const COLORS = ['#0B6B57', '#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']

// ─── small components ────────────────────────────────────────────────────────

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-lg font-bold text-gray-900 leading-tight">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="font-semibold text-gray-800 text-sm mb-3 mt-6">{children}</h3>
}

function DataTable({ rows, cols, headers }: {
  rows: Record<string, any>[]
  cols: string[]
  headers?: string[]
}) {
  const tCommon = useTranslations('common')
  const displayHeaders = headers ?? cols
  if (!rows || rows.length === 0) return <p className="text-xs text-gray-400">{tCommon('noData')}</p>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-gray-200">
            {displayHeaders.map((h, i) => (
              <th key={cols[i]} className="text-left py-2 px-3 font-medium text-gray-600 whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
              {cols.map((c) => (
                <td key={c} className="py-2 px-3 text-gray-700 whitespace-nowrap">{row[c] ?? '—'}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TabBar({ tabs, active, onChange }: {
  tabs: { key: string; label: string }[]
  active: string
  onChange: (k: string) => void
}) {
  return (
    <div className="flex gap-1 border-b border-gray-200 mb-6 overflow-x-auto">
      {tabs.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={`px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
            active === key
              ? 'border-[#0B6B57] text-[#0B6B57]'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

function DownloadBtn({ reportId, file }: { reportId: string; file: { id: string; file_type: string; original_name: string } }) {
  const [loading, setLoading] = useState(false)
  const Icon = file.file_type.includes('pdf') ? FileText : FileSpreadsheet

  const handleDownload = async () => {
    setLoading(true)
    try {
      await downloadFile(reportId, file.id, file.original_name)
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={handleDownload}
      disabled={loading}
      className="inline-flex items-center gap-2 border border-gray-300 rounded-lg px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50"
    >
      <Icon size={16} />
      {file.original_name}
      {loading ? <span className="w-3 h-3 border border-gray-400 border-t-transparent rounded-full animate-spin" /> : <Download size={14} />}
    </button>
  )
}

// ─── Filters ─────────────────────────────────────────────────────────────────

function MultiSelect({ label, options, selected, onChange }: {
  label: string
  options: string[]
  selected: Set<string>
  onChange: (s: Set<string>) => void
}) {
  const tCommon = useTranslations('common')
  const [open, setOpen] = useState(false)
  const ref = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    function handle(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [])

  const toggle = (v: string) => {
    const next = new Set(selected)
    next.has(v) ? next.delete(v) : next.add(v)
    onChange(next)
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 border border-gray-300 rounded-lg px-3 py-1.5 text-xs text-gray-700 bg-white hover:bg-gray-50 whitespace-nowrap"
      >
        <span className="font-medium text-gray-500">{label}:</span>
        <span>{selected.size === 0 ? tCommon('all') : tCommon('selected', { count: selected.size })}</span>
        <span className="text-gray-400">▾</span>
      </button>
      {open && (
        <div className="absolute z-20 mt-1 bg-white border border-gray-200 rounded-xl shadow-lg min-w-[180px] py-1 max-h-60 overflow-y-auto">
          <button
            onClick={() => onChange(new Set())}
            className="w-full text-left px-3 py-1.5 text-xs hover:bg-gray-50 font-medium text-[#0B6B57]"
          >
            {tCommon('all')}
          </button>
          {options.map((o) => (
            <label key={o} className="flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-gray-50 cursor-pointer">
              <input type="checkbox" checked={selected.has(o)} onChange={() => toggle(o)} className="accent-[#0B6B57]" />
              {o}
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Sazón View ──────────────────────────────────────────────────────────────

function SazonView({ meta, reportId, outputFiles }: { meta: any; reportId: string; outputFiles: any[] }) {
  const t = useTranslations('reportDetail')
  const tCommon = useTranslations('common')

  const [tab, setTab] = useState('summary')

  const tabs = [
    { key: 'summary', label: t('tabs.summary') },
    { key: 'monthly', label: t('tabs.monthly') },
    { key: 'payments', label: t('tabs.payments') },
    { key: 'sellers', label: t('tabs.sellers') },
    { key: 'clients', label: t('tabs.clients') },
    { key: 'tips', label: t('tabs.tips') },
    { key: 'courtesies', label: t('tabs.courtesies') },
    { key: 'expenses', label: t('tabs.expenses') },
    { key: 'downloads', label: t('tabs.downloads') },
  ]

  // raw data
  const allMonthly: any[] = meta.monthly ?? []
  const allSellers: any[] = meta.sellers ?? []
  const allClients: any[] = meta.clients ?? []
  const allPayments: any[] = meta.payments ?? []
  const allTips: any[] = meta.tips ?? []
  const allOperating: any[] = meta.operating ?? []
  const allCourtesyMonth: any[] = meta.courtesy_by_month ?? []
  const providers: any[] = meta.provider_summary ?? []

  // filter options
  const monthOptions = allMonthly.map((r: any) => r['Mes']).filter(Boolean)
  const sellerOptions = allSellers.map((r: any) => r['Vendedor']).filter(Boolean)
  const clientOptions = allClients.map((r: any) => r['Cliente']).filter(Boolean)
  const paymentOptions = allPayments.map((r: any) => r['Forma de pago']).filter(Boolean)

  const [selMonths, setSelMonths] = useState<Set<string>>(new Set())
  const [selSellers, setSelSellers] = useState<Set<string>>(new Set())
  const [selClients, setSelClients] = useState<Set<string>>(new Set())
  const [selPayments, setSelPayments] = useState<Set<string>>(new Set())

  const flt = <T extends Record<string, any>>(arr: T[], key: string, sel: Set<string>) =>
    sel.size === 0 ? arr : arr.filter((r) => sel.has(r[key]))

  const monthly = flt(allMonthly, 'Mes', selMonths)
  const sellers = flt(allSellers, 'Vendedor', selSellers)
  const clients = flt(allClients, 'Cliente', selClients)
  const payments = flt(allPayments, 'Forma de pago', selPayments)
  const tips = flt(allTips, 'Mes', selMonths)
  const operating = flt(allOperating, 'Mes', selMonths)
  const courtesyMonth = flt(allCourtesyMonth, 'Mes', selMonths)
  const courtesySeller = flt(meta.courtesy_by_seller ?? [], 'Vendedor', selSellers)

  const sumField = (arr: any[], field: string) => arr.reduce((s: number, r: any) => s + (Number(r[field]) || 0), 0)
  const ventas = sumField(monthly, 'Ventas netas')
  const ventas_brutas = sumField(monthly, 'Ventas brutas')
  const gastos = sumField(monthly, 'Gastos')
  const cortesias = sumField(monthly, 'Cortesías')
  const propinas = sumField(tips, 'Propinas')
  const recaudo = sumField(monthly, 'Recaudo real')
  const utilidad = ventas - gastos
  const margen = ventas ? utilidad / ventas : 0
  const facturas = sumField(monthly, 'Número de facturas')
  const ticket = facturas ? ventas / facturas : 0
  const courtesy_pct = ventas_brutas ? cortesias / ventas_brutas : 0

  const kpis = [
    { label: t('sazon.kpis.grossSales'), value: cop(ventas_brutas) },
    { label: t('sazon.kpis.courtesies'), value: cop(cortesias) },
    { label: t('sazon.kpis.netSales'), value: cop(ventas) },
    { label: t('sazon.kpis.collected'), value: cop(recaudo) },
    { label: t('sazon.kpis.courtesyPct'), value: pct(courtesy_pct) },
    { label: t('sazon.kpis.totalExpenses'), value: cop(gastos) },
    { label: t('sazon.kpis.estimatedProfit'), value: cop(utilidad) },
    { label: t('sazon.kpis.estimatedMargin'), value: pct(margen) },
    { label: t('sazon.kpis.totalTips'), value: cop(propinas) },
    { label: t('sazon.kpis.invoiceCount'), value: num(facturas) },
    { label: t('sazon.kpis.avgTicket'), value: cop(ticket) },
  ]

  // Filtered KPIs for sub-tabs (recalculated from filtered arrays)
  const filteredTipsTotal = sumField(tips, 'Propinas')
  const filteredCourtesiesTotal = sumField(courtesyMonth, 'Cortesías')
  const filteredCourtesyPct = ventas_brutas ? filteredCourtesiesTotal / ventas_brutas : 0
  const filteredTopCourtesyMonth = [...courtesyMonth]
    .sort((a, b) => (b['Cortesías'] ?? 0) - (a['Cortesías'] ?? 0))[0]?.['Mes'] ?? '—'
  const filteredTopExpenseMonth = [...operating]
    .sort((a, b) => (b['Gastos'] ?? 0) - (a['Gastos'] ?? 0))[0]?.['Mes'] ?? '—'
  const filteredExpenseRatio = ventas ? gastos / ventas : 0

  const hasFilters = selMonths.size > 0 || selSellers.size > 0 || selClients.size > 0 || selPayments.size > 0
  const summary = meta.summary ?? {}

  return (
    <div>
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2 mb-5 p-3 bg-gray-50 rounded-xl border border-gray-200">
        <span className="text-xs font-semibold text-gray-500 mr-1">{t('filters.label')}</span>
        <MultiSelect label={t('filters.month')} options={monthOptions} selected={selMonths} onChange={setSelMonths} />
        <MultiSelect label={t('filters.seller')} options={sellerOptions} selected={selSellers} onChange={setSelSellers} />
        <MultiSelect label={t('filters.payment')} options={paymentOptions} selected={selPayments} onChange={setSelPayments} />
        <MultiSelect label={t('filters.client')} options={clientOptions} selected={selClients} onChange={setSelClients} />
        {hasFilters && (
          <button
            onClick={() => { setSelMonths(new Set()); setSelSellers(new Set()); setSelClients(new Set()); setSelPayments(new Set()) }}
            className="text-xs text-red-500 hover:text-red-700 ml-1"
          >
            {tCommon('clearFilters')}
          </button>
        )}
      </div>

      {meta.interpretation && (
        <div className="bg-[#f0faf7] border border-[#0B6B57]/20 rounded-xl p-4 mb-6 text-sm text-gray-700">
          {meta.interpretation}
        </div>
      )}

      <TabBar tabs={tabs} active={tab} onChange={setTab} />

      {tab === 'summary' && (
        <div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            {kpis.map((k: any) => <KpiCard key={k.label} label={k.label} value={k.value} />)}
          </div>

          <SectionTitle>{t('sazon.sections.operatingResult')}</SectionTitle>
          <DataTable
            rows={operating.map((r: any) => ({
              'Mes': r['Mes'],
              'Ventas': typeof r['Ventas'] === 'number' ? cop(r['Ventas']) : r['Ventas'],
              'Gastos': typeof r['Gastos'] === 'number' ? cop(r['Gastos']) : r['Gastos'],
              'Utilidad estimada': typeof r['Utilidad estimada'] === 'number' ? cop(r['Utilidad estimada']) : r['Utilidad estimada'],
              'Margen estimado': typeof r['Margen estimado'] === 'number' ? pct(r['Margen estimado']) : r['Margen estimado'],
            }))}
            cols={['Mes', 'Ventas', 'Gastos', 'Utilidad estimada', 'Margen estimado']}
            headers={[
              t('sazon.cols.month'),
              t('sazon.kpis.netSales'),
              t('sazon.kpis.totalExpenses'),
              t('sazon.kpis.estimatedProfit'),
              t('sazon.kpis.estimatedMargin'),
            ]}
          />

          {operating.length > 0 && (
            <>
              <SectionTitle>{t('sazon.sections.salesVsExpenses')}</SectionTitle>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={operating} margin={{ left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="Mes" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `$${(v / 1_000_000).toFixed(1)}M`} />
                  <Tooltip formatter={(v: any) => cop(v)} />
                  <Legend />
                  <Bar dataKey="Ventas" fill="#0B6B57" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Gastos" fill="#ef4444" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>

              <SectionTitle>{t('sazon.sections.profitByMonth')}</SectionTitle>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={operating}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="Mes" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `$${(v / 1_000_000).toFixed(1)}M`} />
                  <Tooltip formatter={(v: any) => cop(v)} />
                  <Line type="monotone" dataKey="Utilidad estimada" stroke="#0B6B57" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </>
          )}
        </div>
      )}

      {tab === 'monthly' && (
        <div>
          <DataTable
            rows={monthly.map((r: any) => ({
              'Mes': r['Mes'],
              'Ventas brutas': cop(r['Ventas brutas']),
              'Cortesías': cop(r['Cortesías']),
              'Ventas netas': cop(r['Ventas netas']),
              'Recaudo real': cop(r['Recaudo real']),
              'Propinas': cop(r['Propinas']),
              'Gastos': cop(r['Gastos']),
              'Utilidad estimada': cop(r['Utilidad estimada']),
              'Ticket promedio': cop(r['Ticket promedio']),
              'N° facturas': num(r['Número de facturas']),
            }))}
            cols={['Mes', 'Ventas brutas', 'Cortesías', 'Ventas netas', 'Recaudo real', 'Propinas', 'Gastos', 'Utilidad estimada', 'Ticket promedio', 'N° facturas']}
            headers={[
              t('sazon.cols.month'),
              t('sazon.cols.grossSales'),
              t('sazon.cols.courtesies'),
              t('sazon.cols.netSales'),
              t('sazon.cols.collected'),
              t('sazon.cols.tips'),
              t('sazon.cols.expenses'),
              t('sazon.cols.estimatedProfit'),
              t('sazon.cols.avgTicket'),
              t('sazon.cols.invoiceCount'),
            ]}
          />
        </div>
      )}

      {tab === 'payments' && (
        <div>
          <div className="grid grid-cols-2 gap-6 mb-4">
            <div>
              <SectionTitle>{t('sazon.sections.paymentDist')}</SectionTitle>
              <DataTable
                rows={payments.map((r: any) => ({
                  'Forma de pago': r['Forma de pago'],
                  'Valor': cop(r['Valor']),
                  'Participación %': pct(r['Participación %']),
                }))}
                cols={['Forma de pago', 'Valor', 'Participación %']}
                headers={[t('sazon.cols.paymentMethod'), t('sazon.cols.value'), t('sazon.cols.participation')]}
              />
            </div>
            {payments.length > 0 && (
              <div>
                <SectionTitle>{t('sazon.sections.paymentChart')}</SectionTitle>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={payments} dataKey="Valor" nameKey="Forma de pago" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}>
                      {payments.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip formatter={(v: any) => cop(v)} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'sellers' && (
        <div>
          {sellers.length > 0 && (
            <>
              <SectionTitle>{t('sazon.sections.sellerChart')}</SectionTitle>
              <ResponsiveContainer width="100%" height={Math.max(180, sellers.length * 40)}>
                <BarChart data={sellers} layout="vertical" margin={{ left: 80 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => `$${(v / 1_000_000).toFixed(1)}M`} />
                  <YAxis type="category" dataKey="Vendedor" tick={{ fontSize: 11 }} width={80} />
                  <Tooltip formatter={(v: any) => cop(v)} />
                  <Bar dataKey="Total ventas" fill="#0B6B57" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </>
          )}
          <SectionTitle>{t('sazon.sections.sellerDetail')}</SectionTitle>
          <DataTable
            rows={sellers.map((r: any) => ({
              'Vendedor': r['Vendedor'],
              'Total ventas': cop(r['Total ventas']),
              'Total valor neto': cop(r['Total valor neto']),
              'Total propinas': cop(r['Total propinas']),
              'Total cortesías': cop(r['Total cortesías']),
              'Número de facturas': num(r['Número de facturas']),
              'Ticket promedio': cop(r['Ticket promedio']),
            }))}
            cols={['Vendedor', 'Total ventas', 'Total valor neto', 'Total propinas', 'Total cortesías', 'Número de facturas', 'Ticket promedio']}
            headers={[
              t('sazon.cols.seller'),
              t('sazon.cols.totalSales'),
              t('sazon.cols.netValue'),
              t('sazon.cols.tips'),
              t('sazon.cols.totalCourtesies'),
              t('sazon.cols.numInvoices'),
              t('sazon.cols.avgTicket'),
            ]}
          />
        </div>
      )}

      {tab === 'clients' && (
        <div>
          <SectionTitle>{t('sazon.sections.topClients')}</SectionTitle>
          <DataTable
            rows={clients.map((r: any) => ({
              'Cliente': r['Cliente'],
              'Número de compras': num(r['Número de compras']),
              'Total vendido': cop(r['Total vendido']),
              'Última fecha de compra': r['Última fecha de compra'],
              'Ticket promedio': cop(r['Ticket promedio']),
            }))}
            cols={['Cliente', 'Número de compras', 'Total vendido', 'Última fecha de compra', 'Ticket promedio']}
            headers={[
              t('sazon.cols.client'),
              t('sazon.cols.numPurchases'),
              t('sazon.cols.totalSold'),
              t('sazon.cols.lastPurchase'),
              t('sazon.cols.avgTicket'),
            ]}
          />
        </div>
      )}

      {tab === 'tips' && (
        <div>
          <div className="grid grid-cols-3 gap-3 mb-6">
            <KpiCard label={t('sazon.sections.totalTips')} value={cop(filteredTipsTotal)} />
            <KpiCard label={t('sazon.sections.tipsByCard')} value={summary.tips_tarjeta ?? '—'} />
            <KpiCard label={t('sazon.sections.tipsCash')} value={summary.tips_resto ?? '—'} />
          </div>
          {tips.length > 0 && (
            <>
              <SectionTitle>{t('sazon.sections.tipsByMonth')}</SectionTitle>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={tips}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="Mes" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `$${(v / 1_000_000).toFixed(1)}M`} />
                  <Tooltip formatter={(v: any) => cop(v)} />
                  <Bar dataKey="Propinas" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </>
          )}
        </div>
      )}

      {tab === 'courtesies' && (
        <div>
          <div className="grid grid-cols-3 gap-3 mb-6">
            <KpiCard label={t('sazon.sections.totalCourtesies')} value={cop(filteredCourtesiesTotal)} />
            <KpiCard label={t('sazon.sections.courtesyPct')} value={pct(filteredCourtesyPct)} />
            <KpiCard label={t('sazon.sections.topCourtesyMonth')} value={filteredTopCourtesyMonth} />
          </div>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <SectionTitle>{t('sazon.sections.courtesyByMonth')}</SectionTitle>
              <DataTable rows={courtesyMonth} cols={['Mes', 'Cortesías']} headers={[t('sazon.cols.month'), t('sazon.cols.courtesies')]} />
            </div>
            <div>
              <SectionTitle>{t('sazon.sections.courtesyBySeller')}</SectionTitle>
              <DataTable rows={courtesySeller} cols={['Vendedor', 'Cortesías']} headers={[t('sazon.cols.seller'), t('sazon.cols.courtesies')]} />
            </div>
          </div>
        </div>
      )}

      {tab === 'expenses' && (
        <div>
          <div className="grid grid-cols-3 gap-3 mb-6">
            <KpiCard label={t('sazon.sections.totalExpenses')} value={cop(gastos)} />
            <KpiCard label={t('sazon.sections.topExpenseMonth')} value={filteredTopExpenseMonth} />
            <KpiCard label={t('sazon.sections.expenseRatio')} value={pct(filteredExpenseRatio)} />
          </div>
          {providers.length > 0 && (
            <>
              <SectionTitle>{t('sazon.sections.topProviders')}</SectionTitle>
              <ResponsiveContainer width="100%" height={Math.max(180, providers.length * 36)}>
                <BarChart data={providers} layout="vertical" margin={{ left: 140 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => `$${(v / 1_000_000).toFixed(1)}M`} />
                  <YAxis type="category" dataKey="Proveedor o concepto" tick={{ fontSize: 10 }} width={140} />
                  <Tooltip formatter={(v: any) => cop(v)} />
                  <Bar dataKey="Gastos" fill="#ef4444" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
              <SectionTitle>{t('sazon.sections.expenseDetail')}</SectionTitle>
              <DataTable
                rows={providers.map((r: any) => ({ 'Proveedor o concepto': r['Proveedor o concepto'], 'Gastos': cop(r['Gastos']) }))}
                cols={['Proveedor o concepto', 'Gastos']}
                headers={[t('sazon.cols.provider'), t('sazon.cols.expenses')]}
              />
            </>
          )}
        </div>
      )}

      {tab === 'downloads' && (
        <div className="flex flex-wrap gap-3 pt-2">
          {outputFiles.map((f) => <DownloadBtn key={f.id} reportId={reportId} file={f} />)}
        </div>
      )}
    </div>
  )
}

// ─── TLG View ─────────────────────────────────────────────────────────────────

function TlgView({ meta, reportId, outputFiles }: { meta: any; reportId: string; outputFiles: any[] }) {
  const t = useTranslations('reportDetail')
  const [tab, setTab] = useState('validation')

  const tabs = [
    { key: 'validation', label: t('tabs.validation') },
    { key: 'balanceSheet', label: t('tabs.balanceSheet') },
    { key: 'incomeStatement', label: t('tabs.incomeStatement') },
    { key: 'management', label: t('tabs.management') },
    { key: 'downloads', label: t('tabs.downloads') },
  ]

  const metrics = meta.metrics ?? {}
  const balance: any[] = meta.balance ?? []
  const incomeStatement: any[] = meta.income_statement ?? []
  const validation: any[] = meta.validation_rows ?? []

  const kpiCards = [
    { label: t('tlg.kpis.totalAssets'), value: cop(metrics.total_activo) },
    { label: t('tlg.kpis.totalLiabilities'), value: cop(metrics.total_pasivo) },
    { label: t('tlg.kpis.totalEquity'), value: cop(metrics.total_patrimonio) },
    { label: t('tlg.kpis.revenue'), value: cop(metrics.total_ingresos) },
    { label: t('tlg.kpis.costs'), value: cop(metrics.total_costos) },
    { label: t('tlg.kpis.expenses'), value: cop(metrics.total_gastos) },
    { label: t('tlg.kpis.result'), value: cop(metrics.resultado) },
    { label: t('tlg.kpis.difference'), value: cop(Math.abs(metrics.diferencia_cuadre ?? 0)) },
  ]

  const balanceCols = ['CODIGO_CUENTA', 'NOMBRE_CUENTA', 'CLASIFICACION', 'SALDO_INICIAL', 'MOVIMIENTO_DEBITO', 'MOVIMIENTO_CREDITO', 'SALDO_FINAL']
  const balanceHeaders = [
    t('tlg.cols.code'), t('tlg.cols.name'), t('tlg.cols.classification'),
    t('tlg.cols.openingBalance'), t('tlg.cols.debit'), t('tlg.cols.credit'), t('tlg.cols.finalBalance'),
  ]

  const fmtBalance = (rows: any[]) => rows.map((r: any) => ({
    ...r,
    SALDO_INICIAL: cop(r.SALDO_INICIAL),
    MOVIMIENTO_DEBITO: cop(r.MOVIMIENTO_DEBITO),
    MOVIMIENTO_CREDITO: cop(r.MOVIMIENTO_CREDITO),
    SALDO_FINAL: cop(r.SALDO_FINAL),
  }))

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1">
          <p className="font-semibold text-gray-900">{meta.empresa}</p>
          <p className="text-sm text-gray-500">{t('tlg.nit', { nit: meta.nit, period: meta.periodo })}</p>
        </div>
        {meta.cuadre_ok
          ? <span className="flex items-center gap-1 text-green-700 text-sm"><CheckCircle size={16} /> {t('tlg.cuadreOk')}</span>
          : <span className="flex items-center gap-1 text-yellow-600 text-sm"><AlertTriangle size={16} /> {t('tlg.cuadreWarn')}</span>
        }
      </div>

      <TabBar tabs={tabs} active={tab} onChange={setTab} />

      {tab === 'validation' && (
        <div>
          <DataTable
            rows={validation}
            cols={['Validación', 'Resultado']}
            headers={[t('tlg.cols.validation'), t('tlg.cols.result')]}
          />
          {!meta.cuadre_ok && (
            <p className="mt-3 text-sm text-yellow-700 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              {t('tlg.cuadreError')}
            </p>
          )}
        </div>
      )}

      {tab === 'balanceSheet' && (
        <div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            {kpiCards.slice(0, 4).map((k) => <KpiCard key={k.label} {...k} />)}
          </div>
          <DataTable rows={fmtBalance(balance.filter((r: any) => ['1','2','3'].includes(r.CLASE)))} cols={balanceCols} headers={balanceHeaders} />
        </div>
      )}

      {tab === 'incomeStatement' && (
        <div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            {kpiCards.slice(4).map((k) => <KpiCard key={k.label} {...k} />)}
          </div>
          <DataTable rows={fmtBalance(incomeStatement)} cols={balanceCols} headers={balanceHeaders} />
        </div>
      )}

      {tab === 'management' && (
        <div>
          <div className="bg-[#f0faf7] border border-[#0B6B57]/20 rounded-xl p-4 text-sm text-gray-700">
            {meta.management_text}
          </div>
        </div>
      )}

      {tab === 'downloads' && (
        <div className="flex flex-wrap gap-3 pt-2">
          {outputFiles.map((f) => <DownloadBtn key={f.id} reportId={reportId} file={f} />)}
        </div>
      )}
    </div>
  )
}

// ─── Mensualizados View ───────────────────────────────────────────────────────

function MensualizadosView({ meta, reportId, outputFiles }: { meta: any; reportId: string; outputFiles: any[] }) {
  const t = useTranslations('reportDetail')
  const [tab, setTab] = useState('managerDashboard')

  const tabs = [
    { key: 'managerDashboard', label: t('tabs.managerDashboard') },
    { key: 'financialStatements', label: t('tabs.financialStatements') },
    { key: 'thirdParty', label: t('tabs.thirdParty') },
    { key: 'downloads', label: t('tabs.downloads') },
  ]

  const exec = meta.exec_summary ?? {}
  const monthlyMetrics: any[] = (meta.monthly_metrics ?? []).filter((m: any) => m.Tipo === 'Mensual')
  const periods: any[] = meta.periods ?? []
  const receivables: any[] = meta.receivables ?? []
  const payables: any[] = meta.payables ?? []
  const activity: any[] = meta.activity ?? []

  const trendData = monthlyMetrics.map((m: any) => ({
    Periodo: m['Periodo'],
    Ventas: m['Ventas'],
    'Utilidad operacional': m['Utilidad operacional'],
    Resultado: m['Resultado'],
  }))
  const marginData = monthlyMetrics.map((m: any) => {
    const v = m['Ventas'] || 1
    return {
      Periodo: m['Periodo'],
      'Margen bruto': m['Utilidad bruta'] / v,
      'Margen operacional': m['Utilidad operacional'] / v,
      'Margen neto': m['Resultado'] / v,
    }
  })

  return (
    <div>
      <p className="text-sm text-gray-500 mb-4">
        {t('mensualizados.base', { source: meta.source_name, period: meta.last_period })}
      </p>

      <TabBar tabs={tabs} active={tab} onChange={setTab} />

      {tab === 'managerDashboard' && (
        <div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            <KpiCard label={t('mensualizados.kpis.sales')} value={cop(exec.Ventas)} />
            <KpiCard label={t('mensualizados.kpis.grossProfit')} value={cop(exec['Utilidad bruta'])} sub={pct(exec['Margen bruto'])} />
            <KpiCard label={t('mensualizados.kpis.operatingProfit')} value={cop(exec['Utilidad operacional'])} sub={pct(exec['Margen operacional'])} />
            <KpiCard label={t('mensualizados.kpis.netResult')} value={cop(exec['Resultado neto'])} sub={pct(exec['Margen neto'])} />
            <KpiCard label={t('mensualizados.kpis.ebitda')} value={cop(exec.EBITDA)} />
            <KpiCard label={t('mensualizados.kpis.currentRatio')} value={exec['Razón corriente'] ? exec['Razón corriente'].toFixed(2) : '—'} />
            <KpiCard label={t('mensualizados.kpis.leverage')} value={pct(exec.Endeudamiento)} />
            <KpiCard label={t('mensualizados.kpis.workingCapital')} value={cop(exec['Capital de trabajo'])} />
          </div>

          {trendData.length > 0 && (
            <>
              <SectionTitle>{t('mensualizados.sections.trend')}</SectionTitle>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="Periodo" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `$${(v / 1_000_000).toFixed(0)}M`} />
                  <Tooltip formatter={(v: any) => cop(v)} />
                  <Legend />
                  <Line type="monotone" dataKey="Ventas" stroke="#0B6B57" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="Utilidad operacional" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="Resultado" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>

              <SectionTitle>{t('mensualizados.sections.margins')}</SectionTitle>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={marginData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="Periodo" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                  <Tooltip formatter={(v: any) => pct(v)} />
                  <Legend />
                  <Line type="monotone" dataKey="Margen bruto" stroke="#0B6B57" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="Margen operacional" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="Margen neto" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </>
          )}

          {monthlyMetrics.length > 0 && (
            <>
              <SectionTitle>{t('mensualizados.sections.monthlyIndicators')}</SectionTitle>
              <DataTable
                rows={monthlyMetrics.map((m: any) => ({
                  'Periodo': m['Periodo'],
                  'Ventas': cop(m['Ventas']),
                  'Utilidad bruta': cop(m['Utilidad bruta']),
                  'Utilidad operacional': cop(m['Utilidad operacional']),
                  'Resultado': cop(m['Resultado']),
                  'Activos': cop(m['Activos']),
                  'Pasivos': cop(m['Pasivos']),
                  'Diferencia de cuadre': cop(m['Diferencia de cuadre']),
                }))}
                cols={['Periodo', 'Ventas', 'Utilidad bruta', 'Utilidad operacional', 'Resultado', 'Activos', 'Pasivos', 'Diferencia de cuadre']}
                headers={[
                  t('mensualizados.cols.period'),
                  t('mensualizados.cols.sales'),
                  t('mensualizados.cols.grossProfit'),
                  t('mensualizados.cols.operatingProfit'),
                  t('mensualizados.cols.result'),
                  t('mensualizados.cols.assets'),
                  t('mensualizados.cols.liabilities'),
                  t('mensualizados.cols.diff'),
                ]}
              />
            </>
          )}
        </div>
      )}

      {tab === 'financialStatements' && (
        <div>
          <SectionTitle>{t('mensualizados.sections.processingControl')}</SectionTitle>
          <DataTable rows={periods} cols={periods.length > 0 ? Object.keys(periods[0]) : []} />
        </div>
      )}

      {tab === 'thirdParty' && (
        <div>
          <div className="grid grid-cols-3 gap-3 mb-6">
            <KpiCard label={t('mensualizados.sections.receivables')} value={cop(receivables.reduce((s: number, r: any) => s + (r.Saldo ?? 0), 0))} />
            <KpiCard label={t('mensualizados.sections.payables')} value={cop(payables.reduce((s: number, r: any) => s + (r.Saldo ?? 0), 0))} />
            <KpiCard label={t('mensualizados.sections.thirdPartyCount')} value={num(activity.length)} />
          </div>

          {receivables.length > 0 && (
            <>
              <SectionTitle>{t('mensualizados.sections.receivablesChart')}</SectionTitle>
              <ResponsiveContainer width="100%" height={Math.max(150, receivables.length * 36)}>
                <BarChart data={receivables.slice(0, 10)} layout="vertical" margin={{ left: 120 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => `$${(v / 1_000_000).toFixed(1)}M`} />
                  <YAxis type="category" dataKey="Tercero" tick={{ fontSize: 10 }} width={120} />
                  <Tooltip formatter={(v: any) => cop(v)} />
                  <Bar dataKey="Saldo" fill="#0B6B57" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
              <DataTable
                rows={receivables.map((r: any) => ({ 'Tercero': r['Tercero'], 'Saldo': cop(r['Saldo']) }))}
                cols={['Tercero', 'Saldo']}
                headers={[t('mensualizados.cols.third'), t('mensualizados.cols.balance')]}
              />
            </>
          )}

          {payables.length > 0 && (
            <>
              <SectionTitle>{t('mensualizados.sections.payablesChart')}</SectionTitle>
              <ResponsiveContainer width="100%" height={Math.max(150, payables.length * 36)}>
                <BarChart data={payables.slice(0, 10)} layout="vertical" margin={{ left: 120 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => `$${(v / 1_000_000).toFixed(1)}M`} />
                  <YAxis type="category" dataKey="Tercero" tick={{ fontSize: 10 }} width={120} />
                  <Tooltip formatter={(v: any) => cop(v)} />
                  <Bar dataKey="Saldo" fill="#ef4444" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
              <DataTable
                rows={payables.map((r: any) => ({ 'Tercero': r['Tercero'], 'Saldo': cop(r['Saldo']) }))}
                cols={['Tercero', 'Saldo']}
                headers={[t('mensualizados.cols.third'), t('mensualizados.cols.balance')]}
              />
            </>
          )}

          {activity.length > 0 && (
            <>
              <SectionTitle>{t('mensualizados.sections.activityChart')}</SectionTitle>
              <DataTable
                rows={activity.map((r: any) => ({
                  'Tercero': r['Tercero'],
                  'Débitos': cop(r['Débitos']),
                  'Créditos': cop(r['Créditos']),
                  'Movimiento': cop(r['Movimiento']),
                }))}
                cols={['Tercero', 'Débitos', 'Créditos', 'Movimiento']}
                headers={[
                  t('mensualizados.cols.third'),
                  t('mensualizados.cols.debits'),
                  t('mensualizados.cols.credits'),
                  t('mensualizados.cols.movement'),
                ]}
              />
            </>
          )}
        </div>
      )}

      {tab === 'downloads' && (
        <div className="flex flex-wrap gap-3 pt-2">
          {outputFiles.map((f) => <DownloadBtn key={f.id} reportId={reportId} file={f} />)}
        </div>
      )}
    </div>
  )
}

function PurchasesReportView({ meta, reportId, outputFiles }: { meta: any; reportId: string; outputFiles: any[] }) {
  const t = useTranslations('reportDetail')
  const tCommon = useTranslations('common')
  const byCategory: { label: string; value: number }[] = meta?.by_category ?? []
  const topSuppliers: { label: string; value: number }[] = meta?.top_suppliers ?? []

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-2">
        <KpiCard label={t('purchases.total')} value={cop(meta?.total_amount ?? 0)} />
        <KpiCard label={t('purchases.invoices')} value={num(meta?.invoice_count ?? 0)} />
        <KpiCard label={t('purchases.autoClassified')} value={pct(meta?.auto_classified_share ?? 0)} />
        <KpiCard label={t('purchases.period')} value={meta?.period ?? '—'} />
      </div>

      <SectionTitle>{t('purchases.byCategory')}</SectionTitle>
      {byCategory.length > 0 ? (
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={byCategory}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={0} angle={-15} textAnchor="end" height={60} />
            <YAxis tickFormatter={(v) => cop(v)} width={90} tick={{ fontSize: 10 }} />
            <Tooltip formatter={(v: any) => cop(v)} />
            <Bar dataKey="value" fill="#0B6B57" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-xs text-gray-400">{tCommon('noData')}</p>
      )}

      <SectionTitle>{t('purchases.topSuppliers')}</SectionTitle>
      {topSuppliers.length > 0 ? (
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={topSuppliers} dataKey="value" nameKey="label" cx="50%" cy="50%" outerRadius={80} label>
              {topSuppliers.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(v: any) => cop(v)} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-xs text-gray-400">{tCommon('noData')}</p>
      )}

      <SectionTitle>{t('purchases.narrative')}</SectionTitle>
      <p className="text-sm text-gray-700 leading-relaxed bg-gray-50 border border-gray-200 rounded-xl p-4">
        {meta?.narrative}
      </p>

      <SectionTitle>{tCommon('downloads')}</SectionTitle>
      <div className="flex flex-wrap gap-3 pt-2">
        {outputFiles.map((f) => (
          <DownloadBtn key={f.id} reportId={reportId} file={f} />
        ))}
      </div>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function ReportDetailPage() {
  const t = useTranslations('reportDetail')
  const { id } = useParams<{ id: string }>()
  const router = useRouter()

  const { data: report, isLoading, error } = useQuery({
    queryKey: ['report', id],
    queryFn: () => reportApi.get(id),
    refetchInterval: (query) =>
      query.state.data?.status === 'pending' || query.state.data?.status === 'processing' ? 2000 : false,
  })

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-gray-400 text-sm">{t('loading')}</div>
  }
  if (error || !report) {
    return <div className="flex items-center justify-center h-64 text-red-500 text-sm">{t('error')}</div>
  }

  const STATUS_BADGE: Record<string, { cls: string; icon: React.ReactNode }> = {
    pending: { cls: 'bg-gray-100 text-gray-600', icon: null },
    processing: { cls: 'bg-blue-100 text-blue-700', icon: null },
    completed: { cls: 'bg-green-100 text-green-700', icon: <CheckCircle size={13} /> },
    failed: { cls: 'bg-red-100 text-red-700', icon: <XCircle size={13} /> },
  }

  const badge = STATUS_BADGE[report.status]

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-start gap-4 mb-6">
        <button
          onClick={() => router.back()}
          className="mt-0.5 p-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-500"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold text-gray-900">{t(`types.${report.report_type}`)}</h1>
            <span className={`flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${badge.cls}`}>
              {badge.icon}{t(`status.${report.status}`)}
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-0.5">{t('period', { period: report.period })}</p>
        </div>
      </div>

      {(report.status === 'pending' || report.status === 'processing') && (
        <div className="flex items-center gap-3 text-sm text-blue-700 bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
          <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          {t('generating')}
        </div>
      )}

      {report.status === 'failed' && (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
          <strong>{t('failed')}</strong> {report.error_message}
        </div>
      )}

      {report.status === 'completed' && (
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          {report.report_type === 'sazon' && (
            <SazonView meta={report.metadata} reportId={report.id} outputFiles={report.output_files} />
          )}
          {report.report_type === 'tlg' && (
            <TlgView meta={report.metadata} reportId={report.id} outputFiles={report.output_files} />
          )}
          {report.report_type === 'mensualizados' && (
            <MensualizadosView meta={report.metadata} reportId={report.id} outputFiles={report.output_files} />
          )}
          {(report.report_type === 'purchases_general' || report.report_type === 'purchases_sector') && (
            <PurchasesReportView meta={report.metadata} reportId={report.id} outputFiles={report.output_files} />
          )}
        </div>
      )}
    </div>
  )
}
