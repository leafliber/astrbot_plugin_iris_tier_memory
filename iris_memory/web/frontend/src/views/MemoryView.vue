<template>
  <v-container fluid>
    <v-row>
      <!-- 搜索区域 -->
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-brain</v-icon>
            记忆管理
          </v-card-title>
          <v-card-text>
            <v-text-field
              v-model="searchQuery"
              label="搜索记忆"
              prepend-icon="mdi-magnify"
              clearable
              @keyup.enter="handleSearch"
              @click:clear="handleClear"
            />

            <v-btn
              color="primary"
              @click="handleSearch"
              :loading="loading"
              :disabled="!searchQuery"
            >
              <v-icon left>mdi-magnify</v-icon>
              搜索
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 错误提示 -->
      <v-col cols="12" v-if="error">
        <v-alert type="error" dismissible>
          {{ error }}
        </v-alert>
      </v-col>

      <!-- 搜索结果 -->
      <v-col cols="12" v-if="results.length > 0">
        <v-card>
          <v-card-title>
            搜索结果 ({{ results.length }})
          </v-card-title>
          <v-list>
            <v-list-item
              v-for="(item, index) in results"
              :key="index"
              three-line
            >
              <v-list-item-content>
                <v-list-item-title>
                  {{ item.content }}
                </v-list-item-title>
                <v-list-item-subtitle>
                  <v-chip small label class="mr-2">
                    相似度: {{ item.score.toFixed(3) }}
                  </v-chip>
                  <v-chip small label v-if="item.timestamp">
                    {{ formatDate(item.timestamp) }}
                  </v-chip>
                </v-list-item-subtitle>
              </v-list-item-content>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <!-- 空状态 -->
      <v-col cols="12" v-else-if="searchQuery && !loading">
        <v-card>
          <v-card-text class="text-center py-8">
            <v-icon size="64" color="grey">mdi-database-off</v-icon>
            <div class="mt-4 text-h6">暂无搜索结果</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMemoryStore } from '@/stores/memory'
import { storeToRefs } from 'pinia'

const memoryStore = useMemoryStore()
const { searchResults, loading, error } = storeToRefs(memoryStore)

const searchQuery = ref('')

async function handleSearch() {
  if (!searchQuery.value.trim()) return
  await memoryStore.searchMemory(searchQuery.value)
}

function handleClear() {
  memoryStore.clearSearch()
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN')
}
</script>
