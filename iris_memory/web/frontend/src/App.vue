<template>
  <v-app>
    <!-- 未登录提示 -->
    <v-overlay
      :model-value="!isAuthenticated"
      class="align-center justify-center"
      persistent
    >
      <v-card
        max-width="400"
        class="text-center pa-6"
      >
        <v-icon
          icon="mdi-lock-outline"
          size="64"
          color="warning"
          class="mb-4"
        />
        <v-card-title class="text-h5 mb-2">需要登录</v-card-title>
        <v-card-text class="text-body-1 mb-4">
          请先登录 AstrBot Dashboard 后再访问此页面
        </v-card-text>
        <v-btn
          color="primary"
          size="large"
          href="/"
          prepend-icon="mdi-login"
        >
          前往登录
        </v-btn>
      </v-card>
    </v-overlay>

    <!-- 主界面 -->
    <template v-if="isAuthenticated">
      <!-- 导航抽屉 -->
      <v-navigation-drawer v-model="drawer" :rail="rail" permanent>
        <v-list-item
          prepend-icon="mdi-brain"
          title="Iris Memory"
          nav
          @click="rail = !rail"
        >
          <template #append>
            <v-btn
              :icon="rail ? 'mdi-chevron-right' : 'mdi-chevron-left'"
              variant="text"
              size="small"
            />
          </template>
        </v-list-item>

        <v-divider />

        <v-list density="compact" nav>
          <v-list-item
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            :prepend-icon="item.icon"
            :title="item.title"
            :value="item.to"
            color="primary"
          />
        </v-list>
      </v-navigation-drawer>

      <!-- 顶部应用栏 -->
      <v-app-bar color="surface" elevation="0" border="b">
        <v-app-bar-title class="text-h6">
          {{ currentTitle }}
        </v-app-bar-title>

        <template #append>
          <!-- 刷新按钮 -->
          <v-btn
            icon="mdi-refresh"
            variant="text"
            :loading="loading"
            @click="handleRefresh"
          />

          <!-- 主题切换 -->
          <v-btn
            :icon="darkMode ? 'mdi-weather-sunny' : 'mdi-weather-night'"
            variant="text"
            @click="toggleTheme"
          />
        </template>
      </v-app-bar>

      <!-- 主内容 -->
      <v-main>
        <v-container fluid class="pa-4">
          <router-view v-slot="{ Component }">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </v-container>
      </v-main>

      <!-- 错误提示 -->
      <v-snackbar
        v-model="showError"
        color="error"
        :timeout="3000"
        location="top"
      >
        {{ error }}
      </v-snackbar>
    </template>
  </v-app>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAppStore } from '@/stores'
import apiClient from '@/api/request'

const route = useRoute()
const appStore = useAppStore()

const { loading, error, darkMode } = storeToRefs(appStore)

const drawer = ref(true)
const rail = ref(false)
const showError = ref(false)
const isAuthenticated = ref(true)

const navItems = [
  { to: '/dashboard', title: '仪表盘', icon: 'mdi-view-dashboard' },
  { to: '/memory', title: '记忆管理', icon: 'mdi-brain' },
  { to: '/profile', title: '画像管理', icon: 'mdi-account-group' },
  { to: '/stats', title: '数据统计', icon: 'mdi-chart-bar' }
]

const currentTitle = computed(() => {
  const item = navItems.find(i => i.to === route.path)
  return item?.title || 'Iris Memory'
})

const checkAuth = async () => {
  try {
    await apiClient.get('/stats/system')
    isAuthenticated.value = true
  } catch (e: unknown) {
    const err = e as Error
    if (err.message.includes('未登录') || err.message.includes('登录')) {
      isAuthenticated.value = false
    }
  }
}

const handleRefresh = () => {
  window.dispatchEvent(new CustomEvent('iris:refresh'))
}

const toggleTheme = () => {
  appStore.toggleTheme()
}

watch(error, (val) => {
  showError.value = !!val
})

onMounted(() => {
  checkAuth()
})
</script>
