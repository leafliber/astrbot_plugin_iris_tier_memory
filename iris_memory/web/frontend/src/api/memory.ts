import api, { ApiResponse } from './request'

// 记忆结果类型
export interface MemoryResult {
  content: string
  score: number
  metadata: Record<string, any>
  timestamp?: string
}

// 消息类型
export interface Message {
  role: string
  content: string
  timestamp?: string
  user_id?: string
}

// 图谱节点类型
export interface GraphNode {
  id: string
  label: string
  name: string
  confidence: number
}

// 图谱边类型
export interface GraphEdge {
  source: string
  target: string
  relation: string
}

// 记忆 API
export const memoryApi = {
  // 搜索 L2 记忆
  searchL2: async (
    query: string,
    groupId?: string,
    topK: number = 10
  ): Promise<ApiResponse<{ results: MemoryResult[] }>> => {
    return api.post('/memory/l2/search', {
      query,
      group_id: groupId,
      top_k: topK
    })
  },

  // 获取 L1 缓冲列表
  listL1: async (
    groupId?: string
  ): Promise<ApiResponse<{ messages: Message[]; count: number }>> => {
    return api.get('/memory/l1/list', {
      params: { group_id: groupId }
    })
  },

  // 获取 L3 图谱数据
  getL3Graph: async (
    groupId?: string
  ): Promise<ApiResponse<{ nodes: GraphNode[]; edges: GraphEdge[] }>> => {
    return api.get('/memory/l3/graph', {
      params: { group_id: groupId }
    })
  },

  // 获取 L2 统计
  getL2Stats: async (): Promise<ApiResponse<{ stats: any }>> => {
    return api.get('/memory/l2/stats')
  }
}
