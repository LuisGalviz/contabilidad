'use client'

import { useQuery } from '@tanstack/react-query'
import { useTranslations } from 'next-intl'
import { authApi, clientApi, reportApi, tenantApi } from '@/lib/api'
import { Users, FileText, CheckCircle, Clock } from 'lucide-react'

export default function DashboardPage() {
  const t = useTranslations('dashboard')
  const tReports = useTranslations('reports')

  const { data: user } = useQuery({ queryKey: ['me'], queryFn: authApi.me })
  const { data: tenant } = useQuery({ queryKey: ['tenant'], queryFn: tenantApi.getMyTenant })
  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: clientApi.list })
  const { data: reports } = useQuery({ queryKey: ['reports'], queryFn: () => reportApi.list({ limit: 5 }) })

  const completed = reports?.items.filter((r) => r.status === 'completed').length ?? 0
  const pending = reports?.items.filter((r) => r.status === 'pending' || r.status === 'processing').length ?? 0

  return (
    <div>
      <div className="mb-8">
        <p className="text-xs font-semibold text-[#0B6B57] uppercase tracking-wide mb-1">{t('badge')}</p>
        <h1 className="text-2xl font-bold text-gray-900">
          {t('greeting', { name: user?.name?.split(' ')[0] ?? '' })}
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          {t('subtitle', { tenant: tenant?.name ?? '', plan: tenant?.plan ?? '' })}
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { label: t('kpis.activeClients'), value: clients?.total ?? 0, icon: Users, color: 'text-blue-600' },
          { label: t('kpis.totalReports'), value: reports?.total ?? 0, icon: FileText, color: 'text-purple-600' },
          { label: t('kpis.completed'), value: completed, icon: CheckCircle, color: 'text-green-600' },
          { label: t('kpis.processing'), value: pending, icon: Clock, color: 'text-amber-600' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white border border-gray-200 rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-gray-500">{label}</span>
              <Icon size={16} className={color} />
            </div>
            <div className="text-2xl font-bold text-gray-900">{value}</div>
          </div>
        ))}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900 text-sm">{t('recentReports')}</h2>
        </div>
        <div className="divide-y divide-gray-100">
          {reports?.items.length === 0 && (
            <div className="px-6 py-8 text-center text-gray-400 text-sm">{t('noReports')}</div>
          )}
          {reports?.items.map((r) => (
            <div key={r.id} className="px-6 py-4 flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-900">{tReports(`types.${r.report_type}`)}</div>
                <div className="text-xs text-gray-400">{r.period}</div>
              </div>
              <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                r.status === 'completed' ? 'bg-green-50 text-green-700' :
                r.status === 'failed' ? 'bg-red-50 text-red-700' :
                'bg-amber-50 text-amber-700'
              }`}>
                {tReports(`status.${r.status}`)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
