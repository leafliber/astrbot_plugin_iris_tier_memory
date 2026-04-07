import type {
  L1ListResponse,
  L2SearchRequest,
  L2SearchResponse,
  KGGraph,
  KGNode,
  L1QueueItem
} from '@/types'
import apiClient from './request'

interface ApiBaseResponse {
  success: boolean
  error?: string
  message?: string
}

interface L1ListApiResponse extends ApiBaseResponse, L1ListResponse {}

interface L1QueuesApiResponse extends ApiBaseResponse {
  queues: L1QueueItem[]
}

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

export const getL1Queues = async (): Promise<L1QueueItem[]> => {
  const response = await apiClient.get('/memory/l1/queues') as unknown as L1QueuesApiResponse
  if (!response.success) {
    throw new Error(response.error || '获取L1队列列表失败')
  }
  return response.queues || []
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

export const getLatestL2Memories = async (limit: number = 20, groupId?: string): Promise<L2SearchResponse> => {
  const params: Record<string, unknown> = { limit }
  if (groupId) {
    params.group_id = groupId
  }
  const response = await apiClient.get('/memory/l2/latest', { params }) as unknown as L2SearchApiResponse
  if (!response.success) {
    throw new Error(response.error || '获取最新L2记忆失败')
  }
  return { results: response.results || [] }
}

export const getL3Graph = async (params?: L3GraphParams): Promise<L3GraphApiResponse> => {
  const response = await apiClient.get('/memory/l3/graph', { params }) as unknown as L3GraphApiResponse
  if (!response.success) {
    throw new Error(response.error || response.message || '获取L3图谱失败')
  }
  return response
}

export interface L3SearchNodeResult {
  id: string
  label: string
  name: string
  content: string
  confidence: number
}

export interface L3SearchEdgeResult {
  source: {
    id: string
    label: string
    name: string
  }
  target: {
    id: string
    label: string
    name: string
  }
  relation: string
  confidence: number
}

interface L3SearchNodesApiResponse extends ApiBaseResponse {
  nodes: L3SearchNodeResult[]
}

interface L3SearchEdgesApiResponse extends ApiBaseResponse {
  edges: L3SearchEdgeResult[]
}

export const searchL3Nodes = async (keyword: string, limit: number = 20): Promise<L3SearchNodeResult[]> => {
  const response = await apiClient.get('/memory/l3/search/nodes', { 
    params: { keyword, limit } 
  }) as unknown as L3SearchNodesApiResponse
  if (!response.success) {
    throw new Error(response.error || '搜索节点失败')
  }
  return response.nodes || []
}

export const searchL3Edges = async (keyword: string, limit: number = 20): Promise<L3SearchEdgeResult[]> => {
  const response = await apiClient.get('/memory/l3/search/edges', { 
    params: { keyword, limit } 
  }) as unknown as L3SearchEdgesApiResponse
  if (!response.success) {
    throw new Error(response.error || '搜索边失败')
  }
  return response.edges || []
}
