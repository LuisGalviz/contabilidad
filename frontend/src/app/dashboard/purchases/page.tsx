'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslations } from 'next-intl'
import Link from 'next/link'
import { clientApi, purchaseApi } from '@/lib/api'
import { apiError } from '@/lib/errors'
import type { ImportBatch } from '@/types'
import { Upload, FileSpreadsheet, Eye } from 'lucide-react'

export default function PurchasesPage() {
  const t = useTranslations('purchases')
  const tCommon = useTranslations('common')
  const qc = useQueryClient()
  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: clientApi.list })
  const { data: batches, isLoading } = useQuery({
    queryKey: ['import-batches'],
    queryFn: () => purchaseApi.listBatches(),
    refetchInterval: (query) => {
      const hasProcessing = query.state.data?.items?.some(
        (b: ImportBatch) => b.status === 'pending' || b.status === 'processing'
      )
      return hasProcessing ? 3000 : false
    },
  })

  const [showForm, setShowForm] = useState(false)
  const [clientId, setClientId] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')

  function resetForm() {
    setShowForm(false)
    setClientId('')
    setFile(null)
    setError('')
  }

  const upload = useMutation({
    mutationFn: purchaseApi.uploadBatch,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['import-batches'] })
      resetForm()
    },
    onError: (e: any) => setError(apiError(e)),
  })

  const STATUS_CLS: Record<string, string> = {
    completed: 'bg-green-50 text-green-700',
    failed: 'bg-red-50 text-red-700',
    pending: 'bg-amber-50 text-amber-700',
    processing: 'bg-amber-50 text-amber-700',
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{t('subtitle', { count: batches?.total ?? 0 })}</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 bg-[#0B6B57] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#075446] transition-colors"
        >
          <Upload size={16} /> {t('new')}
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
          <h2 className="font-semibold text-gray-900 mb-4 text-sm">{t('formTitle')}</h2>
          {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('fields.client')}</label>
              <select
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B6B57]"
              >
                <option value="">{t('fields.clientPlaceholder')}</option>
                {clients?.items.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('fields.file')}</label>
              <input
                type="file"
                accept=".xlsx"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="w-full text-sm text-gray-500 file:mr-4 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:bg-gray-100 file:text-gray-700"
              />
              {file && <p className="text-xs text-green-600 mt-1">✓ {file.name}</p>}
            </div>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => file && upload.mutate({ client_id: clientId, file })}
              disabled={upload.isPending || !clientId || !file}
              className="bg-[#0B6B57] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#075446] disabled:opacity-60"
            >
              {upload.isPending ? t('submitting') : t('submit')}
            </button>
            <button onClick={resetForm} className="border border-gray-300 text-gray-600 px-4 py-2 rounded-lg text-sm">
              {tCommon('cancel')}
            </button>
          </div>
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {isLoading && <div className="px-6 py-8 text-center text-gray-400 text-sm">{t('loading')}</div>}
        {!isLoading && batches?.items.length === 0 && (
          <div className="px-6 py-8 text-center text-gray-400 text-sm">{t('empty')}</div>
        )}
        {batches && batches.items.length > 0 && (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {[t('table.file'), t('table.status'), t('table.new'), t('table.duplicates'), t('table.errors'), t('table.created'), ''].map(
                  (h) => (
                    <th key={h} className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {batches.items.map((b) => (
                <tr key={b.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <FileSpreadsheet size={14} className="text-gray-400" />
                      <span className="font-medium text-gray-900">{b.original_name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${STATUS_CLS[b.status]}`}>
                      {t(`status.${b.status}`)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-500">{b.new_invoices}</td>
                  <td className="px-6 py-4 text-gray-500">{b.duplicate_invoices}</td>
                  <td className="px-6 py-4 text-gray-500">{b.error_rows}</td>
                  <td className="px-6 py-4 text-gray-500 text-xs">{new Date(b.created_at).toLocaleDateString()}</td>
                  <td className="px-6 py-4 text-right">
                    <Link
                      href={`/dashboard/purchases/${b.id}`}
                      className="inline-flex items-center gap-1 text-xs font-medium text-[#0B6B57] hover:underline"
                    >
                      <Eye size={13} /> {tCommon('view')}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
