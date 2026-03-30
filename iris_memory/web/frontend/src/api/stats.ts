import type {
  ApiResponse,
  MemoryStats,
  TokenStatsResponse,
  KGStats,
  SystemStats
} from '@/types'
import apiClient from './request'

// 获取所有统计（合并端点，推荐）
export interface AllStatsResponse {
  memory: MemoryStats
  token: TokenStatsResponse
  kg: KGStats
  system: SystemStats
}

export const getAllStats = async (): Promise<AllStatsResponse> => {
  const response = await apiClient.get<unknown>('/stats/all') as ApiResponse<{ data: AllStatsResponse }>
  if (!response.success) {
    throw new Error(response.error || '获取统计失败')
  }
  return response.data || {
    memory: { l1: {}, l2: {}, l3: {} },
    token: {},
    kg: { node_count: 0, edge_count: 0, node_types: {}, relation_types: {} },
    system: { components: { l1_buffer: false, l2_memory: false, l3_kg: false, profile: false, llm_manager: false }, uptime: 0, version: '1.0.0' }
  }
}

// Token 统计
export const getTokenStats = async (): Promise<TokenStatsResponse> => {
  const response = await apiClient.get<unknown>('/stats/token') as ApiResponse<{ stats: TokenStatsResponse }>
  if (!response.success) {
    throw new Error(response.error || '获取Token统计失败')
  }
  return response.stats || {}
}

// 记忆统计
export const getMemoryStats = async (): Promise<MemoryStats> => {
  const response = await apiClient.get<unknown>('/stats/memory') as ApiResponse<{ stats: MemoryStats }>
  if (!response.success) {
    throw new Error(response.error || '获取记忆统计失败')
  }
  return response.stats || { l1: {}, l2: {}, l3: {} }
}

// 知识图谱统计
export const getKGStats = async (): Promise<KGStats> => {
  const response = await apiClient.get<unknown>('/stats/kg') as ApiResponse<{ stats: KGStats }>
  if (!response.success) {
    throw new Error(response.error || '获取图谱统计失败')
  }
  return response.stats || { node_count: 0, edge_count: 0, node_types: {}, relation_types: {} }
}

// 系统统计
export const getSystemStats = async (): Promise<SystemStats> => {
  const response = await apiClient.get<unknown>('/stats/system') as ApiResponse<{ stats: SystemStats }>
  if (!response.success) {
    throw new Error(response.error || '获取系统统计失败')
  }
  return response.stats || { components: { l1_buffer: false, l2_memory: false, l3_kg: false, profile: false, llm_manager: false }, uptime: 0, version: '1.0.0' }
}
