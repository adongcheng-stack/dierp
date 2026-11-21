import axios from 'axios'
import { useAuthStore } from '../stores/authStore'
import { handleApiError, getErrorMessage } from '../utils/errorHandler'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000, // 增加到30秒
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    // 静默续期：后端在 token 即将过期时通过响应头换发新 token，前端无感更新
    const renewed = response.headers?.['x-new-access-token']
    if (renewed && typeof renewed === 'string') {
      useAuthStore.getState().setToken(renewed)
    }
    return response
  },
  (error) => {
    // 401 未授权：清鉴权状态，由 React 路由守卫跳转登录页。
    // 注意：登录接口自身的 401（账号/密码错误）不能触发整页跳转，
    // 否则登录表单的错误提示会被刷新冲掉，表现为「闪一下又回到登录页」。
    if (error.response?.status === 401) {
      const isLoginRequest = String(error.config?.url ?? '').includes('/auth/login')
      if (!isLoginRequest) {
        useAuthStore.getState().logout()
      }
      return Promise.reject(error)
    }

    // 403 权限不足：统一标记文案，交由 getErrorMessage 展示；不跳转、不清登录态。
    if (error.response?.status === 403) {
      error.userMessage = '权限不足：当前角色无权执行该操作'
    }
    
    // 其他错误使用统一错误处理（但不自动显示消息，由调用方决定）
    // 如果需要自动显示，可以取消注释下面这行
    // handleApiError(error)
    
    return Promise.reject(error)
  }
)

export default api
export { handleApiError, getErrorMessage }

