import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import api from '../services/api'

interface User {
  username: string
  email: string
  full_name: string
  role: string
  department: string
}

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  setUser: (user: User) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      login: async (username: string, password: string) => {
        const formData = new FormData()
        formData.append('username', username)
        formData.append('password', password)
        
        const response = await api.post('/auth/login', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })
        
        const { access_token } = response.data
        set({ token: access_token, isAuthenticated: true })
        
        // 获取用户信息
        api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
        const userResponse = await api.get('/auth/me')
        set({ user: userResponse.data })
      },
      logout: () => {
        set({ token: null, user: null, isAuthenticated: false })
        delete api.defaults.headers.common['Authorization']
      },
      setUser: (user: User) => set({ user }),
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
)

