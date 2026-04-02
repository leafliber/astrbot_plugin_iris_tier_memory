<template>
  <v-app>
    <!-- 未登录提示 -->
    <v-overlay
      :model-value="!isAuthenticated"
      class="align-center justify-center"
      persistent
    >
      <v-card
        max-width="550"
        class="text-center pa-6"
      >
        <v-icon
          icon="mdi-lock-outline"
          size="64"
          color="warning"
          class="mb-4"
        />
        <v-card-title class="text-h5 mb-2">需要登录</v-card-title>
        <v-card-text class="text-body-1">
          <v-alert
            type="info"
            variant="tonal"
            class="text-left mb-4"
          >
            <p class="text-subtitle-2 font-weight-bold mb-2">认证流程说明</p>
            <ol class="text-caption pl-4">
              <li>先登录 AstrBot Dashboard（端口 {{ astrbotPort }}）</li>
              <li>在 Dashboard 页面使用书签跳转到 Iris</li>
              <li>自动完成认证</li>
            </ol>
          </v-alert>
          
          <!-- 书签方式 -->
          <div class="mb-4">
            <p class="text-subtitle-1 font-weight-medium mb-2">方式一：浏览器书签（推荐）</p>
            <p class="text-caption text-medium-emphasis mb-3">
              将下方按钮拖拽到浏览器书签栏，在 AstrBot Dashboard 页面点击即可自动跳转认证
            </p>
            <v-btn
              color="primary"
              size="large"
              variant="outlined"
              block
              :href="bookmarkletCode"
              @click.prevent="showBookmarkHint"
            >
              <v-icon start icon="mdi-bookmark-plus" />
              📌 跳转到 Iris Memory
            </v-btn>
            <p class="text-caption text-medium-emphasis mt-2">
              💡 提示：拖拽此按钮到书签栏，然后在 AstrBot Dashboard 页面使用
            </p>
          </div>
          
          <v-divider class="my-4">
            <span class="text-caption text-medium-emphasis px-2">或者</span>
          </v-divider>
          
          <!-- 手动输入 -->
          <div class="mb-4">
            <p class="text-subtitle-1 font-weight-medium mb-2">方式二：手动输入 Token</p>
            <p class="text-caption text-medium-emphasis mb-3">
              从 AstrBot Dashboard 的浏览器开发者工具中复制 Cookie
            </p>
            <v-text-field
              v-model="manualToken"
              label="JWT Token"
              variant="outlined"
              density="comfortable"
              :type="showToken ? 'text' : 'password'"
              :append-inner-icon="showToken ? 'mdi-eye-off' : 'mdi-eye'"
              @click:append-inner="showToken = !showToken"
              hint="Cookie 中的 jwt_token 值"
              persistent-hint
            />
            <v-btn
              color="secondary"
              class="mt-4"
              :disabled="!manualToken"
              @click="handleManualLogin"
            >
              验证 Token
            </v-btn>
          </div>
          
          <v-divider class="my-4" />
          
          <!-- 直接跳转 -->
          <div>
            <p class="text-subtitle-1 font-weight-medium mb-2">方式三：直接访问</p>
            <p class="text-caption text-medium-emphasis mb-3">
              如果你已经在 AstrBot Dashboard 登录，可以直接访问带 Token 的链接
            </p>
            <v-btn
              color="info"
              variant="text"
              :href="`http://${astrbotHost}/`"
              target="_blank"
              prepend-icon="mdi-open-in-new"
            >
              打开 AstrBot Dashboard
            </v-btn>
          </div>
        </v-card-text>
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
import apiClient, { setStoredToken, clearStoredToken } from '@/api/request'

const route = useRoute()
const appStore = useAppStore()

const { loading, error, darkMode } = storeToRefs(appStore)

const drawer = ref(true)
const rail = ref(false)
const showError = ref(false)
const isAuthenticated = ref(true)
const manualToken = ref('')
const showToken = ref(false)

const astrbotPort = 6185
const irisHost = window.location.host
const astrbotHost = window.location.hostname + ':' + astrbotPort

const bookmarkletCode = computed(() => {
  const code = `javascript:(function(){var t=document.cookie.split('; ').find(r=>r.startsWith('jwt_token='));if(t){var e=t.split('=')[1];window.location.href='http://${irisHost}/iris/auth/login?token='+e;}else{alert('请先登录 AstrBot Dashboard');}})();`
  return code
})

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

const handleManualLogin = async () => {
  if (!manualToken.value.trim()) return
  
  setStoredToken(manualToken.value.trim())
  
  try {
    await apiClient.get('/stats/system')
    isAuthenticated.value = true
  } catch (e: unknown) {
    clearStoredToken()
    const err = e as Error
    alert('Token 验证失败: ' + err.message)
  }
}

const showBookmarkHint = () => {
  alert('请将此按钮拖拽到浏览器书签栏，然后在 AstrBot Dashboard 页面点击使用。\n\n使用步骤：\n1. 拖拽此按钮到书签栏\n2. 登录 AstrBot Dashboard\n3. 在 Dashboard 页面点击书签\n4. 自动跳转到 Iris 并完成认证')
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
  const urlToken = route.query.token as string
  if (urlToken) {
    setStoredToken(urlToken)
    window.history.replaceState({}, '', route.path)
  }
  
  checkAuth()
})
</script>
