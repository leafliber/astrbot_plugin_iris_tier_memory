import axios, { AxiosInstance, AxiosError } from 'axios'

const apiClient: AxiosInstance = axios.create({
  baseURL: '/api/iris',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError<{ error?: string }>) => {
    const message = error.response?.data?.error || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

export default apiClient
