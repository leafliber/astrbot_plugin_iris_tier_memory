<template>
  <v-app>
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
        <v-card-title class="text-h5 mb-2">需要访问密钥</v-card-title>
        <v-card-text class="text-body-1">
          <p class="mb-4">请输入访问密钥以访问 Iris Memory</p>
          
          <v-form @submit.prevent="handleLogin">
            <v-text-field
              v-model="accessKey"
              label="访问密钥"
              variant="outlined"
              density="comfortable"
              :type="showKey ? 'text' : 'password'"
              :append-inner-icon="showKey ? 'mdi-eye-off' : 'mdi-eye'"
              @click:append-inner="showKey = !showKey"
              :error-messages="errorMessage"
              :loading="logging"
              autofocus
            />
            <v-btn
              color="primary"
              size="large"
              type="submit"
              block
              class="mt-4"
              :disabled="!accessKey"
              :loading="logging"
            >
              登录
            </v-btn>
          </v-form>
        </v-card-text>
      </v-card>
    </v-overlay>

    <template v-if="isAuthenticated">
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

      <v-app-bar color="surface" elevation="0" border="b">
        <v-app-bar-title class="text-h6">
          {{ currentTitle }}
        </v-app-bar-title>

        <template #append>
          <v-btn
            icon="mdi-refresh"
            variant="text"
            :loading="loading"
            @click="handleRefresh"
          />

          <v-btn
            :icon="darkMode ? 'mdi-weather-sunny' : 'mdi-weather-night'"
            variant="text"
            @click="toggleTheme"
          />
        </template>
      </v-app-bar>

      <v-main>
        <v-container fluid class="pa-4">
          <router-view v-slot="{ Component }">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </v-container>
      </v-main>

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
import axios from 'axios'

const route = useRoute()
const appStore = useAppStore()

const { loading, error, darkMode } = storeToRefs(appStore)

const drawer = ref(true)
const rail = ref(false)
const showError = ref(false)
const isAuthenticated = ref(true)
const accessKey = ref('')
const showKey = ref(false)
const logging = ref(false)
const errorMessage = ref('')

const navItems = [
  { to: '/dashboard', title: '仪表盘', icon: 'mdi-view-dashboard' },
  { to: '/l1-buffer', title: 'L1 缓冲', icon: 'mdi-lightning-bolt' },
  { to: '/l2-memory', title: 'L2 记忆', icon: 'mdi-database-search' },
  { to: '/l3-graph', title: 'L3 图谱', icon: 'mdi-graph' },
  { to: '/profile', title: '画像管理', icon: 'mdi-account-group' },
  { to: '/stats', title: '数据统计', icon: 'mdi-chart-bar' }
]

const currentTitle = computed(() => {
  const item = navItems.find(i => i.to === route.path)
  return item?.title || 'Iris Memory'
})

const checkAuth = async () => {
  try {
    const response = await axios.get('/iris/auth/status')
    const data = response.data as { require_auth: boolean; authenticated: boolean }
    
    if (!data.require_auth) {
      isAuthenticated.value = true
    } else {
      isAuthenticated.value = data.authenticated
    }
  } catch (e) {
    console.error('检查认证状态失败:', e)
    isAuthenticated.value = false
  }
}

const handleLogin = async () => {
  if (!accessKey.value.trim()) return
  
  logging.value = true
  errorMessage.value = ''
  
  try {
    const response = await axios.post('/iris/auth/login', {
      key: accessKey.value
    })
    
    const data = response.data as { success: boolean; message?: string; error?: string }
    
    if (data.success) {
      isAuthenticated.value = true
    } else {
      errorMessage.value = data.error || '登录失败'
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { error?: string } } }
    errorMessage.value = err.response?.data?.error || '登录失败，请重试'
  } finally {
    logging.value = false
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
