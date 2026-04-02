// ============================================
// API 类型定义
// ============================================

// 通用响应
export interface ApiResponse<T = unknown> {
  success: boolean
  error?: string
  data?: T
}

// ============================================
// 记忆相关类型
// ============================================

// L1 消息
export interface L1Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
  user_id?: string
}

// L2 记忆条目
export interface L2Memory {
  content: string
  score: number
  metadata: Record<string, unknown>
  timestamp?: string
}

// L3 图谱节点
export interface KGNode {
  id: string
  label: string
  name: string
  confidence: number
}

// L3 图谱边
export interface KGEdge {
  source: string
  target: string
  relation: string
}

// L3 图谱
export interface KGGraph {
  nodes: KGNode[]
  edges: KGEdge[]
}

// L2 搜索请求
export interface L2SearchRequest {
  query: string
  group_id?: string
  top_k?: number
}

// L2 搜索结果
export interface L2SearchResponse {
  results: L2Memory[]
}

// L1 列表响应
export interface L1ListResponse {
  messages: L1Message[]
  count: number
}

// ============================================
// 画像相关类型
// ============================================

// 群聊画像
export interface GroupProfile {
  group_id: string
  group_name?: string
  atmosphere_tags?: string[]
  active_users?: string[]
  interests?: string[]
  member_count?: number
  last_interaction_time?: string
}

// 用户画像
export interface UserProfile {
  user_id: string
  user_name?: string
  interests?: string[]
  personality_tags?: string[]
  last_interaction_time?: string
}

// 群聊列表项
export interface GroupListItem {
  group_id: string
  group_name?: string
  member_count?: number
}

// 用户列表项
export interface UserListItem {
  user_id: string
  nickname?: string
  group_id?: string
}

// ============================================
// 统计相关类型
// ============================================

// Token 统计
export interface TokenStats {
  total_input_tokens: number
  total_output_tokens: number
  total_calls: number
}

export interface TokenStatsResponse {
  global: TokenStats
  l1_summarizer: TokenStats
  [key: string]: TokenStats
}

// L1 统计
export interface L1Stats {
  total_messages?: number
  max_capacity?: number
}

// L2 统计
export interface L2Stats {
  total_count?: number
  group_count?: number
}

// L3 统计
export interface L3Stats {
  node_count?: number
  edge_count?: number
  node_types?: Record<string, number>
  relation_types?: Record<string, number>
}

// 记忆统计
export interface MemoryStats {
  l1: L1Stats
  l2: L2Stats
  l3: L3Stats
}

// 系统组件状态
export interface SystemComponents {
  l1_buffer: boolean
  l2_memory: boolean
  l3_kg: boolean
  profile: boolean
  llm_manager: boolean
}

// 系统统计
export interface SystemStats {
  components: SystemComponents
  uptime: number
  version: string
}

// 知识图谱统计
export interface KGStats {
  node_count: number
  edge_count: number
  node_types: Record<string, number>
  relation_types: Record<string, number>
}

// ============================================
// 仪表盘类型
// ============================================

export interface DashboardData {
  system: SystemStats
  memory: MemoryStats
  token: TokenStatsResponse
}
