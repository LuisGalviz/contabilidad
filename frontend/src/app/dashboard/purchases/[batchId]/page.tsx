'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useTranslations } from 'next-intl'
import Link from 'next/link'
import { purchaseApi } from '@/lib/api'
import { apiError } from '@/lib/errors'
import { ArrowLeft, CheckCircle, XCircle, ListChecks } from 'lucide-react'

function currentPeriod(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

export default function ImportBatchDetailPage() {
  const t = useTranslations('purchases')
  const tCommon = useTranslations('common')
  const { batchId } = useParams<{ batchId: string }>()
  const router = useRouter()
  const [period, setPeriod] = useState(currentPeriod())
  const [message, setMessage] = useState('')

  const { data: batch, isLoading, error } = useQuery({
    queryKey: ['import-batch', batchId],
    queryFn: () => purchaseApi.getBatch(batchId),
    refetchInterval: (query) =>
      query.state.data?.status === 'pending' || query.state.data?.status === 'processing' ? 2000 : false,
  })

  const generateCausation = useMutation({
    mutationFn: () => purchaseApi.generateCausation({ client_id: batch!.client_id, period }),
    onSuccess: () => setMessage(t('batch.generateSuccess')),
    onError: (e: any) => setMessage(apiError(e)),
  })

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-gray-400 text-sm">{tCommon('loading')}</div>
  }
  if (error || !batch) {
    return <div className="flex items-center justify-center h-64 text-red-500 text-sm">{tCommon('error')}</div>
  }

  const STATUS_BADGE: Record<string, { cls: string; icon: React.ReactNode }> = {
    pending: { cls: 'bg-gray-100 text-gray-600', icon: null },
    processing: { cls: 'bg-blue-100 text-blue-700', icon: null },
    completed: { cls: 'bg-green-100 text-green-700', icon: <CheckCircle size={13} /> },
    failed: { cls: 'bg-red-100 text-red-700', icon: <XCircle size={13} /> },
  }
  const badge = STATUS_BADGE[batch.status]

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-start gap-4 mb-6">
        <button
          onClick={() => router.push('/dashboard/purchases')}
          className="mt-0.5 p-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-500"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold text-gray-900">{batch.original_name}</h1>
            <span className={`flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${badge.cls}`}>
              {badge.icon}
              {t(`status.${batch.status}`)}
            </span>
          </div>
        </div>
      </div>

      {(batch.status === 'pending' || batch.status === 'processing') && (
        <div className="flex items-center gap-3 text-sm text-blue-700 bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
          <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          {tCommon('loading')}
        </div>
      )}

      {batch.status === 'failed' && (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
          <strong>{tCommon('error')}:</strong> {batch.error_message}
        </div>
      )}

      {batch.status === 'completed' && (
        <>
          <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
            <p className="text-sm text-gray-700 mb-4">
              {t('batch.summary', {
                total: batch.total_rows,
                new: batch.new_invoices,
                duplicates: batch.duplicate_invoices,
                errors: batch.error_rows,
              })}
            </p>
            <Link
              href={`/dashboard/purchases/invoices?batch_id=${batch.id}&client_id=${batch.client_id}`}
              className="inline-flex items-center gap-2 bg-[#0B6B57] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#075446] transition-colors"
            >
              <ListChecks size={16} /> {t('batch.reviewCta')}
            </Link>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <h2 className="font-semibold text-gray-900 mb-1 text-sm">{t('batch.causationTitle')}</h2>
            <p className="text-xs text-gray-500 mb-4">{t('batch.generateHint')}</p>
            {message && <p className="text-sm text-[#0B6B57] mb-3">{message}</p>}
            <div className="flex items-end gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t('batch.period')}</label>
                <input
                  type="month"
                  value={period}
                  onChange={(e) => setPeriod(e.target.value)}
                  className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B6B57]"
                />
              </div>
              <button
                onClick={() => generateCausation.mutate()}
                disabled={generateCausation.isPending}
                className="bg-[#0B6B57] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#075446] disabled:opacity-60"
              >
                {generateCausation.isPending ? t('batch.generating') : t('batch.generateCausation')}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
