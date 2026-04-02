import type {
  MemoryStats,
  TokenStatsResponse,
  KGStats,
  SystemStats
} from '@/types'
import apiClient from './request'

interface ApiBaseResponse {
  success: boolean
  error?: string
}

export interface AllStatsResponse {
  memory: MemoryStats
  token: TokenStatsResponse
  kg: KGStats
  system: SystemStats
}

interface AllStatsApiResponse extends ApiBaseResponse {
  data: AllStatsResponse
}

interface TokenStatsApiResponse extends ApiBaseResponse {
  stats: TokenStatsResponse
}

interface MemoryStatsApiResponse extends ApiBaseResponse {
  stats: MemoryStats
}

interface KGStatsApiResponse extends ApiBaseResponse {
  stats: KGStats
}

interface SystemStatsApiResponse extends ApiBaseResponse {
  stats: SystemStats
}

export const getAllStats = async (): Promise<AllStatsResponse> => {
  const response = await apiClient.get('/stats/all') as unknown as AllStatsApiResponse
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

export const getTokenStats = async (): Promise<TokenStatsResponse> => {
  const response = await apiClient.get('/stats/token') as unknown as TokenStatsApiResponse
  if (!response.success) {
    throw new Error(response.error || '获取Token统计失败')
  }
  return response.stats || {}
}

export const getMemoryStats = async (): Promise<MemoryStats> => {
  const response = await apiClient.get('/stats/memory') as unknown as MemoryStatsApiResponse
  if (!response.success) {
    throw new Error(response.error || '获取记忆统计失败')
  }
  return response.stats || { l1: {}, l2: {}, l3: {} }
}

export const getKGStats = async (): Promise<KGStats> => {
  const response = await apiClient.get('/stats/kg') as unknown as KGStatsApiResponse
  if (!response.success) {
    throw new Error(response.error || '获取图谱统计失败')
  }
  return response.stats || { node_count: 0, edge_count: 0, node_types: {}, relation_types: {} }
}

export const getSystemStats = async (): Promise<SystemStats> => {
  const response = await apiClient.get('/stats/system') as unknown as SystemStatsApiResponse
  if (!response.success) {
    throw new Error(response.error || '获取系统统计失败')
  }
  return response.stats || { components: { l1_buffer: false, l2_memory: false, l3_kg: false, profile: false, llm_manager: false }, uptime: 0, version: '1.0.0' }
}
