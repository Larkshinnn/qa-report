import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api'

interface AuthState {
  authenticated: boolean
  account_id: string | null
  email: string | null
  display_name: string | null
  avatar_url: string | null
  google_ready: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const authenticated = ref(false)
  const accountId = ref('')
  const email = ref('')
  const displayName = ref('')
  const avatarUrl = ref('')
  const googleReady = ref(false)
  const everAuthenticated = ref(false)
  function update(state: AuthState): void {
    authenticated.value = state.authenticated
    accountId.value = state.account_id ?? ''
    email.value = state.email ?? ''
    displayName.value = state.display_name ?? ''
    avatarUrl.value = state.avatar_url ?? ''
    googleReady.value = state.google_ready
    if (state.authenticated) everAuthenticated.value = true
  }
  async function check(): Promise<void> {
    update(await api<AuthState>('/auth/status'))
  }
  function loginWithGoogle(): void {
    const base = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
    window.location.assign(`${base}/auth/google/start`)
  }
  async function logout(): Promise<void> {
    await api<void>('/auth/logout', { method: 'POST' })
    authenticated.value = false
    everAuthenticated.value = false
    accountId.value = ''
    email.value = ''
    displayName.value = ''
    avatarUrl.value = ''
  }
  return {
    authenticated,
    accountId,
    email,
    displayName,
    avatarUrl,
    googleReady,
    everAuthenticated,
    check,
    loginWithGoogle,
    logout,
  }
})
