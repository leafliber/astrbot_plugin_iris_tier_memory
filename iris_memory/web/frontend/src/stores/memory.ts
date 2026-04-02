import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { L1Message, L2Memory, KGGraph, KGNode, L1QueueItem } from '@/types'
import * as memoryApi from '@/api/memory'

export const useMemoryStore = defineStore('memory', () => {
  // L1 缓冲
  const l1Messages = ref<L1Message[]>([])
  const l1Loading = ref(false)
  const l1Queues = ref<L1QueueItem[]>([])
  const l1QueuesLoading = ref(false)

  // L2 记忆
  const l2Results = ref<L2Memory[]>([])
  const l2Loading = ref(false)
  const l2Query = ref('')
  const l2TotalCount = ref(0)
  const l2GroupCount = ref(0)

  // L3 图谱
  const l3Graph = ref<KGGraph>({ nodes: [], edges: [] })
  const l3StartNode = ref<KGNode | null>(null)
  const l3Loading = ref(false)
  const l3Depth = ref(2)

  // 获取 L1 缓冲
  const fetchL1Messages = async (groupId?: string) => {
    l1Loading.value = true
    try {
      const response = await memoryApi.getL1Messages(groupId)
      l1Messages.value = response.messages
    } catch (error) {
      console.error('获取L1缓冲失败:', error)
      l1Messages.value = []
    } finally {
      l1Loading.value = false
    }
  }

  // 获取 L1 队列列表
  const fetchL1Queues = async () => {
    l1QueuesLoading.value = true
    try {
      l1Queues.value = await memoryApi.getL1Queues()
    } catch (error) {
      console.error('获取L1队列列表失败:', error)
      l1Queues.value = []
    } finally {
      l1QueuesLoading.value = false
    }
  }

  // 搜索 L2 记忆
  const searchL2Memory = async (query: string, groupId?: string, topK = 10) => {
    l2Loading.value = true
    l2Query.value = query
    try {
      const response = await memoryApi.searchL2Memory({ query, group_id: groupId, top_k: topK })
      l2Results.value = response.results
    } catch (error) {
      console.error('搜索L2记忆失败:', error)
      l2Results.value = []
    } finally {
      l2Loading.value = false
    }
  }

  // 获取 L2 统计
  const fetchL2Stats = async () => {
    try {
      const stats = await memoryApi.getL2Stats()
      l2TotalCount.value = stats.total_count || 0
      l2GroupCount.value = stats.group_count || 0
    } catch (error) {
      console.error('获取L2统计失败:', error)
    }
  }

  // 获取 L3 图谱（支持拓展）
  const fetchL3Graph = async (nodeId?: string) => {
    l3Loading.value = true
    try {
      const response = await memoryApi.getL3Graph({
        node_id: nodeId,
        depth: l3Depth.value
      })
      l3Graph.value = {
        nodes: response.nodes || [],
        edges: response.edges || []
      }
      l3StartNode.value = response.start_node
    } catch (error) {
      console.error('获取L3图谱失败:', error)
      l3Graph.value = { nodes: [], edges: [] }
      l3StartNode.value = null
    } finally {
      l3Loading.value = false
    }
  }

  // 从指定节点拓展
  const expandFromNode = async (nodeId: string) => {
    l3Loading.value = true
    try {
      const response = await memoryApi.getL3Graph({
        node_id: nodeId,
        depth: l3Depth.value
      })
      l3Graph.value = {
        nodes: response.nodes || [],
        edges: response.edges || []
      }
      l3StartNode.value = response.start_node
    } catch (error) {
      console.error('拓展图谱失败:', error)
    } finally {
      l3Loading.value = false
    }
  }

  // 设置拓展深度
  const setDepth = (depth: number) => {
    l3Depth.value = depth
  }

  // 清除搜索结果
  const clearL2Results = () => {
    l2Results.value = []
    l2Query.value = ''
  }

  return {
    l1Messages,
    l1Loading,
    l1Queues,
    l1QueuesLoading,
    l2Results,
    l2Loading,
    l2Query,
    l2TotalCount,
    l2GroupCount,
    l3Graph,
    l3StartNode,
    l3Loading,
    l3Depth,
    fetchL1Messages,
    fetchL1Queues,
    searchL2Memory,
    fetchL2Stats,
    fetchL3Graph,
    expandFromNode,
    setDepth,
    clearL2Results
  }
})
