import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiJson, setTokens, clearTokens, getAccessToken, getRefreshToken } from '../services/api'

export interface User {
  id: string
  username: string
  email: string
  display_name: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(true)

  const isAuthenticated = computed(() => !!user.value)

  async function register(username: string, email: string, password: string, displayName: string = '') {
    const data = await apiJson<{
      user: User
      access_token: string
      refresh_token: string
    }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, email, password, display_name: displayName }),
    })
    setTokens(data.access_token, data.refresh_token)
    user.value = data.user
    return data.user
  }

  async function login(username: string, password: string) {
    const data = await apiJson<{
      user: User
      access_token: string
      refresh_token: string
    }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    setTokens(data.access_token, data.refresh_token)
    user.value = data.user
    return data.user
  }

  async function logout() {
    const refreshToken = getRefreshToken()
    if (refreshToken) {
      try {
        await apiJson('/api/auth/logout', {
          method: 'POST',
          body: JSON.stringify({ refresh_token: refreshToken }),
        })
      } catch {
        // Ignore errors on logout
      }
    }
    clearTokens()
    user.value = null
  }

  async function fetchProfile() {
    if (!getAccessToken()) {
      loading.value = false
      return
    }
    try {
      user.value = await apiJson<User>('/api/auth/me')
    } catch {
      clearTokens()
      user.value = null
    } finally {
      loading.value = false
    }
  }

  async function init() {
    await fetchProfile()
  }

  return {
    user,
    loading,
    isAuthenticated,
    register,
    login,
    logout,
    fetchProfile,
    init,
  }
})
