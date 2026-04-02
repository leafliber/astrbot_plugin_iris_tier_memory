import type {
  L1ListResponse,
  L2SearchRequest,
  L2SearchResponse,
  KGGraph,
  KGNode
} from '@/types'
import apiClient from './request'

interface ApiBaseResponse {
  success: boolean
  error?: string
  message?: string
}

interface L1ListApiResponse extends ApiBaseResponse, L1ListResponse {}

interface L2SearchApiResponse extends ApiBaseResponse {
  results: L2SearchResponse['results']
}

interface L2StatsApiResponse extends ApiBaseResponse {
  stats: { total_count: number; group_count: number }
}

interface L3GraphApiResponse extends ApiBaseResponse {
  start_node: KGNode | null
  nodes: KGGraph['nodes']
  edges: KGGraph['edges']
}

export interface L3GraphParams {
  node_id?: string
  depth?: number
  max_nodes?: number
  max_edges?: number
}

export const getL1Messages = async (groupId?: string): Promise<L1ListResponse> => {
  const params = groupId ? { group_id: groupId } : {}
  const response = await apiClient.get('/memory/l1/list', { params }) as unknown as L1ListApiResponse
  if (!response.success) {
    throw new Error(response.error || '获取L1缓冲失败')
  }
  return {
    messages: response.messages || [],
    count: response.count || 0
  }
}

export const searchL2Memory = async (params: L2SearchRequest): Promise<L2SearchResponse> => {
  const response = await apiClient.post('/memory/l2/search', params) as unknown as L2SearchApiResponse
  if (!response.success) {
    throw new Error(response.error || '搜索L2记忆失败')
  }
  return { results: response.results || [] }
}

export const getL2Stats = async (): Promise<{ total_count: number; group_count: number }> => {
  const response = await apiClient.get('/memory/l2/stats') as unknown as L2StatsApiResponse
  if (!response.success) {
    throw new Error(response.error || '获取L2统计失败')
  }
  return response.stats || { total_count: 0, group_count: 0 }
}

export const getL3Graph = async (params?: L3GraphParams): Promise<L3GraphApiResponse> => {
  const response = await apiClient.get('/memory/l3/graph', { params }) as unknown as L3GraphApiResponse
  if (!response.success) {
    throw new Error(response.error || response.message || '获取L3图谱失败')
  }
  return response
}
