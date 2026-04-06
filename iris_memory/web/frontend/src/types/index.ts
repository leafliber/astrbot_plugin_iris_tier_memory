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
// 组件状态类型
// ============================================

export type ComponentStatus = 'pending' | 'initializing' | 'available' | 'unavailable'

export type ErrorType = 'disabled' | 'dependency_missing' | 'connection_failed' | 'other'

export interface ComponentState {
  status: ComponentStatus
  error: string | null
  error_type: ErrorType | null
}

export type GlobalStatus = 'pending' | 'initializing' | 'available'

export interface ComponentStates {
  [key: string]: ComponentState
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

// L1 队列项
export interface L1QueueItem {
  group_id: string
  message_count: number
  total_tokens: number
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
  current_topic?: string
  active_users?: string[]
  interests?: string[]
  active_time_slots?: string[]
  atmosphere_tags?: string[]
  common_expressions?: string[]
  long_term_tags?: string[]
  blacklist_topics?: string[]
  last_interaction_time?: string
}

// 用户画像
export interface UserProfile {
  user_id: string
  user_name?: string
  historical_names?: string[]
  current_emotional_state?: string
  personality_tags?: string[]
  interests?: string[]
  occupation?: string
  language_style?: string
  bot_relationship?: string
  important_dates?: Array<{ date: string; description: string }>
  taboo_topics?: string[]
  important_events?: string[]
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

// 系统统计（新格式）
export interface SystemStats {
  components: ComponentStates
  global_status: GlobalStatus
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
  kg: KGStats
}

// ============================================
// 组件状态映射
// ============================================

export const COMPONENT_DISPLAY_NAMES: Record<string, string> = {
  l1_buffer: 'L1 缓冲',
  l2_memory: 'L2 记忆',
  l3_kg: 'L3 图谱',
  profile: '画像管理',
  llm_manager: 'LLM 管理器'
}

export const ERROR_TYPE_DISPLAY_NAMES: Record<ErrorType, string> = {
  disabled: '已禁用',
  dependency_missing: '依赖缺失',
  connection_failed: '连接失败',
  other: '其他原因'
}

export const STATUS_DISPLAY_NAMES: Record<ComponentStatus, string> = {
  pending: '等待初始化',
  initializing: '正在初始化',
  available: '可用',
  unavailable: '不可用'
}
