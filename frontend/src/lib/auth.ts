'use client'

import type { TokenResponse } from '@/types'

export function saveTokens(tokens: TokenResponse): void {
  localStorage.setItem('access_token', tokens.access_token)
  localStorage.setItem('refresh_token', tokens.refresh_token)
}

export function clearTokens(): void {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

export function getAccessToken(): string | null {
  return typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
}

export function isAuthenticated(): boolean {
  return getAccessToken() !== null
}
