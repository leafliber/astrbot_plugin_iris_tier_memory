<template>
  <div class="dashboard">
    <v-row>
      <v-col cols="12" sm="6" md="4" lg="2" v-for="(state, key) in componentStates" :key="key">
        <v-card
          :color="getCardColor(state.status)"
          variant="outlined"
          class="h-100 component-card"
          :class="{ 'component-loading': isLoading(state.status) }"
        >
          <v-card-text class="text-center">
            <v-icon
              :icon="getStatusIcon(state.status)"
              :color="getStatusColor(state.status)"
              size="32"
              :class="{ 'animate-spin': state.status === 'initializing' }"
            />
            <div class="text-body-2 mt-2">{{ getComponentName(key) }}</div>
            <div class="text-caption" :class="getStatusTextClass(state.status)">
              {{ getStatusText(state.status) }}
            </div>
            <v-tooltip v-if="state.error" activator="parent" location="bottom">
              <div class="text-caption">
                <div class="font-weight-bold mb-1">{{ getErrorTypeName(state.error_type) }}</div>
                <div>{{ state.error }}</div>
              </div>
            </v-tooltip>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12" md="4">
        <v-card 
          color="surface" 
          variant="flat"
          :class="{ 'component-disabled': !isL1Available }"
        >
          <v-card-item>
            <template #prepend>
              <v-avatar color="primary" variant="tonal">
                <v-icon icon="mdi-lightning-bolt" />
              </v-avatar>
            </template>
            <v-card-title>L1 缓冲</v-card-title>
            <v-card-subtitle>短期记忆 · 消息缓冲</v-card-subtitle>
          </v-card-item>
          <v-card-text v-if="isL1Available">
            <div class="d-flex justify-space-between align-center">
              <span class="text-h4 font-weight-bold">{{ l1QueueLength }}</span>
              <span class="text-caption">/ {{ l1MaxCapacity || '∞' }}</span>
            </div>
            <v-progress-linear
              :model-value="l1UsagePercent"
              color="primary"
              height="8"
              rounded
              class="mt-2"
            />
            <div class="text-caption text-medium-emphasis mt-1">
              队列长度
            </div>
          </v-card-text>
          <v-card-text v-else class="text-center py-4">
            <v-icon icon="mdi-block-helper" color="error" size="large" />
            <div class="text-caption text-medium-emphasis mt-2">
              {{ getComponentDisabledReason('l1_buffer') }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card 
          color="surface" 
          variant="flat"
          :class="{ 'component-disabled': !isL2Available }"
        >
          <v-card-item>
            <template #prepend>
              <v-avatar color="secondary" variant="tonal">
                <v-icon icon="mdi-database" />
              </v-avatar>
            </template>
            <v-card-title>L2 记忆</v-card-title>
            <v-card-subtitle>长期记忆 · 向量检索</v-card-subtitle>
          </v-card-item>
          <v-card-text v-if="isL2Available">
            <div class="d-flex justify-space-between align-center">
              <span class="text-h4 font-weight-bold">{{ l2TotalCount }}</span>
              <span class="text-caption">条记忆</span>
            </div>
            <div class="d-flex justify-space-between mt-2">
              <div>
                <span class="text-h6">{{ l2GroupCount }}</span>
                <span class="text-caption text-medium-emphasis ml-1">群聊</span>
              </div>
            </div>
          </v-card-text>
          <v-card-text v-else class="text-center py-4">
            <v-icon icon="mdi-block-helper" color="error" size="large" />
            <div class="text-caption text-medium-emphasis mt-2">
              {{ getComponentDisabledReason('l2_memory') }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card 
          color="surface" 
          variant="flat"
          :class="{ 'component-disabled': !isL3Available }"
        >
          <v-card-item>
            <template #prepend>
              <v-avatar color="accent" variant="tonal">
                <v-icon icon="mdi-graph" />
              </v-avatar>
            </template>
            <v-card-title>L3 知识图谱</v-card-title>
            <v-card-subtitle>结构化知识 · 关系网络</v-card-subtitle>
          </v-card-item>
          <v-card-text v-if="isL3Available">
            <div class="d-flex justify-space-between">
              <div class="text-center">
                <span class="text-h4 font-weight-bold">{{ kgNodeCount }}</span>
                <div class="text-caption">节点</div>
              </div>
              <div class="text-center">
                <span class="text-h4 font-weight-bold">{{ kgEdgeCount }}</span>
                <div class="text-caption">边</div>
              </div>
            </div>
          </v-card-text>
          <v-card-text v-else class="text-center py-4">
            <v-icon icon="mdi-block-helper" color="error" size="large" />
            <div class="text-caption text-medium-emphasis mt-2">
              {{ getComponentDisabledReason('l3_kg') }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12">
        <v-card color="surface" variant="flat">
          <v-card-item>
            <template #prepend>
              <v-icon icon="mdi-counter" color="info" />
            </template>
            <v-card-title>Token 使用统计</v-card-title>
            <v-card-subtitle>全局 Token 消耗</v-card-subtitle>
          </v-card-item>
          <v-card-text>
            <v-row>
              <v-col cols="12" sm="4">
                <div class="text-center">
                  <span class="text-h5 font-weight-bold text-primary">
                    {{ formatNumber(globalInputTokens) }}
                  </span>
                  <div class="text-caption">输入 Token</div>
                </div>
              </v-col>
              <v-col cols="12" sm="4">
                <div class="text-center">
                  <span class="text-h5 font-weight-bold text-secondary">
                    {{ formatNumber(globalOutputTokens) }}
                  </span>
                  <div class="text-caption">输出 Token</div>
                </div>
              </v-col>
              <v-col cols="12" sm="4">
                <div class="text-center">
                  <span class="text-h5 font-weight-bold text-accent">
                    {{ globalCalls }}
                  </span>
                  <div class="text-caption">调用次数</div>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12">
        <v-card color="surface" variant="flat">
          <v-card-text class="text-center text-medium-emphasis">
            <v-icon icon="mdi-clock-outline" size="small" class="mr-1" />
            运行时间: {{ uptime }}
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useStatsStore } from '@/stores'
import type { ComponentState, ComponentStatus, ErrorType } from '@/types'
import { 
  COMPONENT_DISPLAY_NAMES, 
  ERROR_TYPE_DISPLAY_NAMES, 
  STATUS_DISPLAY_NAMES 
} from '@/types'

const statsStore = useStatsStore()

const refreshInterval = ref<number | null>(null)

const componentStates = computed(() => {
  return statsStore.componentStates
})

const getComponentName = (key: string): string => {
  return COMPONENT_DISPLAY_NAMES[key] || key
}

const isLoading = (status: ComponentStatus): boolean => {
  return status === 'pending' || status === 'initializing'
}

const getCardColor = (status: ComponentStatus): string => {
  switch (status) {
    case 'available':
      return 'surface'
    case 'pending':
    case 'initializing':
      return 'surface'
    case 'unavailable':
      return 'surface'
    default:
      return 'surface'
  }
}

const getStatusIcon = (status: ComponentStatus): string => {
  switch (status) {
    case 'available':
      return 'mdi-check-circle'
    case 'pending':
      return 'mdi-clock-outline'
    case 'initializing':
      return 'mdi-loading'
    case 'unavailable':
      return 'mdi-alert-circle'
    default:
      return 'mdi-help-circle'
  }
}

const getStatusColor = (status: ComponentStatus): string => {
  switch (status) {
    case 'available':
      return 'success'
    case 'pending':
    case 'initializing':
      return 'warning'
    case 'unavailable':
      return 'error'
    default:
      return 'grey'
  }
}

const getStatusText = (status: ComponentStatus): string => {
  return STATUS_DISPLAY_NAMES[status] || status
}

const getStatusTextClass = (status: ComponentStatus): string => {
  switch (status) {
    case 'available':
      return 'text-success'
    case 'pending':
    case 'initializing':
      return 'text-warning'
    case 'unavailable':
      return 'text-error'
    default:
      return 'text-medium-emphasis'
  }
}

const getErrorTypeName = (errorType: ErrorType | null): string => {
  if (!errorType) return ''
  return ERROR_TYPE_DISPLAY_NAMES[errorType] || errorType
}

const isL1Available = computed(() => statsStore.isComponentAvailable('l1_buffer'))
const isL2Available = computed(() => statsStore.isComponentAvailable('l2_memory'))
const isL3Available = computed(() => statsStore.isComponentAvailable('l3_kg'))

const getComponentDisabledReason = (componentName: string): string => {
  const state = statsStore.getComponentState(componentName)
  if (state.status === 'pending' || state.status === 'initializing') {
    return '正在加载...'
  }
  if (state.error_type) {
    return ERROR_TYPE_DISPLAY_NAMES[state.error_type] || '不可用'
  }
  return '不可用'
}

const l1QueueLength = computed(() => statsStore.memoryStats?.l1?.total_messages ?? 0)
const l1MaxCapacity = computed(() => statsStore.memoryStats?.l1?.max_capacity)
const l1UsagePercent = computed(() => {
  if (!l1MaxCapacity.value) return 0
  return (l1QueueLength.value / l1MaxCapacity.value) * 100
})

const l2TotalCount = computed(() => statsStore.memoryStats?.l2?.total_count ?? 0)
const l2GroupCount = computed(() => statsStore.memoryStats?.l2?.group_count ?? 0)

const kgNodeCount = computed(() => statsStore.kgStats?.node_count ?? 0)
const kgEdgeCount = computed(() => statsStore.kgStats?.edge_count ?? 0)

const globalInputTokens = computed(() => statsStore.tokenStats?.global?.total_input_tokens ?? 0)
const globalOutputTokens = computed(() => statsStore.tokenStats?.global?.total_output_tokens ?? 0)
const globalCalls = computed(() => statsStore.tokenStats?.global?.total_calls ?? 0)

const uptime = computed(() => {
  const seconds = statsStore.systemStats?.uptime ?? 0
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${hours} 小时 ${minutes} 分钟`
})

const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

const loadData = async () => {
  await statsStore.fetchAllStats()
}

const handleRefresh = () => {
  loadData()
}

onMounted(() => {
  loadData()
  refreshInterval.value = window.setInterval(loadData, 30000)
  window.addEventListener('iris:refresh', handleRefresh)
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
  window.removeEventListener('iris:refresh', handleRefresh)
})
</script>

<style scoped>
.component-card {
  transition: all 0.3s ease;
}

.component-loading {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.component-disabled {
  opacity: 0.6;
}
</style>
