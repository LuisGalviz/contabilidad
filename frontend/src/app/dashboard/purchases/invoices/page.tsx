'use client'

import { useMemo, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslations } from 'next-intl'
import { clientApi, purchaseApi, pucApi } from '@/lib/api'
import { apiError } from '@/lib/errors'
import type { SupplierInvoice } from '@/types'
import { Check, X } from 'lucide-react'

function cop(v: number) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v)
}

const CONFIDENCE_CLS: Record<string, string> = {
  auto_high_confidence: 'bg-green-50 text-green-700',
  auto_low_confidence: 'bg-amber-50 text-amber-700',
  manual: 'bg-blue-50 text-blue-700',
  none: 'bg-gray-100 text-gray-500',
}

function AccountPicker({
  value,
  onChange,
  accounts,
  placeholder,
}: {
  value: string
  onChange: (code: string) => void
  accounts: { code: string; name: string }[]
  placeholder: string
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="border border-gray-300 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-[#0B6B57] max-w-[220px]"
    >
      <option value="">{placeholder}</option>
      {accounts.map((a) => (
        <option key={a.code} value={a.code}>
          {a.code} · {a.name}
        </option>
      ))}
    </select>
  )
}

export default function InvoiceReviewPage() {
  const t = useTranslations('invoiceReview')
  const tCommon = useTranslations('common')
  const qc = useQueryClient()
  const searchParams = useSearchParams()
  const batchId = searchParams.get('batch_id') ?? undefined

  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: clientApi.list })
  const [clientId, setClientId] = useState(searchParams.get('client_id') ?? '')
  const [statusFilter, setStatusFilter] = useState('')
  const [selectedAccounts, setSelectedAccounts] = useState<Record<string, string>>({})
  const [checked, setChecked] = useState<Set<string>>(new Set())
  const [bulkAccount, setBulkAccount] = useState('')
  const [error, setError] = useState('')

  const { data: accounts } = useQuery({ queryKey: ['puc-accounts'], queryFn: () => pucApi.listAccounts() })

  const { data: invoices, isLoading } = useQuery({
    queryKey: ['purchase-invoices', clientId, statusFilter, batchId],
    queryFn: () =>
      purchaseApi.listInvoices({
        client_id: clientId || undefined,
        status: statusFilter || undefined,
        batch_id: batchId,
      }),
    enabled: !!clientId,
  })

  const classify = useMutation({
    mutationFn: ({ id, account_code }: { id: string; account_code: string }) =>
      purchaseApi.classifyInvoice(id, { account_code }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['purchase-invoices'] }),
    onError: (e: any) => setError(apiError(e)),
  })

  const reject = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => purchaseApi.rejectInvoice(id, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['purchase-invoices'] }),
    onError: (e: any) => setError(apiError(e)),
  })

  const bulkClassify = useMutation({
    mutationFn: () => purchaseApi.bulkClassify({ invoice_ids: Array.from(checked), account_code: bulkAccount }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['purchase-invoices'] })
      setChecked(new Set())
      setBulkAccount('')
    },
    onError: (e: any) => setError(apiError(e)),
  })

  const accountOptions = useMemo(() => accounts?.items ?? [], [accounts])

  function toggleChecked(id: string) {
    setChecked((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{t('subtitle', { count: invoices?.total ?? 0 })}</p>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-4 mb-4 flex gap-4 flex-wrap items-end">
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">{t('filters.client')}</label>
          <select
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B6B57]"
          >
            <option value="">—</option>
            {clients?.items.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">{t('filters.status')}</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B6B57]"
          >
            <option value="">{tCommon('all')}</option>
            {['pending_review', 'classified', 'caused', 'rejected', 'error'].map((s) => (
              <option key={s} value={s}>
                {t(`status.${s}`)}
              </option>
            ))}
          </select>
        </div>

        {checked.size > 0 && (
          <div className="flex items-end gap-2 ml-auto">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{tCommon('selected', { count: checked.size })}</label>
              <AccountPicker value={bulkAccount} onChange={setBulkAccount} accounts={accountOptions} placeholder={t('actions.selectAccount')} />
            </div>
            <button
              onClick={() => bulkClassify.mutate()}
              disabled={!bulkAccount || bulkClassify.isPending}
              className="bg-[#0B6B57] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#075446] disabled:opacity-60"
            >
              {t('actions.bulkConfirm')}
            </button>
          </div>
        )}
      </div>

      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {!clientId && <div className="px-6 py-8 text-center text-gray-400 text-sm">{t('filters.client')}</div>}
        {clientId && isLoading && <div className="px-6 py-8 text-center text-gray-400 text-sm">{tCommon('loading')}</div>}
        {clientId && !isLoading && invoices?.items.length === 0 && (
          <div className="px-6 py-8 text-center text-gray-400 text-sm">{t('empty')}</div>
        )}
        {clientId && invoices && invoices.items.length > 0 && (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="px-4 py-3" />
                {[t('table.supplier'), t('table.concept'), t('table.amount'), t('table.suggestion'), t('table.account'), t('table.actions')].map(
                  (h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {invoices.items.map((inv: SupplierInvoice) => {
                const confidenceKey = inv.classification_source ?? 'none'
                const selected = selectedAccounts[inv.id] ?? inv.suggested_account_code ?? ''
                const canEdit = inv.status === 'pending_review' || inv.status === 'classified'
                return (
                  <tr key={inv.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      {canEdit && (
                        <input type="checkbox" checked={checked.has(inv.id)} onChange={() => toggleChecked(inv.id)} />
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{inv.supplier_name}</div>
                      <div className="text-xs text-gray-400">{inv.supplier_nit}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-600 max-w-xs truncate" title={inv.concept_description}>
                      {inv.concept_description}
                    </td>
                    <td className="px-4 py-3 text-gray-900 font-medium whitespace-nowrap">{cop(inv.total_amount)}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-medium px-2 py-1 rounded-full ${CONFIDENCE_CLS[confidenceKey]}`}>
                        {t(`confidence.${confidenceKey}`)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {canEdit ? (
                        <AccountPicker
                          value={selected}
                          onChange={(code) => setSelectedAccounts((prev) => ({ ...prev, [inv.id]: code }))}
                          accounts={accountOptions}
                          placeholder={t('actions.selectAccount')}
                        />
                      ) : (
                        <span className="text-xs text-gray-500">{inv.final_account_code ?? '—'}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {canEdit && (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => classify.mutate({ id: inv.id, account_code: selected })}
                            disabled={!selected || classify.isPending}
                            className="flex items-center gap-1 text-xs text-white bg-[#0B6B57] px-2.5 py-1.5 rounded-lg hover:bg-[#075446] disabled:opacity-50"
                          >
                            <Check size={12} /> {t('actions.confirm')}
                          </button>
                          <button
                            onClick={() => {
                              const reason = window.prompt(t('rejectPrompt')) ?? ''
                              if (reason) reject.mutate({ id: inv.id, reason })
                            }}
                            className="flex items-center gap-1 text-xs text-red-600 border border-red-200 px-2.5 py-1.5 rounded-lg hover:bg-red-50"
                          >
                            <X size={12} /> {t('actions.reject')}
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
