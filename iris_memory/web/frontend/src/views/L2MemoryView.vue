<template>
  <div class="l2-memory-view">
    <ComponentDisabled
      :status="status"
      :error="error"
      :error-type="errorType"
      component-name="L2 记忆"
      @retry="refreshState"
    >
      <v-row>
        <v-col cols="12">
          <v-card color="surface" variant="flat">
            <v-tabs v-model="activeTab" color="primary" grow>
              <v-tab value="latest">
                <v-icon icon="mdi-clock-outline" class="mr-2" />
                最新记忆
              </v-tab>
              <v-tab value="search">
                <v-icon icon="mdi-magnify" class="mr-2" />
                记忆搜索
              </v-tab>
            </v-tabs>
          </v-card>
        </v-col>
      </v-row>

      <v-window v-model="activeTab" class="mt-4">
        <v-window-item value="latest">
          <v-row>
            <v-col cols="12">
              <v-card color="surface" variant="flat">
                <v-card-title class="d-flex align-center">
                  <v-icon icon="mdi-clock-outline" color="secondary" class="mr-2" />
                  最新记忆
                  <v-spacer />
                  <v-select
                    v-model="selectedLimit"
                    :items="limitOptions"
                    label="显示数量"
                    variant="outlined"
                    density="compact"
                    hide-details
                    style="max-width: 120px"
                    @update:model-value="handleLimitChange"
                  />
                </v-card-title>
                <v-card-text>
                  <v-progress-linear
                    v-if="memoryStore.l2LatestLoading"
                    indeterminate
                    color="primary"
                  />

                  <div v-else-if="memoryStore.l2LatestResults.length > 0">
                    <v-card
                      v-for="(result, index) in memoryStore.l2LatestResults"
                      :key="index"
                      variant="outlined"
                      class="mb-3"
                    >
                      <v-card-text>
                        <div class="d-flex align-start">
                          <v-chip
                            color="secondary"
                            size="small"
                            class="mr-3 mt-1"
                          >
                            #{{ index + 1 }}
                          </v-chip>
                          <div class="flex-grow-1">
                            <div class="text-body-1 text-wrap">{{ result.content }}</div>
                            <div class="d-flex align-center mt-2 text-caption text-medium-emphasis">
                              <v-icon icon="mdi-clock-outline" size="small" class="mr-1" />
                              {{ formatTime(result.timestamp) }}
                              <template v-if="result.metadata?.group_id">
                                <v-icon icon="mdi-account-group" size="small" class="ml-3 mr-1" />
                                {{ result.metadata.group_id }}
                              </template>
                            </div>
                          </div>
                        </div>
                      </v-card-text>
                    </v-card>
                  </div>

                  <div v-else class="text-center text-medium-emphasis py-12">
                    <v-icon icon="mdi-database-outline" size="80" class="mb-3" />
                    <div class="text-h6">暂无记忆数据</div>
                    <div class="text-body-2 mt-2">
                      L2 记忆库为空或数据加载失败
                    </div>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-window-item>

        <v-window-item value="search">
          <v-row>
            <v-col cols="12">
              <v-card color="surface" variant="flat">
                <v-card-title class="d-flex align-center">
                  <v-icon icon="mdi-database-search" color="secondary" class="mr-2" />
                  L2 记忆搜索
                </v-card-title>
                <v-card-text>
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="searchQuery"
                        placeholder="输入关键词搜索记忆..."
                        prepend-inner-icon="mdi-magnify"
                        variant="outlined"
                        density="comfortable"
                        hide-details
                        clearable
                        @keyup.enter="handleSearch"
                      />
                    </v-col>
                    <v-col cols="12" md="3">
                      <v-text-field
                        v-model="groupIdFilter"
                        placeholder="群聊 ID（可选）"
                        prepend-inner-icon="mdi-account-group"
                        variant="outlined"
                        density="comfortable"
                        hide-details
                        clearable
                      />
                    </v-col>
                    <v-col cols="12" md="3">
                      <v-btn
                        color="primary"
                        size="large"
                        block
                        :loading="memoryStore.l2Loading"
                        @click="handleSearch"
                      >
                        <v-icon icon="mdi-magnify" class="mr-1" />
                        搜索
                      </v-btn>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <v-row class="mt-4">
            <v-col cols="12">
              <v-card color="surface" variant="flat">
                <v-card-title class="d-flex align-center">
                  <span>搜索结果</span>
                  <v-spacer />
                  <v-chip v-if="memoryStore.l2Results.length > 0" size="small" color="secondary" variant="tonal">
                    {{ memoryStore.l2Results.length }} 条结果
                  </v-chip>
                </v-card-title>
                <v-card-text>
                  <v-progress-linear
                    v-if="memoryStore.l2Loading"
                    indeterminate
                    color="primary"
                  />

                  <div v-else-if="memoryStore.l2Results.length > 0">
                    <v-card
                      v-for="(result, index) in memoryStore.l2Results"
                      :key="index"
                      variant="outlined"
                      class="mb-3"
                    >
                      <v-card-text>
                        <div class="d-flex align-start">
                          <v-chip
                            :color="getScoreColor(result.score)"
                            size="small"
                            class="mr-3 mt-1"
                          >
                            {{ (result.score * 100).toFixed(0) }}%
                          </v-chip>
                          <div class="flex-grow-1">
                            <div class="text-body-1 text-wrap">{{ result.content }}</div>
                            <div class="d-flex align-center mt-2 text-caption text-medium-emphasis">
                              <v-icon icon="mdi-clock-outline" size="small" class="mr-1" />
                              {{ formatTime(result.timestamp) }}
                              <template v-if="result.metadata?.group_id">
                                <v-icon icon="mdi-account-group" size="small" class="ml-3 mr-1" />
                                {{ result.metadata.group_id }}
                              </template>
                            </div>
                          </div>
                        </div>
                      </v-card-text>
                    </v-card>
                  </div>

                  <div v-else class="text-center text-medium-emphasis py-12">
                    <v-icon icon="mdi-database-search-outline" size="80" class="mb-3" />
                    <div class="text-h6">
                      {{ memoryStore.l2Query ? '未找到相关记忆' : '输入关键词搜索记忆' }}
                    </div>
                    <div class="text-body-2 mt-2">
                      {{ memoryStore.l2Query ? '尝试使用其他关键词' : 'L2 记忆支持语义检索' }}
                    </div>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-window-item>
      </v-window>

      <v-row class="mt-4">
        <v-col cols="12">
          <v-card color="surface" variant="flat">
            <v-card-title>
              <v-icon icon="mdi-information" class="mr-2" />
              L2 记忆说明
            </v-card-title>
            <v-card-text>
              <v-alert type="info" variant="tonal" density="compact">
                <div class="text-body-2">
                  <strong>L2 记忆（Episodic Memory）</strong> 是长期记忆存储，基于 RIF 评分动态管理，支持选择性遗忘。
                  使用向量检索技术，可以语义相似度搜索历史对话内容。
                </div>
              </v-alert>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </ComponentDisabled>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useMemoryStore } from '@/stores'
