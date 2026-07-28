'use client'

import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslations } from 'next-intl'
import { clientApi, pucApi } from '@/lib/api'
import { apiError } from '@/lib/errors'
import { ACCOUNT_ROLES, type ChartImportResult } from '@/types'
import { AlertTriangle, Upload } from 'lucide-react'

export default function ChartOfAccountsPage() {
  const t = useTranslations('chartOfAccounts')
  const queryClient = useQueryClient()
  const fileInput = useRef<HTMLInputElement>(null)

  const [clientId, setClientId] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState<ChartImportResult | null>(null)
  const [roleDraft, setRoleDraft] = useState<Record<string, string>>({})

  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: clientApi.list })

  const { data: accounts } = useQuery({
    queryKey: ['puc-accounts', clientId],
    queryFn: () => pucApi.listAccounts({ client_id: clientId }),
    enabled: Boolean(clientId),
  })

  const { data: settings } = useQuery({
    queryKey: ['account-settings', clientId],
    queryFn: () => pucApi.getAccountSettings(clientId),
    enabled: Boolean(clientId),
  })

  const importMutation = useMutation({
    mutationFn: (file: File) => pucApi.importChart({ client_id: clientId, file }),
    onSuccess: (data) => {
      setResult(data)
      setError('')
      queryClient.invalidateQueries({ queryKey: ['puc-accounts', clientId] })
      queryClient.invalidateQueries({ queryKey: ['account-settings', clientId] })
    },
    onError: (e) => {
      setResult(null)
      setError(apiError(e))
    },
  })

  const saveRolesMutation = useMutation({
    mutationFn: () => pucApi.updateAccountSettings(clientId, roleDraft),
    onSuccess: () => {
      setError('')
      setRoleDraft({})
      queryClient.invalidateQueries({ queryKey: ['account-settings', clientId] })
    },
    onError: (e) => setError(apiError(e)),
  })

  const currentRoleCode = (role: string) =>
    roleDraft[role] ?? settings?.items.find((s) => s.role === role)?.account_code ?? ''

  return (
    <div>
      <div className="mb-8">
        <p className="text-xs font-semibold text-[#0B6B57] uppercase tracking-wide mb-1">{t('badge')}</p>
        <h1 className="text-2xl font-bold text-gray-900">{t('title')}</h1>
        <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
      </div>

      <div className="grid gap-6 max-w-3xl">
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">{t('client')}</label>
          <select
            value={clientId}
            onChange={(e) => {
              setClientId(e.target.value)
              setResult(null)
              setRoleDraft({})
            }}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">{t('selectClient')}</option>
            {clients?.items.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        {clientId && (
          <>
            <div className="bg-white border border-gray-200 rounded-xl p-6">
              <h2 className="font-semibold text-gray-900 mb-1">{t('import.title')}</h2>
              <p className="text-sm text-gray-500 mb-4">{t('import.help')}</p>

              <input
                ref={fileInput}
                type="file"
                accept=".xlsx,.xls"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) importMutation.mutate(file)
                  e.target.value = ''
                }}
              />
              <button
                onClick={() => fileInput.current?.click()}
                disabled={importMutation.isPending}
                className="inline-flex items-center gap-2 bg-[#0B6B57] text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
              >
                <Upload className="w-4 h-4" />
                {importMutation.isPending ? t('import.uploading') : t('import.button')}
              </button>

              <p className="text-xs text-gray-500 mt-3">
                {t('import.currentCount', { count: accounts?.items.length ?? 0 })}
              </p>

              {result && (
                <div className="mt-4 rounded-lg bg-green-50 border border-green-200 p-4 text-sm">
                  <p className="font-medium text-green-800">
                    {t('import.summary', {
                      created: result.created,
                      updated: result.updated,
                      deactivated: result.deactivated,
                    })}
                  </p>
                  {result.messages.map((m) => (
                    <p key={m} className="text-green-700 mt-1">
                      {m}
                    </p>
                  ))}
                </div>
              )}

              {result?.warnings.map((w) => (
                <div
                  key={w}
                  className="mt-3 flex gap-2 rounded-lg bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800"
                >
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{w}</span>
                </div>
              ))}
            </div>

            <div className="bg-white border border-gray-200 rounded-xl p-6">
              <h2 className="font-semibold text-gray-900 mb-1">{t('roles.title')}</h2>
              <p className="text-sm text-gray-500 mb-4">{t('roles.help')}</p>

              <div className="space-y-4">
                {ACCOUNT_ROLES.map((role) => (
                  <div key={role}>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{t(`roles.${role}`)}</label>
                    <select
                      value={currentRoleCode(role)}
                      onChange={(e) => setRoleDraft({ ...roleDraft, [role]: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    >
                      <option value="">{t('roles.selectAccount')}</option>
                      {accounts?.items.map((a) => (
                        <option key={a.code} value={a.code}>
                          {a.code} — {a.name}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>

              <button
                onClick={() => saveRolesMutation.mutate()}
                disabled={Object.keys(roleDraft).length === 0 || saveRolesMutation.isPending}
                className="mt-4 bg-[#0B6B57] text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
              >
                {saveRolesMutation.isPending ? t('roles.saving') : t('roles.save')}
              </button>
            </div>
          </>
        )}

        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">{error}</div>
        )}
      </div>
    </div>
  )
}
