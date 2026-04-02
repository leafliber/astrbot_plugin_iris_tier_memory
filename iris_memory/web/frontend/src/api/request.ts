import axios, { AxiosInstance, AxiosError } from 'axios'

const TOKEN_KEY = 'iris_jwt_token'

function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

const apiClient: AxiosInstance = axios.create({
  baseURL: '/api/iris',
  timeout: 30000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.request.use(
  (config) => {
    const token = getStoredToken()
    if (token) {
      config.params = { ...config.params, token }
    }
    return config
  },
  (error) => Promise.reject(error)
)

apiClient.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError<{ error?: string; code?: string }>) => {
    const message = error.response?.data?.error || error.message || '请求失败'
    const code = error.response?.data?.code
    
    if (code === 'UNAUTHORIZED' || error.response?.status === 401) {
      console.warn('未登录，需要先登录 AstrBot Dashboard')
      clearStoredToken()
    }
    
    return Promise.reject(new Error(message))
  }
)

export default apiClient
