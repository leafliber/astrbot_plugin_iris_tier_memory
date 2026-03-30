import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  // 加载状态
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 选中的群聊
  const selectedGroupId = ref<string | null>(null)

  // 主题
  const darkMode = ref(true)

  // 设置加载状态
  const setLoading = (value: boolean) => {
    loading.value = value
  }

  // 设置错误
  const setError = (msg: string | null) => {
    error.value = msg
  }

  // 清除错误
  const clearError = () => {
    error.value = null
  }

  // 选中群聊
  const selectGroup = (groupId: string | null) => {
    selectedGroupId.value = groupId
  }

  // 切换主题
  const toggleTheme = () => {
    darkMode.value = !darkMode.value
  }

  return {
    loading,
    error,
    selectedGroupId,
    darkMode,
    setLoading,
    setError,
    clearError,
    selectGroup,
    toggleTheme
  }
})
