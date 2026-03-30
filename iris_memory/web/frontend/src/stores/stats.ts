import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MemoryStats, TokenStatsResponse, KGStats, SystemStats } from '@/types'
import { getAllStats, getMemoryStats, getTokenStats, getKGStats, getSystemStats } from '@/api/stats'

export const useStatsStore = defineStore('stats', () => {
  // 加载状态
  const loading = ref(false)

  // 记忆统计
  const memoryStats = ref<MemoryStats | null>(null)

  // Token 统计
  const tokenStats = ref<TokenStatsResponse | null>(null)

  // 图谱统计
  const kgStats = ref<KGStats | null>(null)

  // 系统统计
  const systemStats = ref<SystemStats | null>(null)

  // 获取所有统计（合并请求，推荐）
  const fetchAllStats = async () => {
    loading.value = true
    try {
      const data = await getAllStats()
      memoryStats.value = data.memory
      tokenStats.value = data.token
      kgStats.value = data.kg
      systemStats.value = data.system
    } catch (error) {
      console.error('获取统计数据失败:', error)
    } finally {
      loading.value = false
    }
  }

  // 获取记忆统计
  const fetchMemoryStats = async () => {
    try {
      memoryStats.value = await getMemoryStats()
    } catch (error) {
      console.error('获取记忆统计失败:', error)
    }
  }

  // 获取 Token 统计
  const fetchTokenStats = async () => {
    try {
      tokenStats.value = await getTokenStats()
    } catch (error) {
      console.error('获取Token统计失败:', error)
    }
  }

  // 获取图谱统计
  const fetchKGStats = async () => {
    try {
      kgStats.value = await getKGStats()
    } catch (error) {
      console.error('获取图谱统计失败:', error)
    }
  }

  // 获取系统统计
  const fetchSystemStats = async () => {
    try {
      systemStats.value = await getSystemStats()
    } catch (error) {
      console.error('获取系统统计失败:', error)
    }
  }

  return {
    loading,
    memoryStats,
    tokenStats,
    kgStats,
    systemStats,
    fetchAllStats,
    fetchMemoryStats,
    fetchTokenStats,
    fetchKGStats,
    fetchSystemStats
  }
})
