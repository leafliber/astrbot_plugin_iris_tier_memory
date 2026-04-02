<template>
  <div class="stats-view">
    <v-row>
      <!-- 记忆统计 -->
      <v-col cols="12" md="6">
        <v-card color="surface" variant="flat">
          <v-card-title class="d-flex align-center">
            <v-icon icon="mdi-brain" color="primary" class="mr-2" />
            记忆统计
          </v-card-title>
          <v-card-text>
            <v-list density="compact" class="bg-transparent">
              <!-- L1 -->
              <v-list-item>
                <template #prepend>
                  <v-icon icon="mdi-lightning-bolt" color="primary" />
                </template>
                <v-list-item-title>L1 缓冲</v-list-item-title>
                <template #append>
                  <v-chip size="small" variant="tonal" color="primary">
                    {{ memoryStats?.l1?.queue_length ?? 0 }} / {{ memoryStats?.l1?.max_capacity ?? '∞' }}
                  </v-chip>
                </template>
              </v-list-item>

              <!-- L2 -->
              <v-list-item>
                <template #prepend>
                  <v-icon icon="mdi-database" color="secondary" />
                </template>
                <v-list-item-title>L2 记忆库</v-list-item-title>
                <template #append>
                  <v-chip size="small" variant="tonal" color="secondary">
                    {{ memoryStats?.l2?.total_count ?? 0 }} 条
                  </v-chip>
                </template>
              </v-list-item>

              <v-list-item>
                <template #prepend>
                  <span class="ml-7 text-caption">涉及群聊</span>
                </template>
                <template #append>
                  <v-chip size="small" variant="tonal" color="secondary">
                    {{ memoryStats?.l2?.group_count ?? 0 }} 个
                  </v-chip>
                </template>
              </v-list-item>

              <!-- L3 -->
              <v-list-item>
                <template #prepend>
                  <v-icon icon="mdi-graph" color="accent" />
                </template>
                <v-list-item-title>L3 知识图谱</v-list-item-title>
                <template #append>
                  <v-chip size="small" variant="tonal" color="accent">
                    {{ kgStats?.node_count ?? 0 }} 节点
                  </v-chip>
                </template>
              </v-list-item>

              <v-list-item>
                <template #prepend>
                  <span class="ml-7 text-caption">关系边</span>
                </template>
                <template #append>
                  <v-chip size="small" variant="tonal" color="accent">
                    {{ kgStats?.edge_count ?? 0 }} 条
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Token 统计 -->
      <v-col cols="12" md="6">
        <v-card color="surface" variant="flat">
          <v-card-title class="d-flex align-center">
            <v-icon icon="mdi-counter" color="info" class="mr-2" />
            Token 消耗
          </v-card-title>
          <v-card-text>
            <v-table density="compact" class="bg-transparent">
              <thead>
                <tr>
                  <th>模块</th>
                  <th class="text-right">输入 Token</th>
                  <th class="text-right">输出 Token</th>
                  <th class="text-right">调用次数</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(stat, module) in tokenStats" :key="module">
                  <td class="font-weight-medium">{{ getModuleName(module) }}</td>
                  <td class="text-right text-primary">{{ formatNumber(stat.total_input_tokens) }}</td>
                  <td class="text-right text-secondary">{{ formatNumber(stat.total_output_tokens) }}</td>
                  <td class="text-right">{{ stat.total_calls }}</td>
                </tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 图谱类型分布 -->
    <v-row class="mt-4">
      <!-- 节点类型 -->
      <v-col cols="12" sm="6">
        <v-card color="surface" variant="flat">
          <v-card-title class="text-subtitle-1">
            <v-icon icon="mdi-circle-multiple" class="mr-1" />
            节点类型分布
          </v-card-title>
          <v-card-text>
            <div v-if="kgStats?.node_types && Object.keys(kgStats.node_types).length > 0">
              <div
                v-for="(count, type) in kgStats.node_types"
                :key="type"
                class="d-flex align-center mb-2"
              >
                <span class="text-body-2 w-25">{{ type }}</span>
                <v-progress-linear
                  :model-value="(count / kgStats.node_count) * 100"
                  color="primary"
                  height="20"
                  rounded
                />
                <span class="ml-2 text-caption">{{ count }}</span>
              </div>
            </div>
            <div v-else class="text-center text-medium-emphasis py-4">
              暂无数据
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 关系类型 -->
      <v-col cols="12" sm="6">
        <v-card color="surface" variant="flat">
          <v-card-title class="text-subtitle-1">
            <v-icon icon="mdi-arrow-decision" class="mr-1" />
            关系类型分布
          </v-card-title>
          <v-card-text>
            <div v-if="kgStats?.relation_types && Object.keys(kgStats.relation_types).length > 0">
              <div
                v-for="(count, type) in kgStats.relation_types"
                :key="type"
                class="d-flex align-center mb-2"
              >
                <span class="text-body-2 w-25">{{ type }}</span>
                <v-progress-linear
                  :model-value="(count / kgStats.edge_count) * 100"
                  color="secondary"
                  height="20"
                  rounded
                />
                <span class="ml-2 text-caption">{{ count }}</span>
              </div>
            </div>
            <div v-else class="text-center text-medium-emphasis py-4">
              暂无数据
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 系统信息 -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card color="surface" variant="flat">
          <v-card-title class="text-subtitle-1">
            <v-icon icon="mdi-information" class="mr-1" />
            系统信息
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" sm="4">
                <div class="text-caption text-medium-emphasis">版本</div>
                <div class="text-body-1">{{ systemStats?.version || '1.0.0' }}</div>
              </v-col>
              <v-col cols="12" sm="4">
                <div class="text-caption text-medium-emphasis">运行时间</div>
                <div class="text-body-1">{{ uptime }}</div>
              </v-col>
              <v-col cols="12" sm="4">
                <div class="text-caption text-medium-emphasis">组件状态</div>
                <div class="d-flex flex-wrap ga-1 mt-1">
                  <v-chip
                    v-for="(status, name) in systemStats?.components"
                    :key="name"
                    size="x-small"
                    :color="status ? 'success' : 'error'"
                  >
                    {{ getComponentName(name) }}: {{ status ? '✓' : '✗' }}
                  </v-chip>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useStatsStore } from '@/stores'
import type { TokenStats } from '@/types'

const statsStore = useStatsStore()

const refreshInterval = ref<number | null>(null)

const memoryStats = computed(() => statsStore.memoryStats)
const tokenStats = computed((): Record<string, TokenStats> => statsStore.tokenStats || {})
const kgStats = computed(() => statsStore.kgStats)
const systemStats = computed(() => statsStore.systemStats)

const uptime = computed(() => {
  const seconds = systemStats.value?.uptime ?? 0
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days} 天 ${hours} 小时`
  if (hours > 0) return `${hours} 小时 ${minutes} 分钟`
  return `${minutes} 分钟`
})

const getModuleName = (module: string): string => {
  const names: Record<string, string> = {
    global: '全局',
    l1_summarizer: 'L1 摘要器',
    llm_manager: 'LLM 管理器'
  }
  return names[module] || module
}

const getComponentName = (name: string): string => {
  const names: Record<string, string> = {
    l1_buffer: 'L1',
    l2_memory: 'L2',
    l3_kg: 'L3',
    profile: '画像',
    llm_manager: 'LLM'
  }
  return names[name] || name
}

const formatNumber = (num: number): string => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

const loadData = () => {
  statsStore.fetchAllStats()
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
