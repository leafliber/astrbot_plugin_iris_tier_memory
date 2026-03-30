<template>
  <div class="memory-view">
    <v-tabs v-model="activeTab" color="primary" align-tabs="start">
      <v-tab value="l1">
        <v-icon icon="mdi-lightning-bolt" class="mr-1" />
        L1 缓冲
      </v-tab>
      <v-tab value="l2">
        <v-icon icon="mdi-database-search" class="mr-1" />
        L2 记忆
      </v-tab>
      <v-tab value="l3">
        <v-icon icon="mdi-graph" class="mr-1" />
        L3 图谱
      </v-tab>
    </v-tabs>

    <v-window v-model="activeTab" class="mt-4">
      <!-- L1 缓冲 -->
      <v-window-item value="l1">
        <v-card color="surface" variant="flat">
          <v-card-title class="d-flex align-center">
            <span>L1 消息缓冲</span>
            <v-spacer />
            <v-btn
              icon="mdi-refresh"
              variant="text"
              size="small"
              :loading="memoryStore.l1Loading"
              @click="loadL1Messages"
            />
          </v-card-title>
          <v-card-text>
            <v-progress-linear
              v-if="memoryStore.l1Loading"
              indeterminate
              color="primary"
            />

            <v-list v-else-if="memoryStore.l1Messages.length > 0" lines="three">
              <v-list-item
                v-for="(msg, index) in memoryStore.l1Messages"
                :key="index"
                :class="getRoleClass(msg.role)"
              >
                <template #prepend>
                  <v-avatar :color="getRoleColor(msg.role)" variant="tonal">
                    <v-icon :icon="getRoleIcon(msg.role)" size="small" />
                  </v-avatar>
                </template>

                <v-list-item-title class="font-weight-medium">
                  {{ msg.role === 'user' ? '用户' : msg.role === 'assistant' ? '助手' : '系统' }}
                </v-list-item-title>

                <v-list-item-subtitle class="text-wrap mt-1">
                  {{ msg.content }}
                </v-list-item-subtitle>

                <template #append>
                  <span class="text-caption text-medium-emphasis">
                    {{ formatTime(msg.timestamp) }}
                  </span>
                </template>
              </v-list-item>
            </v-list>

            <div v-else class="text-center text-medium-emphasis py-8">
              <v-icon icon="mdi-inbox-outline" size="64" class="mb-2" />
              <div>暂无缓冲消息</div>
            </div>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- L2 记忆 -->
      <v-window-item value="l2">
        <v-card color="surface" variant="flat">
          <v-card-title>L2 记忆搜索</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="8">
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
              <v-col cols="12" md="4">
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

          <v-divider />

          <v-card-text>
            <v-progress-linear
              v-if="memoryStore.l2Loading"
              indeterminate
              color="primary"
            />

            <div v-else-if="memoryStore.l2Results.length > 0">
              <div class="text-caption text-medium-emphasis mb-2">
                找到 {{ memoryStore.l2Results.length }} 条相关记忆
              </div>

              <v-card
                v-for="(result, index) in memoryStore.l2Results"
                :key="index"
                variant="outlined"
                class="mb-2"
              >
                <v-card-text>
                  <div class="d-flex align-start">
                    <v-chip
                      :color="getScoreColor(result.score)"
                      size="small"
                      class="mr-2"
                    >
                      {{ (result.score * 100).toFixed(0) }}%
                    </v-chip>
                    <div class="flex-grow-1">
                      <div class="text-body-1">{{ result.content }}</div>
                      <div class="text-caption text-medium-emphasis mt-1">
                        {{ formatTime(result.timestamp) }}
                      </div>
                    </div>
                  </div>
                </v-card-text>
              </v-card>
            </div>

            <div v-else class="text-center text-medium-emphasis py-8">
              <v-icon icon="mdi-database-search-outline" size="64" class="mb-2" />
              <div>{{ memoryStore.l2Query ? '未找到相关记忆' : '输入关键词搜索记忆' }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- L3 图谱 -->
      <v-window-item value="l3">
        <v-card color="surface" variant="flat">
          <v-card-title class="d-flex align-center">
            <span>知识图谱</span>
            <v-spacer />
            <v-btn
              icon="mdi-refresh"
              variant="text"
              size="small"
              :loading="memoryStore.l3Loading"
              @click="loadL3Graph"
            />
          </v-card-title>
          <v-card-text>
            <v-progress-linear
              v-if="memoryStore.l3Loading"
              indeterminate
              color="primary"
            />

            <div v-else-if="memoryStore.l3Graph.nodes.length > 0">
              <v-row>
                <v-col cols="12" sm="6">
                  <div class="text-subtitle-2 mb-2">节点 ({{ memoryStore.l3Graph.nodes.length }})</div>
                  <v-chip-group>
                    <v-chip
                      v-for="node in memoryStore.l3Graph.nodes"
                      :key="node.id"
                      color="primary"
                      variant="outlined"
                      size="small"
                    >
                      {{ node.name || node.label }}
                    </v-chip>
                  </v-chip-group>
                </v-col>
                <v-col cols="12" sm="6">
                  <div class="text-subtitle-2 mb-2">关系 ({{ memoryStore.l3Graph.edges.length }})</div>
                  <v-list density="compact" class="bg-transparent">
                    <v-list-item
                      v-for="(edge, index) in memoryStore.l3Graph.edges"
                      :key="index"
                      class="px-0"
                    >
                      <template #prepend>
                        <v-icon icon="mdi-arrow-right" size="small" />
                      </template>
                      <v-list-item-title class="text-body-2">
                        {{ edge.source }} → {{ edge.target }}
                      </v-list-item-title>
                      <v-list-item-subtitle>
                        {{ edge.relation }}
                      </v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-col>
              </v-row>
            </div>

            <div v-else class="text-center text-medium-emphasis py-8">
              <v-icon icon="mdi-graph-outline" size="64" class="mb-2" />
              <div>暂无图谱数据</div>
            </div>
          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useMemoryStore } from '@/stores'
