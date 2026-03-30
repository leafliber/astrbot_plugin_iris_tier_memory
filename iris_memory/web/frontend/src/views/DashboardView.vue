<template>
  <div class="dashboard">
    <!-- 组件状态卡片 -->
    <v-row>
      <v-col cols="12" sm="6" md="4" lg="2" v-for="(status, key) in componentStatus" :key="key">
        <v-card
          :color="status ? 'surface' : 'error'"
          variant="outlined"
          class="h-100"
        >
          <v-card-text class="text-center">
            <v-icon
              :icon="status ? 'mdi-check-circle' : 'mdi-alert-circle'"
              :color="status ? 'success' : 'error'"
              size="32"
            />
            <div class="text-body-2 mt-2">{{ componentNames[key] }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ status ? '运行中' : '不可用' }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 记忆层级概览 -->
    <v-row class="mt-4">
      <v-col cols="12" md="4">
        <v-card color="surface" variant="flat">
          <v-card-item>
            <template #prepend>
              <v-avatar color="primary" variant="tonal">
                <v-icon icon="mdi-lightning-bolt" />
              </v-avatar>
            </template>
            <v-card-title>L1 缓冲</v-card-title>
            <v-card-subtitle>短期记忆 · 消息缓冲</v-card-subtitle>
          </v-card-item>
          <v-card-text>
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
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card color="surface" variant="flat">
          <v-card-item>
            <template #prepend>
              <v-avatar color="secondary" variant="tonal">
                <v-icon icon="mdi-database" />
              </v-avatar>
            </template>
            <v-card-title>L2 记忆</v-card-title>
            <v-card-subtitle>长期记忆 · 向量检索</v-card-subtitle>
          </v-card-item>
          <v-card-text>
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
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card color="surface" variant="flat">
          <v-card-item>
            <template #prepend>
              <v-avatar color="accent" variant="tonal">
                <v-icon icon="mdi-graph" />
              </v-avatar>
            </template>
            <v-card-title>L3 知识图谱</v-card-title>
            <v-card-subtitle>结构化知识 · 关系网络</v-card-subtitle>
          </v-card-item>
          <v-card-text>
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
        </v-card>
      </v-col>
    </v-row>

    <!-- Token 使用统计 -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card color="surface" variant="flat">
          <v-card-item>
            <template #prepend>
              <v-icon icon="mdi-twitter" color="info" />
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

    <!-- 运行时间 -->
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

const statsStore = useStatsStore()

const refreshInterval = ref<number | null>(null)

// 组件状态
const componentStatus = computed(() => {
  return statsStore.systemStats?.components || {}
})

const componentNames: Record<string, string> = {
  l1_buffer: 'L1 缓冲',
  l2_memory: 'L2 记忆',
  l3_kg: 'L3 图谱',
  profile: '画像',
  llm_manager: 'LLM 管理'
}

// L1 统计
const l1QueueLength = computed(() => statsStore.memoryStats?.l1?.queue_length ?? 0)
const l1MaxCapacity = computed(() => statsStore.memoryStats?.l1?.max_capacity)
const l1UsagePercent = computed(() => {
  if (!l1MaxCapacity.value) return 0
  return (l1QueueLength.value / l1MaxCapacity.value) * 100
})

// L2 统计
const l2TotalCount = computed(() => statsStore.memoryStats?.l2?.total_count ?? 0)
const l2GroupCount = computed(() => statsStore.memoryStats?.l2?.group_count ?? 0)

// L3 统计
const kgNodeCount = computed(() => statsStore.kgStats?.node_count ?? 0)
const kgEdgeCount = computed(() => statsStore.kgStats?.edge_count ?? 0)

// Token 统计
const globalInputTokens = computed(() => statsStore.tokenStats?.global?.total_input_tokens ?? 0)
const globalOutputTokens = computed(() => statsStore.tokenStats?.global?.total_output_tokens ?? 0)
const globalCalls = computed(() => statsStore.tokenStats?.global?.total_calls ?? 0)

// 运行时间
const uptime = computed(() => {
  const seconds = statsStore.systemStats?.uptime ?? 0
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${hours} 小时 ${minutes} 分钟`
})

// 格式化数字
const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

// 加载数据
const loadData = async () => {
  await Promise.all([
    statsStore.fetchMemoryStats(),
    statsStore.fetchTokenStats(),
    statsStore.fetchKGStats(),
    statsStore.fetchSystemStats()
  ])
}

// 刷新处理
const handleRefresh = () => {
  loadData()
}

onMounted(() => {
  loadData()
  // 每30秒自动刷新
  refreshInterval.value = window.setInterval(loadData, 30000)
  // 监听刷新事件
  window.addEventListener('iris:refresh', handleRefresh)
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
  window.removeEventListener('iris:refresh', handleRefresh)
})
</script>
