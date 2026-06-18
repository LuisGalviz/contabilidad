'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslations } from 'next-intl'
import { clientApi, reportApi, downloadFile } from '@/lib/api'
import { apiError } from '@/lib/errors'
import type { Report, ReportType } from '@/types'
import { Upload, FileText, Download, Eye } from 'lucide-react'
import Link from 'next/link'

function DownloadButtons({ report, tFn }: { report: Report; tFn: (k: string) => string }) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null

  const download = (fileId: string, fileName: string) => {
    const url = reportApi.downloadUrl(report.id, fileId)
    const a = document.createElement('a')
    a.href = url
    a.setAttribute('download', fileName)
    fetch(url, { headers: { Authorization: `Bearer ${token}` }, redirect: 'follow' })
      .then((r) => r.url)
      .then((redirectUrl) => { a.href = redirectUrl; a.click() })
  }

  return (
    <div className="flex gap-2">
      {report.output_files.map((f) => (
        <button
          key={f.id}
          onClick={() => download(f.id, f.original_name)}
          className="flex items-center gap-1 text-xs text-[#0B6B57] border border-[#0B6B57] px-2.5 py-1 rounded-lg hover:bg-[#0B6B57] hover:text-white transition-colors"
        >
          <Download size={12} />
          {f.original_name.endsWith('.pdf') ? 'PDF' : 'Excel'}
        </button>
      ))}
    </div>
  )
}

export default function ReportsPage() {
  const t = useTranslations('reports')
  const tCommon = useTranslations('common')
  const qc = useQueryClient()
  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: clientApi.list })
  const { data: reports, isLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: () => reportApi.list(),
    refetchInterval: (data) => {
      const hasProcessing = data?.items?.some((r) => r.status === 'pending' || r.status === 'processing')
      return hasProcessing ? 3000 : false
    },
  })
  const [showForm, setShowForm] = useState(false)
  const [clientId, setClientId] = useState('')
  const [reportType, setReportType] = useState<ReportType>('sazon')
  const [ventasFile, setVentasFile] = useState<File | null>(null)
  const [gastosFile, setGastosFile] = useState<File | null>(null)
  const [files, setFiles] = useState<File[]>([])
  const [error, setError] = useState('')

  const REPORT_TYPES: { value: ReportType; label: string; hint: string }[] = [
    { value: 'sazon', label: t('types.sazon'), hint: t('hints.sazon') },
    { value: 'tlg', label: t('types.tlg'), hint: t('hints.tlg') },
    { value: 'mensualizados', label: t('types.mensualizados'), hint: t('hints.mensualizados') },
  ]

  const selectedType = REPORT_TYPES.find((rt) => rt.value === reportType)
  const isSazon = reportType === 'sazon'

  const allFiles = isSazon
    ? ([ventasFile, gastosFile].filter(Boolean) as File[])
    : files

  const canSubmit = !!(clientId && (isSazon ? ventasFile && gastosFile : files.length > 0))

  function resetForm() {
    setShowForm(false)
    setVentasFile(null)
    setGastosFile(null)
    setFiles([])
    setError('')
  }

  const create = useMutation({
    mutationFn: reportApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reports'] })
      resetForm()
    },
    onError: (e: any) => setError(apiError(e)),
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{t('subtitle', { count: reports?.total ?? 0 })}</p>
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
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('fields.type')}</label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value as ReportType)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B6B57]"
              >
                {REPORT_TYPES.map((rt) => (
                  <option key={rt.value} value={rt.value}>{rt.label}</option>
                ))}
              </select>
              {selectedType && <p className="text-xs text-gray-400 mt-1">{selectedType.hint}</p>}
            </div>
            {isSazon ? (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('fields.salesFile')}</label>
                  <input
                    type="file"
                    accept=".xlsx"
                    onChange={(e) => setVentasFile(e.target.files?.[0] ?? null)}
                    className="w-full text-sm text-gray-500 file:mr-4 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:bg-gray-100 file:text-gray-700"
                  />
                  {ventasFile && <p className="text-xs text-green-600 mt-1">✓ {ventasFile.name}</p>}
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('fields.expensesFile')}</label>
                  <input
                    type="file"
                    accept=".xlsx"
                    onChange={(e) => setGastosFile(e.target.files?.[0] ?? null)}
                    className="w-full text-sm text-gray-500 file:mr-4 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:bg-gray-100 file:text-gray-700"
                  />
                  {gastosFile && <p className="text-xs text-green-600 mt-1">✓ {gastosFile.name}</p>}
                </div>
              </>
            ) : (
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  {reportType === 'tlg' ? t('fields.balanceFile') : t('fields.monthlyFiles')}
                </label>
                <input
                  type="file"
                  accept=".xlsx"
                  multiple={reportType === 'mensualizados'}
                  onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
                  className="w-full text-sm text-gray-500 file:mr-4 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:bg-gray-100 file:text-gray-700"
                />
                {files.length > 0 && (
                  <p className="text-xs text-green-600 mt-1">✓ {files.map((f) => f.name).join(', ')}</p>
                )}
              </div>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => create.mutate({ client_id: clientId, report_type: reportType, period: '', files: allFiles })}
              disabled={create.isPending || !canSubmit}
              className="bg-[#0B6B57] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#075446] disabled:opacity-60"
            >
              {create.isPending ? t('submitting') : t('submit')}
            </button>
            <button onClick={resetForm} className="border border-gray-300 text-gray-600 px-4 py-2 rounded-lg text-sm">
              {tCommon('cancel')}
            </button>
          </div>
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {isLoading && <div className="px-6 py-8 text-center text-gray-400 text-sm">{t('loading')}</div>}
        {!isLoading && reports?.items.length === 0 && (
          <div className="px-6 py-8 text-center text-gray-400 text-sm">{t('empty')}</div>
        )}
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              {[t('table.type'), t('table.period'), t('table.status'), t('table.created'), t('table.actions')].map((h) => (
                <th key={h} className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {reports?.items.map((r) => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <FileText size={14} className="text-gray-400" />
                    <span className="font-medium text-gray-900">{t(`types.${r.report_type}`)}</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-gray-500">{r.period}</td>
                <td className="px-6 py-4">
                  <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                    r.status === 'completed' ? 'bg-green-50 text-green-700' :
                    r.status === 'failed' ? 'bg-red-50 text-red-700' :
                    'bg-amber-50 text-amber-700'
                  }`}>
                    {t(`status.${r.status}`)}
                  </span>
                  {r.error_message && (
                    <p className="text-xs text-red-500 mt-1 max-w-xs truncate" title={r.error_message}>
                      {r.error_message}
                    </p>
                  )}
                </td>
                <td className="px-6 py-4 text-gray-500 text-xs">
                  {new Date(r.created_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Link
                      href={`/dashboard/reports/${r.id}`}
                      className="inline-flex items-center gap-1 text-xs font-medium text-[#0B6B57] hover:underline"
                    >
                      <Eye size={13} /> {tCommon('view')}
                    </Link>
                    {r.status === 'completed' && r.output_files.length > 0 && (
                      <DownloadButtons report={r} tFn={(k) => t(k)} />
                    )}
                    {(r.status === 'pending' || r.status === 'processing') && (
                      <span className="text-xs text-gray-400 animate-pulse">{t('processing')}</span>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
