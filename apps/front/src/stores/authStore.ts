import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface User {
  id: string
  username: string
  name: string | null
  created_at: string
}

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  error: string | null
  
  // Actions
  login: (username: string, password: string) => Promise<boolean>
  register: (username: string, password: string, name?: string) => Promise<boolean>
  logout: () => void
  checkAuth: () => Promise<boolean>
  clearError: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,
      error: null,
      
      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
          })
          
          if (!response.ok) {
            const data = await response.json()
            throw new Error(data.detail || '로그인 실패')
          }
          
          const data = await response.json()
          set({ 
            user: data.user, 
            token: data.access_token, 
            isLoading: false,
            error: null
          })
          return true
        } catch (error) {
          set({ 
            isLoading: false, 
            error: error instanceof Error ? error.message : '로그인 실패' 
          })
          return false
        }
      },
      
      register: async (username: string, password: string, name?: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${API_BASE}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, name })
          })
          
          if (!response.ok) {
            const data = await response.json()
            throw new Error(data.detail || '회원가입 실패')
          }
          
          const data = await response.json()
          set({ 
            user: data.user, 
            token: data.access_token, 
            isLoading: false,
            error: null
          })
          return true
        } catch (error) {
          set({ 
            isLoading: false, 
            error: error instanceof Error ? error.message : '회원가입 실패' 
          })
          return false
        }
      },
      
      logout: () => {
        set({ user: null, token: null, error: null })
      },
      
      checkAuth: async () => {
        const { token } = get()
        if (!token) return false
        
        try {
          const response = await fetch(`${API_BASE}/api/auth/me`, {
            headers: { 
              'Authorization': `Bearer ${token}`
            }
          })
          
          if (!response.ok) {
            set({ user: null, token: null })
            return false
          }
          
          const user = await response.json()
          set({ user })
          return true
        } catch {
          set({ user: null, token: null })
          return false
        }
      },
      
      clearError: () => set({ error: null })
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        user: state.user, 
        token: state.token 
      })
    }
  )
)
