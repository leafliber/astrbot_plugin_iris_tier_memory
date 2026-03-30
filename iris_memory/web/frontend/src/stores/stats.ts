import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MemoryStats, TokenStatsResponse, KGStats, SystemStats } from '@/types'
import * as statsApi from '@/api/stats'

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

  // 获取所有统计
  const fetchAllStats = async () => {
    loading.value = true
    try {
      const [memory, token, kg, system] = await Promise.all([
        statsApi.getMemoryStats(),
        statsApi.getTokenStats(),
        statsApi.getKGStats(),
        statsApi.getSystemStats()
      ])
      memoryStats.value = memory
      tokenStats.value = token
      kgStats.value = kg
      systemStats.value = system
    } catch (error) {
      console.error('获取统计数据失败:', error)
    } finally {
      loading.value = false
    }
  }

  // 获取记忆统计
  const fetchMemoryStats = async () => {
    try {
      memoryStats.value = await statsApi.getMemoryStats()
    } catch (error) {
      console.error('获取记忆统计失败:', error)
    }
  }

  // 获取 Token 统计
  const fetchTokenStats = async () => {
    try {
      tokenStats.value = await statsApi.getTokenStats()
    } catch (error) {
      console.error('获取Token统计失败:', error)
    }
  }

  // 获取图谱统计
  const fetchKGStats = async () => {
    try {
      kgStats.value = await statsApi.getKGStats()
    } catch (error) {
      console.error('获取图谱统计失败:', error)
    }
  }

  // 获取系统统计
  const fetchSystemStats = async () => {
    try {
      systemStats.value = await statsApi.getSystemStats()
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
