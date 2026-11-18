/**
 * 统一错误处理工具
 */

/** 与 antd App.useApp() 返回的 message 实例兼容的最小接口 */
interface MessageNotifier {
  error: (content: string) => void
}

interface ErrorResponse {
  error_code?: string
  message?: string
  detail?: string | {
    error_code?: string
    message?: string
    [key: string]: any
  }
}

/**
 * 处理API错误响应
 */
export const handleApiError = (error: any, notifier?: MessageNotifier): void => {
  let errorMessage = '操作失败'
  
  if (error?.response?.data) {
    const errorData: ErrorResponse = error.response.data
    
    // 处理统一错误格式
    if (typeof errorData.detail === 'object' && errorData.detail?.message) {
      errorMessage = errorData.detail.message
    } else if (typeof errorData.detail === 'string') {
      errorMessage = errorData.detail
    } else if (errorData.message) {
      errorMessage = errorData.message
    }
  } else if (error?.message) {
    errorMessage = error.message
  }
  
  // 使用调用方通过 App.useApp() 取得的 message 实例，避免 antd 静态方法告警
  if (notifier) {
    notifier.error(errorMessage)
  } else {
    console.error(errorMessage)
  }
}

/**
 * 获取错误信息
 */
export const getErrorMessage = (error: any): string => {
  if (error?.response?.data) {
    const errorData: ErrorResponse = error.response.data
    
    if (typeof errorData.detail === 'object' && errorData.detail?.message) {
      return errorData.detail.message
    } else if (typeof errorData.detail === 'string') {
      return errorData.detail
    } else if (errorData.message) {
      return errorData.message
    }
  }
  
  return error?.message || '操作失败'
}

/**
 * 获取错误代码
 */
export const getErrorCode = (error: any): string | undefined => {
  if (error?.response?.data) {
    const errorData: ErrorResponse = error.response.data
    
    if (typeof errorData.detail === 'object' && errorData.detail?.error_code) {
      return errorData.detail.error_code
    } else if (errorData.error_code) {
      return errorData.error_code
    }
  }
  
  return undefined
}

