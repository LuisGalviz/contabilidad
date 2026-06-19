import type { NextConfig } from 'next'
import createNextIntlPlugin from 'next-intl/plugin'

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts')

const nextConfig: NextConfig = {
  ...(process.env.NEXT_OUTPUT === 'standalone' && { output: 'standalone' }),
  async rewrites() {
    const backend = process.env.BACKEND_URL ?? 'http://localhost:8000'
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backend}/api/v1/:path*`,
      },
    ]
  },
}

export default withNextIntl(nextConfig)