import { useComponentState } from '@/composables/useComponentState'
import ComponentDisabled from '@/components/ComponentDisabled.vue'

const memoryStore = useMemoryStore()
const { status, error, errorType, refreshState } = useComponentState('l2_memory')

const activeTab = ref('latest')
const searchQuery = ref('')
const groupIdFilter = ref('')
const selectedLimit = ref(20)

const limitOptions = [
  { title: '10 条', value: 10 },
  { title: '20 条', value: 20 },
  { title: '50 条', value: 50 },
  { title: '100 条', value: 100 }
]

const handleLimitChange = (value: number) => {
  memoryStore.setL2LatestLimit(value)
  memoryStore.fetchLatestL2Memories(value)
}

const handleSearch = () => {
  if (searchQuery.value.trim()) {
    memoryStore.searchL2Memory(
      searchQuery.value.trim(),
      groupIdFilter.value || undefined
    )
  }
}

const getScoreColor = (score: number): string => {
  if (score >= 0.9) return 'success'
  if (score >= 0.7) return 'info'
  if (score >= 0.5) return 'warning'
  return 'error'
}

const formatTime = (timestamp?: string): string => {
  if (!timestamp) return '未知时间'
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return timestamp
  }
}

const handleRefresh = () => {
  if (activeTab.value === 'latest') {
    memoryStore.fetchLatestL2Memories()
  } else if (searchQuery.value.trim()) {
    handleSearch()
  }
}

watch(activeTab, (newTab) => {
  if (newTab === 'latest' && memoryStore.l2LatestResults.length === 0) {
    memoryStore.fetchLatestL2Memories()
  }
})

onMounted(() => {
  window.addEventListener('iris:refresh', handleRefresh)
  if (activeTab.value === 'latest') {
    memoryStore.fetchLatestL2Memories()
  }
})

onUnmounted(() => {
  window.removeEventListener('iris:refresh', handleRefresh)
})
</script>
