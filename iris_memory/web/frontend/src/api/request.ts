import axios, { AxiosInstance, AxiosError } from 'axios'

// API 响应格式
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  code?: string
}

// 创建 Axios 实例
const api: AxiosInstance = axios.create({
  baseURL: '/api/iris',
  timeout: 10000,
  withCredentials: true,  // 自动携带 Cookie（JWT Token）
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // JWT Token 在 Cookie 中自动携带，无需手动添加
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error: AxiosError<ApiResponse>) => {
    // 处理认证错误
    if (error.response?.status === 401) {
      // 未登录，跳转到 AstrBot 登录页
      const redirect = encodeURIComponent(window.location.pathname)
      window.location.href = `/dashboard/login?redirect=${redirect}`
    }

    // 返回错误信息
    const errorMessage = error.response?.data?.error || error.message
    return Promise.reject(new Error(errorMessage))
  }
)

export default api