import type { L1Message } from '@/types'

const memoryStore = useMemoryStore()

const activeTab = ref('l1')
const searchQuery = ref('')

const loadL1Messages = () => {
  memoryStore.fetchL1Messages()
}

const loadL3Graph = () => {
  memoryStore.fetchL3Graph()
}

const handleSearch = () => {
  if (searchQuery.value.trim()) {
    memoryStore.searchL2Memory(searchQuery.value.trim())
  }
}

// 角色样式
const getRoleClass = (role: string): string => {
  return role === 'user' ? 'border-l-primary' : role === 'assistant' ? 'border-l-secondary' : 'border-l-accent'
}

const getRoleColor = (role: string): string => {
  return role === 'user' ? 'primary' : role === 'assistant' ? 'secondary' : 'accent'
}

const getRoleIcon = (role: string): string => {
  return role === 'user' ? 'mdi-account' : role === 'assistant' ? 'mdi-robot' : 'mdi-cog'
}

// 分数颜色
const getScoreColor = (score: number): string => {
  if (score >= 0.9) return 'success'
  if (score >= 0.7) return 'info'
  if (score >= 0.5) return 'warning'
  return 'error'
}

// 格式化时间
const formatTime = (timestamp?: string): string => {
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return timestamp
  }
}

// 刷新处理
const handleRefresh = () => {
  if (activeTab.value === 'l1') loadL1Messages()
  else if (activeTab.value === 'l3') loadL3Graph()
}

onMounted(() => {
  loadL1Messages()
  window.addEventListener('iris:refresh', handleRefresh)
})

onUnmounted(() => {
  window.removeEventListener('iris:refresh', handleRefresh)
})
</script>

<style scoped>
.border-l-primary {
  border-left: 3px solid rgb(var(--v-theme-primary));
}
.border-l-secondary {
  border-left: 3px solid rgb(var(--v-theme-secondary));
}
.border-l-accent {
  border-left: 3px solid rgb(var(--v-theme-accent));
}
</style>
