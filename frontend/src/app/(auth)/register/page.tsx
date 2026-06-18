'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { authApi } from '@/lib/api'
import { saveTokens } from '@/lib/auth'

export default function RegisterPage() {
  const t = useTranslations('auth.register')
  const router = useRouter()
  const [form, setForm] = useState({ name: '', email: '', password: '', tenant_name: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (key: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const tokens = await authApi.register(form)
      saveTokens(tokens)
      router.push('/dashboard')
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : t('error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <span className="text-2xl font-bold text-[#0B6B57]">ContaFlow</span>
          <p className="text-gray-500 text-sm mt-2">{t('title')}</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white border border-gray-200 rounded-xl p-8 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          {[
            { key: 'name', label: t('name'), type: 'text', placeholder: t('namePlaceholder'), min: 2 },
            { key: 'email', label: t('email'), type: 'email', placeholder: t('emailPlaceholder'), min: undefined },
            { key: 'password', label: t('password'), type: 'password', placeholder: t('passwordPlaceholder'), min: 8 },
            { key: 'tenant_name', label: t('tenantName'), type: 'text', placeholder: t('tenantNamePlaceholder'), min: 2 },
          ].map(({ key, label, type, placeholder, min }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
              <input
                type={type}
                value={form[key as keyof typeof form]}
                onChange={set(key)}
                required
                minLength={min}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B6B57]"
                placeholder={placeholder}
              />
            </div>
          ))}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#0B6B57] text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-[#075446] disabled:opacity-60 transition-colors"
          >
            {loading ? t('submitting') : t('submit')}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-4">
          {t('hasAccount')}{' '}
          <Link href="/login" className="text-[#0B6B57] font-medium hover:underline">
            {t('loginLink')}
          </Link>
        </p>
      </div>
    </div>
  )
}
