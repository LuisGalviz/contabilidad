'use client'

import { useQuery } from '@tanstack/react-query'
import { useTranslations } from 'next-intl'
import { authApi, tenantApi } from '@/lib/api'

export default function SettingsPage() {
  const t = useTranslations('settings')
  const { data: user } = useQuery({ queryKey: ['me'], queryFn: authApi.me })
  const { data: tenant } = useQuery({ queryKey: ['tenant'], queryFn: tenantApi.getMyTenant })

  return (
    <div>
      <div className="mb-8">
        <p className="text-xs font-semibold text-[#0B6B57] uppercase tracking-wide mb-1">{t('badge')}</p>
        <h1 className="text-2xl font-bold text-gray-900">{t('title')}</h1>
      </div>

      <div className="grid gap-6 max-w-2xl">
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="font-semibold text-gray-900 mb-4">{t('profile.title')}</h2>
          <div className="space-y-3">
            {[
              { label: t('profile.name'), value: user?.name },
              { label: t('profile.email'), value: user?.email },
              { label: t('profile.role'), value: user?.role },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between text-sm">
                <span className="text-gray-500">{label}</span>
                <span className="font-medium text-gray-900 capitalize">{value ?? '—'}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="font-semibold text-gray-900 mb-4">{t('workspace.title')}</h2>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">{t('workspace.name')}</span>
              <span className="font-medium text-gray-900">{tenant?.name ?? '—'}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">{t('workspace.plan')}</span>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700">
                {tenant?.plan ? t(`plans.${tenant.plan}`) : '—'}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">{t('workspace.maxClients')}</span>
              <span className="font-medium text-gray-900">{tenant?.max_clients ?? '—'}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">{t('workspace.since')}</span>
              <span className="font-medium text-gray-900">
                {tenant?.created_at ? new Date(tenant.created_at).toLocaleDateString() : '—'}
              </span>
            </div>
          </div>
        </div>

        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
          <h2 className="font-semibold text-amber-900 mb-1">{t('upgrade.title')}</h2>
          <p className="text-sm text-amber-700 mb-4">
            {t('upgrade.desc', { max: tenant?.max_clients ?? 5 })}
          </p>
          <button
            disabled
            className="text-sm bg-amber-600 text-white px-4 py-2 rounded-lg font-medium opacity-60 cursor-not-allowed"
          >
            {t('upgrade.cta')}
          </button>
        </div>
      </div>
    </div>
  )
}
