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
    return response
  },
  (error) => {
    // 401未授权，跳转登录
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
      return Promise.reject(error)
    }
    
    // 其他错误使用统一错误处理（但不自动显示消息，由调用方决定）
    // 如果需要自动显示，可以取消注释下面这行
    // handleApiError(error)
    
    return Promise.reject(error)
  }
)

export default api
export { handleApiError, getErrorMessage }

