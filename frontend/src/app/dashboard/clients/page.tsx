'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslations } from 'next-intl'
import { clientApi } from '@/lib/api'
import { apiError } from '@/lib/errors'
import { Plus, Trash2 } from 'lucide-react'

export default function ClientsPage() {
  const t = useTranslations('clients')
  const tCommon = useTranslations('common')
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['clients'], queryFn: clientApi.list })
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', nit: '', contact_email: '', contact_name: '', contact_phone: '' })
  const [error, setError] = useState('')

  const create = useMutation({
    mutationFn: clientApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clients'] })
      setShowForm(false)
      setForm({ name: '', nit: '', contact_email: '', contact_name: '', contact_phone: '' })
    },
    onError: (e: any) => setError(apiError(e)),
  })

  const deactivate = useMutation({
    mutationFn: clientApi.deactivate,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['clients'] }),
  })

  const fields = [
    { key: 'name', label: t('fields.name'), type: 'text', required: true },
    { key: 'nit', label: t('fields.nit'), type: 'text', required: true },
    { key: 'contact_email', label: t('fields.email'), type: 'email', required: true },
    { key: 'contact_name', label: t('fields.contactName'), type: 'text', required: false },
    { key: 'contact_phone', label: t('fields.phone'), type: 'text', required: false },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{t('subtitle', { count: data?.total ?? 0 })}</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 bg-[#0B6B57] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#075446] transition-colors"
        >
          <Plus size={16} /> {t('new')}
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
          <h2 className="font-semibold text-gray-900 mb-4 text-sm">{t('formTitle')}</h2>
          {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
          <div className="grid grid-cols-2 gap-4">
            {fields.map(({ key, label, type, required }) => (
              <div key={key}>
                <label className="block text-xs font-medium text-gray-700 mb-1">{label}</label>
                <input
                  type={type}
                  required={required}
                  value={form[key as keyof typeof form]}
                  onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B6B57]"
                />
              </div>
            ))}
          </div>
          <div className="flex gap-3 mt-4">
            <button
              onClick={() => create.mutate(form)}
              disabled={create.isPending}
              className="bg-[#0B6B57] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#075446] disabled:opacity-60"
            >
              {create.isPending ? tCommon('saving') : tCommon('save')}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="border border-gray-300 text-gray-600 px-4 py-2 rounded-lg text-sm"
            >
              {tCommon('cancel')}
            </button>
          </div>
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {isLoading && <div className="px-6 py-8 text-center text-gray-400 text-sm">{t('loading')}</div>}
        {!isLoading && data?.items.length === 0 && (
          <div className="px-6 py-8 text-center text-gray-400 text-sm">{t('empty')}</div>
        )}
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              {[t('table.name'), t('table.nit'), t('table.email'), t('table.phone'), ''].map((h) => (
                <th key={h} className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data?.items.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 font-medium text-gray-900">{c.name}</td>
                <td className="px-6 py-4 text-gray-500">{c.nit}</td>
                <td className="px-6 py-4 text-gray-500">{c.contact_email}</td>
                <td className="px-6 py-4 text-gray-500">{c.contact_phone || '—'}</td>
                <td className="px-6 py-4 text-right">
                  <button
                    onClick={() => deactivate.mutate(c.id)}
                    className="text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
