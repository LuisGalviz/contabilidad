import Link from 'next/link'
import { getTranslations } from 'next-intl/server'

export default async function LandingPage() {
  const t = await getTranslations('landing')

  const modules = [
    { key: 'sazon', title: t('modules.sazon.title'), desc: t('modules.sazon.desc') },
    { key: 'tlg', title: t('modules.tlg.title'), desc: t('modules.tlg.desc') },
    { key: 'mensualizados', title: t('modules.mensualizados.title'), desc: t('modules.mensualizados.desc') },
  ]

  return (
    <main className="min-h-screen bg-white">
      <nav className="border-b border-gray-100 px-6 py-4 flex items-center justify-between max-w-6xl mx-auto">
        <span className="font-bold text-xl text-[#0B6B57]">ContaFlow</span>
        <div className="flex gap-4">
          <Link href="/login" className="text-sm text-gray-600 hover:text-gray-900 px-4 py-2">
            {t('login')}
          </Link>
          <Link
            href="/register"
            className="text-sm bg-[#0B6B57] text-white px-4 py-2 rounded-lg hover:bg-[#075446] transition-colors"
          >
            {t('startFree')}
          </Link>
        </div>
      </nav>

      <section className="max-w-4xl mx-auto px-6 py-24 text-center">
        <p className="text-sm font-semibold text-[#0B6B57] uppercase tracking-wide mb-4">
          {t('badge')}
        </p>
        <h1 className="text-5xl font-bold text-gray-900 leading-tight mb-6">
          {t('headline')}
        </h1>
        <p className="text-xl text-gray-500 max-w-2xl mx-auto mb-10">
          {t('subtitle')}
        </p>
        <Link
          href="/register"
          className="inline-block bg-[#0B6B57] text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-[#075446] transition-colors"
        >
          {t('cta')}
        </Link>
      </section>

      <section className="max-w-5xl mx-auto px-6 pb-24 grid grid-cols-1 md:grid-cols-3 gap-8">
        {modules.map((m) => (
          <div key={m.key} className="border border-gray-200 rounded-xl p-6 bg-white">
            <h3 className="font-semibold text-gray-900 mb-2">{m.title}</h3>
            <p className="text-sm text-gray-500 leading-relaxed">{m.desc}</p>
          </div>
        ))}
      </section>
    </main>
  )
}
