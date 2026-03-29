import { defineStore } from 'pinia'
import { ref } from 'vue'
import { memoryApi, type MemoryResult } from '@/api/memory'

export const useMemoryStore = defineStore('memory', () => {
  // 状态
  const searchQuery = ref('')
  const searchResults = ref<MemoryResult[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 搜索记忆
  async function searchMemory(query: string, groupId?: string) {
    if (!query.trim()) return

    loading.value = true
    error.value = null

    try {
      const response = await memoryApi.searchL2(query, groupId)

      if (response.success && response.data) {
        searchResults.value = response.data.results
      } else {
        error.value = response.error || '搜索失败'
      }
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  // 清空搜索
  function clearSearch() {
    searchQuery.value = ''
    searchResults.value = []
    error.value = null
  }

  return {
    searchQuery,
    searchResults,
    loading,
    error,
    searchMemory,
    clearSearch
  }
})
