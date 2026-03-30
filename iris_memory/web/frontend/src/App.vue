<template>
  <v-app>
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
  </v-app>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAppStore } from '@/stores'

const route = useRoute()
const appStore = useAppStore()

const { loading, error, darkMode } = storeToRefs(appStore)

const drawer = ref(true)
const rail = ref(false)
const showError = ref(false)

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

const handleRefresh = () => {
  // 触发刷新事件
  window.dispatchEvent(new CustomEvent('iris:refresh'))
}

const toggleTheme = () => {
  appStore.toggleTheme()
}

// 监听错误
watch(error, (val) => {
  showError.value = !!val
})
</script>
