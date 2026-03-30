import type {
  ApiResponse,
  MemoryStats,
  TokenStatsResponse,
  KGStats,
  SystemStats
} from '@/types'
import apiClient from './request'

// Token 统计
export const getTokenStats = async (): Promise<TokenStatsResponse> => {
  const response = await apiClient.get<ApiResponse<TokenStatsResponse>>('/stats/token')
  if (!response.success) {
    throw new Error(response.error || '获取Token统计失败')
  }
  return response.data!
}

// 记忆统计
export const getMemoryStats = async (): Promise<MemoryStats> => {
  const response = await apiClient.get<ApiResponse<MemoryStats>>('/stats/memory')
  if (!response.success) {
    throw new Error(response.error || '获取记忆统计失败')
  }
  return response.data!
}

// 知识图谱统计
export const getKGStats = async (): Promise<KGStats> => {
  const response = await apiClient.get<ApiResponse<KGStats>>('/stats/kg')
  if (!response.success) {
    throw new Error(response.error || '获取图谱统计失败')
  }
  return response.data!
}

// 系统统计
export const getSystemStats = async (): Promise<SystemStats> => {
  const response = await apiClient.get<ApiResponse<SystemStats>>('/stats/system')
  if (!response.success) {
    throw new Error(response.error || '获取系统统计失败')
  }
  return response.data!
}
