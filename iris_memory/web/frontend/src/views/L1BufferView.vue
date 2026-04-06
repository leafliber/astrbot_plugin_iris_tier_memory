<template>
  <div class="l1-buffer-view">
    <ComponentDisabled
      :status="status"
      :error="error"
      :error-type="errorType"
      component-name="L1 缓冲"
      @retry="refreshState"
    >
      <v-row>
        <v-col cols="12" md="4">
          <v-card color="surface" variant="flat">
            <v-card-title class="d-flex align-center">
              <span>群聊列表</span>
              <v-spacer />
              <v-btn
                icon="mdi-refresh"
                variant="text"
                size="small"
                :loading="memoryStore.l1QueuesLoading"
                @click="loadL1Queues"
              />
            </v-card-title>
            <v-card-text class="pa-0">
              <v-progress-linear
                v-if="memoryStore.l1QueuesLoading"
                indeterminate
                color="primary"
              />

              <v-list v-else-if="memoryStore.l1Queues.length > 0" lines="two">
                <v-list-item
                  v-for="queue in memoryStore.l1Queues"
                  :key="queue.group_id"
                  :active="selectedGroupId === queue.group_id"
                  @click="selectGroup(queue.group_id)"
                >
                  <template #prepend>
                    <v-avatar color="primary" variant="tonal">
                      <v-icon icon="mdi-account-group" />
                    </v-avatar>
                  </template>

                  <v-list-item-title>{{ queue.group_id }}</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ queue.message_count }} 条消息 · {{ queue.total_tokens }} tokens
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>

              <div v-else class="text-center text-medium-emphasis py-8">
                <v-icon icon="mdi-inbox-outline" size="48" />
                <div class="mt-2">暂无群聊数据</div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="8">
          <v-card color="surface" variant="flat">
            <v-card-title class="d-flex align-center">
              <span>消息缓冲</span>
              <v-chip v-if="selectedGroupId" size="small" color="primary" variant="tonal" class="ml-2">
                {{ selectedGroupId }}
              </v-chip>
              <v-spacer />
              <v-btn
                v-if="selectedGroupId"
                icon="mdi-refresh"
                variant="text"
                size="small"
                :loading="memoryStore.l1Loading"
                @click="loadL1Messages"
              />
            </v-card-title>
            <v-card-text>
              <template v-if="selectedGroupId">
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
                  <v-icon icon="mdi-message-outline" size="64" class="mb-2" />
                  <div>暂无缓冲消息</div>
                </div>
              </template>

              <div v-else class="text-center text-medium-emphasis py-8">
                <v-icon icon="mdi-hand-pointing-up" size="64" class="mb-2" />
                <div>请从左侧选择一个群聊</div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-row class="mt-4">
        <v-col cols="12">
          <v-card color="surface" variant="flat">
            <v-card-title>
              <v-icon icon="mdi-information" class="mr-2" />
              L1 缓冲说明
            </v-card-title>
            <v-card-text>
              <v-alert type="info" variant="tonal" density="compact">
                <div class="text-body-2">
                  <strong>L1 缓冲（Working Memory）</strong> 是会话内的临时存储，采用 LRU 缓存策略。
                  这里显示的是当前会话中的消息列表，消息会在会话结束后被清理或转移到 L2 长期记忆。
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
import { ref, onMounted, onUnmounted } from 'vue'
import { useMemoryStore } from '@/stores'
import { useComponentState } from '@/composables/useComponentState'
import ComponentDisabled from '@/components/ComponentDisabled.vue'

const memoryStore = useMemoryStore()
const { status, error, errorType, refreshState } = useComponentState('l1_buffer')

const selectedGroupId = ref<string | null>(null)

const loadL1Queues = () => {
  memoryStore.fetchL1Queues()
}

const selectGroup = (groupId: string) => {
  selectedGroupId.value = groupId
  memoryStore.fetchL1Messages(groupId)
}

const loadL1Messages = () => {
  if (selectedGroupId.value) {
    memoryStore.fetchL1Messages(selectedGroupId.value)
  }
}

const getRoleClass = (role: string): string => {
  return role === 'user' ? 'border-l-primary' : role === 'assistant' ? 'border-l-secondary' : 'border-l-accent'
}

const getRoleColor = (role: string): string => {
  return role === 'user' ? 'primary' : role === 'assistant' ? 'secondary' : 'accent'
}

const getRoleIcon = (role: string): string => {
  return role === 'user' ? 'mdi-account' : role === 'assistant' ? 'mdi-robot' : 'mdi-cog'
}

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

const handleRefresh = () => {
  loadL1Queues()
}

onMounted(() => {
  loadL1Queues()
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
