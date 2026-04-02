import axios, { AxiosInstance, AxiosError } from 'axios'

const apiClient: AxiosInstance = axios.create({
  baseURL: '/api/iris',
  timeout: 30000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError<{ error?: string; code?: string }>) => {
    const message = error.response?.data?.error || error.message || '请求失败'
    const code = error.response?.data?.code
    
    if (code === 'UNAUTHORIZED' || error.response?.status === 401) {
      console.warn('未登录，需要先登录 AstrBot Dashboard')
    }
    
    return Promise.reject(new Error(message))
  }
)

export default apiClient
