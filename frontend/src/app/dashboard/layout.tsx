'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { useTranslations, useLocale } from 'next-intl'
import { isAuthenticated, clearTokens } from '@/lib/auth'
import { setLocale } from '@/lib/locale'
import { LayoutDashboard, Users, ShoppingCart, FileText, Settings, LogOut, Globe } from 'lucide-react'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations('nav')
  const tSettings = useTranslations('settings.language')
  const locale = useLocale()
  const router = useRouter()
  const pathname = usePathname()
  const [switching, setSwitching] = useState(false)

  const NAV = [
    { href: '/dashboard', label: t('home'), icon: LayoutDashboard },
    { href: '/dashboard/clients', label: t('clients'), icon: Users },
    { href: '/dashboard/purchases', label: t('purchases'), icon: ShoppingCart },
    { href: '/dashboard/reports', label: t('reports'), icon: FileText },
    { href: '/dashboard/settings', label: t('settings'), icon: Settings },
  ]

  useEffect(() => {
    if (!isAuthenticated()) router.push('/login')
  }, [router])

  const handleLogout = () => {
    clearTokens()
    router.push('/login')
  }

  const handleLocale = async (next: 'es' | 'en') => {
    setSwitching(true)
    await setLocale(next)
    router.refresh()
    setSwitching(false)
  }

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 bg-[#101828] flex flex-col">
        <div className="px-5 py-6 border-b border-[#1D2939]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-[#D6A44B] rounded-lg flex items-center justify-center text-[#101828] font-bold text-sm">
              CF
            </div>
            <div>
              <div className="text-white text-sm font-semibold">{t('brand')}</div>
              <div className="text-[#98A2B3] text-xs">{t('brandSub')}</div>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  active ? 'bg-[#1D2939] text-white' : 'text-[#98A2B3] hover:bg-[#1D2939] hover:text-white'
                }`}
              >
                <Icon size={16} />
                {label}
              </Link>
            )
          })}
        </nav>

        <div className="px-3 py-3 border-t border-[#1D2939] space-y-1">
          {/* Language switcher */}
          <div className="flex items-center gap-2 px-3 py-2">
            <Globe size={14} className="text-[#98A2B3]" />
            <div className="flex gap-1">
              {(['es', 'en'] as const).map((lng) => (
                <button
                  key={lng}
                  onClick={() => handleLocale(lng)}
                  disabled={switching}
                  className={`text-xs px-2 py-0.5 rounded transition-colors ${
                    locale === lng
                      ? 'bg-[#0B6B57] text-white'
                      : 'text-[#98A2B3] hover:text-white'
                  }`}
                >
                  {tSettings(lng)}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm text-[#98A2B3] hover:bg-[#1D2939] hover:text-white transition-colors"
          >
            <LogOut size={16} />
            {t('logout')}
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto bg-gray-50">
        <div className="max-w-6xl mx-auto px-8 py-8">{children}</div>
      </main>
    </div>
  )
}
