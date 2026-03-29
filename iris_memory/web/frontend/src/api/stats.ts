import api, { ApiResponse } from './request'

// Token 统计类型
export interface TokenStats {
  total_input_tokens: number
  total_output_tokens: number
  total_calls: number
}

// 记忆统计类型
export interface MemoryStats {
  l1: {
    queue_length?: number
    max_capacity?: number
  }
  l2: {
    total_count?: number
    group_count?: number
  }
  l3: {
    node_count?: number
    edge_count?: number
  }
}

// 图谱统计类型
export interface KGStats {
  node_count?: number
  edge_count?: number
  node_types?: Record<string, number>
  relation_types?: Record<string, number>
}

// 系统统计类型
export interface SystemStats {
  components: Record<string, boolean>
  uptime?: number
  version?: string
}

// 统计 API
export const statsApi = {
  // 获取 Token 统计
  getTokenStats: async (): Promise<ApiResponse<{ stats: Record<string, TokenStats> }>> => {
    return api.get('/stats/token')
  },

  // 获取记忆统计
  getMemoryStats: async (): Promise<ApiResponse<{ stats: MemoryStats }>> => {
    return api.get('/stats/memory')
  },

  // 获取图谱统计
  getKgStats: async (): Promise<ApiResponse<{ stats: KGStats }>> => {
    return api.get('/stats/kg')
  },

  // 获取系统统计
  getSystemStats: async (): Promise<ApiResponse<{ stats: SystemStats }>> => {
    return api.get('/stats/system')
  }
}
