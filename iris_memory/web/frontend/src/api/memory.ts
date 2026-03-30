import type {
  ApiResponse,
  L1ListResponse,
  L2SearchRequest,
  L2SearchResponse,
  KGGraph
} from '@/types'
import apiClient from './request'

// L1 缓冲
export const getL1Messages = async (groupId?: string): Promise<L1ListResponse> => {
  const params = groupId ? { group_id: groupId } : {}
  const response = await apiClient.get<unknown>('/memory/l1/list', { params }) as ApiResponse<L1ListResponse>
  if (!response.success) {
    throw new Error(response.error || '获取L1缓冲失败')
  }
  return {
    messages: response.results?.messages || [],
    count: response.results?.count || 0
  }
}

// L2 搜索
export const searchL2Memory = async (params: L2SearchRequest): Promise<L2SearchResponse> => {
  const response = await apiClient.post<unknown>('/memory/l2/search', params) as ApiResponse<{ results: L2SearchResponse['results'] }>
  if (!response.success) {
    throw new Error(response.error || '搜索L2记忆失败')
  }
  return { results: response.results || [] }
}

// L2 统计
export const getL2Stats = async (): Promise<{ total_count: number; group_count: number }> => {
  const response = await apiClient.get<unknown>('/memory/l2/stats') as ApiResponse<{ stats: { total_count: number; group_count: number } }>
  if (!response.success) {
    throw new Error(response.error || '获取L2统计失败')
  }
  return response.stats || { total_count: 0, group_count: 0 }
}

// L3 图谱
export const getL3Graph = async (groupId?: string): Promise<KGGraph> => {
  const params = groupId ? { group_id: groupId } : {}
  const response = await apiClient.get<unknown>('/memory/l3/graph', { params }) as ApiResponse<KGGraph>
  if (!response.success) {
    throw new Error(response.error || '获取L3图谱失败')
  }
  return {
    nodes: response.nodes || [],
    edges: response.edges || []
  }
}
