<template>
  <div class="profile-view">
    <ComponentDisabled
      :status="status"
      :error="error"
      :error-type="errorType"
      component-name="画像管理"
      @retry="refreshState"
    >
      <v-tabs v-model="activeTab" color="primary" align-tabs="start">
        <v-tab value="group">
          <v-icon icon="mdi-account-group" class="mr-1" />
          群聊画像
        </v-tab>
        <v-tab value="user">
          <v-icon icon="mdi-account" class="mr-1" />
          用户画像
        </v-tab>
      </v-tabs>

      <v-window v-model="activeTab" class="mt-4">
        <v-window-item value="group">
          <v-row>
            <v-col cols="12" md="4">
              <v-card color="surface" variant="flat" class="list-card">
                <v-card-title class="d-flex align-center">
                  <v-icon icon="mdi-account-group" color="primary" class="mr-2" />
                  群聊列表
                  <v-spacer />
                  <v-btn
                    icon="mdi-refresh"
                    variant="text"
                    size="small"
                    :loading="profileStore.groupListLoading"
                    @click="loadGroupList"
                  />
                </v-card-title>
                <v-card-text class="pa-0">
                  <v-text-field
                    v-model="groupSearchQuery"
                    placeholder="搜索群聊..."
                    prepend-inner-icon="mdi-magnify"
                    variant="outlined"
                    density="compact"
                    hide-details
                    class="ma-2"
                    clearable
                  />
                  <v-progress-linear
                    v-if="profileStore.groupListLoading"
                    indeterminate
                    color="primary"
                  />

                  <v-list v-else-if="filteredGroupList.length > 0" lines="two" class="py-0">
                    <v-list-item
                      v-for="group in filteredGroupList"
                      :key="group.group_id"
                      :active="selectedGroupId === group.group_id"
                      @click="selectGroup(group.group_id)"
                    >
                      <template #prepend>
                        <v-avatar color="primary" variant="tonal" size="36">
                          <v-icon icon="mdi-account-group" size="20" />
                        </v-avatar>
                      </template>

                      <v-list-item-title>{{ group.group_name || group.group_id }}</v-list-item-title>
                      <v-list-item-subtitle>
                        <v-icon icon="mdi-account-multiple" size="small" class="mr-1" />
                        {{ group.member_count || '?' }} 成员
                      </v-list-item-subtitle>
                    </v-list-item>
                  </v-list>

                  <div v-else class="text-center text-medium-emphasis py-8">
                    <v-icon icon="mdi-account-group-outline" size="48" />
                    <div class="mt-2">{{ groupSearchQuery ? '未找到匹配的群聊' : '暂无群聊数据' }}</div>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>

            <v-col cols="12" md="8">
              <v-card color="surface" variant="flat">
                <v-card-title class="d-flex align-center">
                  <v-icon icon="mdi-information" color="primary" class="mr-2" />
                  群聊画像详情
                  <v-spacer />
                  <v-btn
                    v-if="selectedGroupId"
                    icon="mdi-refresh"
                    variant="text"
                    size="small"
                    :loading="profileStore.groupProfileLoading"
                    @click="loadGroupProfile"
                  />
                </v-card-title>
                <v-card-text>
                  <template v-if="selectedGroupId">
                    <v-progress-linear
                      v-if="profileStore.groupProfileLoading"
                      indeterminate
                      color="primary"
                      class="mb-4"
                    />

                    <div v-else-if="profileStore.currentGroupProfile" class="profile-content">
                      <div class="profile-header mb-4">
                        <v-avatar color="primary" size="56" class="mr-4">
                          <v-icon icon="mdi-account-group" size="32" />
                        </v-avatar>
                        <div>
                          <div class="text-h5">{{ profileStore.currentGroupProfile.group_name || '未命名群聊' }}</div>
                          <div class="text-caption text-medium-emphasis">{{ profileStore.currentGroupProfile.group_id }}</div>
                        </div>
                      </div>

                      <v-card variant="outlined" class="info-card">
                        <v-card-title class="text-subtitle-2 pb-0">
                          <v-icon icon="mdi-emoticon-outline" color="accent" class="mr-2" />
                          群聊氛围
                        </v-card-title>
                        <v-card-text>
                          <div v-if="profileStore.currentGroupProfile.atmosphere_tags?.length" class="tags-container">
                            <v-chip
                              v-for="tag in profileStore.currentGroupProfile.atmosphere_tags"
                              :key="tag"
                              color="accent"
                              variant="tonal"
                              size="small"
                              class="ma-1"
                            >
                              {{ tag }}
                            </v-chip>
                          </div>
                          <div v-else class="text-medium-emphasis text-body-2">暂无氛围标签</div>
                        </v-card-text>
                      </v-card>

                      <v-card variant="outlined" class="info-card mt-4">
                        <v-card-title class="text-subtitle-2 pb-0">
                          <v-icon icon="mdi-heart" color="pink" class="mr-2" />
                          兴趣偏好
                        </v-card-title>
                        <v-card-text>
                          <div v-if="profileStore.currentGroupProfile.interests?.length" class="tags-container">
                            <v-chip
                              v-for="interest in profileStore.currentGroupProfile.interests"
                              :key="interest"
                              color="pink"
                              variant="tonal"
                              size="small"
                              class="ma-1"
                            >
                              {{ interest }}
                            </v-chip>
                          </div>
                          <div v-else class="text-medium-emphasis text-body-2">暂无兴趣标签</div>
                        </v-card-text>
                      </v-card>

                      <v-card variant="outlined" class="info-card mt-4">
                        <v-card-title class="text-subtitle-2 pb-0">
                          <v-icon icon="mdi-star" color="warning" class="mr-2" />
                          核心特征
                        </v-card-title>
                        <v-card-text>
                          <div v-if="profileStore.currentGroupProfile.long_term_tags?.length" class="tags-container">
                            <v-chip
                              v-for="tag in profileStore.currentGroupProfile.long_term_tags"
                              :key="tag"
                              color="warning"
                              variant="tonal"
                              size="small"
                              class="ma-1"
                            >
                              {{ tag }}
                            </v-chip>
                          </div>
                          <div v-else class="text-medium-emphasis text-body-2">暂无数据</div>
                        </v-card-text>
                      </v-card>

                      <v-card variant="outlined" class="info-card mt-4" v-if="profileStore.currentGroupProfile.blacklist_topics?.length">
                        <v-card-title class="text-subtitle-2 pb-0">
                          <v-icon icon="mdi-block-helper" color="error" class="mr-2" />
                          禁忌话题
                        </v-card-title>
                        <v-card-text>
                          <div class="tags-container">
                            <v-chip
                              v-for="topic in profileStore.currentGroupProfile.blacklist_topics"
                              :key="topic"
                              color="error"
                              variant="tonal"
                              size="small"
                              class="ma-1"
                            >
                              {{ topic }}
                            </v-chip>
                          </div>
                        </v-card-text>
                      </v-card>
                    </div>

                    <div v-else class="text-center text-medium-emphasis py-8">
                      <v-icon icon="mdi-file-document-outline" size="64" />
                      <div class="mt-2">暂无群聊画像数据</div>
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
        </v-window-item>

        <v-window-item value="user">
          <v-row>
            <v-col cols="12" md="4">
              <v-card color="surface" variant="flat" class="list-card">
                <v-card-title class="d-flex align-center">
                  <v-icon icon="mdi-account" color="secondary" class="mr-2" />
                  用户列表
                  <v-spacer />
                  <v-btn
                    icon="mdi-refresh"
                    variant="text"
                    size="small"
                    :loading="profileStore.userListLoading"
                    @click="loadUserList"
                  />
                </v-card-title>
                <v-card-text class="pa-0">
                  <v-text-field
                    v-model="userSearchQuery"
                    placeholder="搜索用户..."
                    prepend-inner-icon="mdi-magnify"
                    variant="outlined"
                    density="compact"
                    hide-details
                    class="ma-2"
                    clearable
                  />
                  <v-progress-linear
                    v-if="profileStore.userListLoading"
                    indeterminate
                    color="primary"
                  />

                  <v-list v-else-if="filteredUserList.length > 0" lines="two" class="py-0">
                    <v-list-item
                      v-for="user in filteredUserList"
                      :key="user.user_id + (user.group_id || 'global')"
                      :active="selectedUserId === user.user_id"
                      @click="selectUser(user.user_id, user.group_id)"
                    >
                      <template #prepend>
                        <v-avatar color="secondary" variant="tonal" size="36">
                          <v-icon icon="mdi-account" size="20" />
                        </v-avatar>
                      </template>

                      <v-list-item-title>{{ user.nickname || user.user_id }}</v-list-item-title>
                      <v-list-item-subtitle>
                        <v-icon icon="mdi-account-group" size="small" class="mr-1" />
                        {{ user.group_id || '全局' }}
                      </v-list-item-subtitle>
                    </v-list-item>
                  </v-list>

                  <div v-else class="text-center text-medium-emphasis py-8">
                    <v-icon icon="mdi-account-outline" size="48" />
                    <div class="mt-2">{{ userSearchQuery ? '未找到匹配的用户' : '暂无用户数据' }}</div>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>

            <v-col cols="12" md="8">
              <v-card color="surface" variant="flat">
                <v-card-title class="d-flex align-center">
                  <v-icon icon="mdi-account-details" color="secondary" class="mr-2" />
                  用户画像详情
                  <v-spacer />
                  <v-btn
                    v-if="selectedUserId"
                    icon="mdi-refresh"
                    variant="text"
                    size="small"
                    :loading="profileStore.userProfileLoading"
                    @click="loadUserProfile"
                  />
                </v-card-title>
                <v-card-text>
                  <template v-if="selectedUserId">
                    <v-progress-linear
                      v-if="profileStore.userProfileLoading"
                      indeterminate
                      color="primary"
                      class="mb-4"
                    />

                    <div v-else-if="profileStore.currentUserProfile" class="profile-content">
                      <div class="profile-header mb-4">
                        <v-avatar color="secondary" size="56" class="mr-4">
                          <v-icon icon="mdi-account" size="32" />
                        </v-avatar>
                        <div>
                          <div class="text-h5">{{ profileStore.currentUserProfile.user_name || '未命名用户' }}</div>
                          <div class="text-caption text-medium-emphasis">{{ profileStore.currentUserProfile.user_id }}</div>
                        </div>
                      </div>

                      <v-row>
                        <v-col cols="12" sm="6">
                          <v-card variant="outlined" class="info-card">
                            <v-card-text>
                              <div class="d-flex align-center mb-2">
                                <v-icon icon="mdi-briefcase" color="primary" size="small" class="mr-2" />
                                <span class="text-caption text-medium-emphasis">职业/身份</span>
                              </div>
                              <div class="text-body-1">{{ profileStore.currentUserProfile.occupation || '暂无' }}</div>
                            </v-card-text>
                          </v-card>
                        </v-col>

                        <v-col cols="12" sm="6">
                          <v-card variant="outlined" class="info-card">
                            <v-card-text>
                              <div class="d-flex align-center mb-2">
                                <v-icon icon="mdi-translate" color="info" size="small" class="mr-2" />
                                <span class="text-caption text-medium-emphasis">语言风格</span>
                              </div>
                              <div class="text-body-1">{{ profileStore.currentUserProfile.language_style || '暂无' }}</div>
                            </v-card-text>
                          </v-card>
                        </v-col>
                      </v-row>

                      <v-row>
                        <v-col cols="12" sm="6">
                          <v-card variant="outlined" class="info-card">
                            <v-card-text>
                              <div class="d-flex align-center mb-2">
                                <v-icon icon="mdi-robot" color="accent" size="small" class="mr-2" />
                                <span class="text-caption text-medium-emphasis">与Bot关系</span>
                              </div>
                              <div class="text-body-1">{{ profileStore.currentUserProfile.bot_relationship || '暂无' }}</div>
                            </v-card-text>
                          </v-card>
                        </v-col>
                      </v-row>

                      <v-card variant="outlined" class="info-card mt-4">
                        <v-card-title class="text-subtitle-2 pb-0">
                          <v-icon icon="mdi-account-switch" color="cyan" class="mr-2" />
                          历史曾用名
                        </v-card-title>
                        <v-card-text>
                          <div v-if="profileStore.currentUserProfile.historical_names?.length">
                            <v-chip
                              v-for="name in profileStore.currentUserProfile.historical_names"
                              :key="name"
                              color="cyan"
                              variant="tonal"
                              size="small"
                              class="ma-1"
                            >
                              {{ name }}
                            </v-chip>
                          </div>
                          <div v-else class="text-medium-emphasis text-body-2">暂无历史名称</div>
                        </v-card-text>
                      </v-card>

                      <v-card variant="outlined" class="info-card mt-4">
                        <v-card-title class="text-subtitle-2 pb-0">
                          <v-icon icon="mdi-brain" color="purple" class="mr-2" />
                          性格特征
                        </v-card-title>
                        <v-card-text>
                          <div v-if="profileStore.currentUserProfile.personality_tags?.length" class="tags-container">
                            <v-chip
                              v-for="tag in profileStore.currentUserProfile.personality_tags"
                              :key="tag"
                              color="purple"
                              variant="tonal"
                              size="small"
                              class="ma-1"
                            >
                              {{ tag }}
                            </v-chip>
                          </div>
                          <div v-else class="text-medium-emphasis text-body-2">暂无性格标签</div>
                        </v-card-text>
                      </v-card>

                      <v-card variant="outlined" class="info-card mt-4">
                        <v-card-title class="text-subtitle-2 pb-0">
                          <v-icon icon="mdi-heart" color="pink" class="mr-2" />
                          兴趣爱好
                        </v-card-title>
                        <v-card-text>
                          <div v-if="profileStore.currentUserProfile.interests?.length" class="tags-container">
                            <v-chip
                              v-for="interest in profileStore.currentUserProfile.interests"
                              :key="interest"
                              color="pink"
                              variant="tonal"
                              size="small"
                              class="ma-1"
                            >
                              {{ interest }}
                            </v-chip>
                          </div>
                          <div v-else class="text-medium-emphasis text-body-2">暂无兴趣标签</div>
                        </v-card-text>
                      </v-card>

                      <v-card variant="outlined" class="info-card mt-4" v-if="profileStore.currentUserProfile.important_events?.length">
                        <v-card-title class="text-subtitle-2 pb-0">
                          <v-icon icon="mdi-calendar-star" color="warning" class="mr-2" />
                          重要事件
                        </v-card-title>
                        <v-card-text>
                          <v-list density="compact" class="bg-transparent pa-0">
                            <v-list-item
                              v-for="(event, idx) in profileStore.currentUserProfile.important_events"
                              :key="idx"
                              class="px-0"
                            >
                              <template #prepend>
                                <v-icon icon="mdi-star" color="warning" size="small" />
                              </template>
                              <v-list-item-title>{{ event }}</v-list-item-title>
                            </v-list-item>
                          </v-list>
                        </v-card-text>
                      </v-card>

                      <v-card variant="outlined" class="info-card mt-4" v-if="profileStore.currentUserProfile.important_dates?.length">
                        <v-card-title class="text-subtitle-2 pb-0">
                          <v-icon icon="mdi-calendar-clock" color="success" class="mr-2" />
                          重要日期
                        </v-card-title>
                        <v-card-text>
                          <v-list density="compact" class="bg-transparent pa-0">
                            <v-list-item
                              v-for="(item, idx) in profileStore.currentUserProfile.important_dates"
                              :key="idx"
                              class="px-0"
                            >
                              <template #prepend>
                                <v-icon icon="mdi-calendar" color="success" size="small" />
                              </template>
                              <v-list-item-title>{{ item.description }}</v-list-item-title>
                              <v-list-item-subtitle>{{ item.date }}</v-list-item-subtitle>
                            </v-list-item>
                          </v-list>
                        </v-card-text>
                      </v-card>

                      <v-card variant="outlined" class="info-card mt-4" v-if="profileStore.currentUserProfile.taboo_topics?.length">
                        <v-card-title class="text-subtitle-2 pb-0">
                          <v-icon icon="mdi-block-helper" color="error" class="mr-2" />
                          禁忌话题
                        </v-card-title>
                        <v-card-text>
                          <div class="tags-container">
                            <v-chip
                              v-for="topic in profileStore.currentUserProfile.taboo_topics"
                              :key="topic"
                              color="error"
                              variant="tonal"
                              size="small"
                              class="ma-1"
                            >
                              {{ topic }}
                            </v-chip>
                          </div>
                        </v-card-text>
                      </v-card>
                    </div>

                    <div v-else class="text-center text-medium-emphasis py-8">
                      <v-icon icon="mdi-file-document-outline" size="64" />
                      <div class="mt-2">暂无用户画像数据</div>
                    </div>
                  </template>

                  <div v-else class="text-center text-medium-emphasis py-8">
                    <v-icon icon="mdi-hand-pointing-up" size="64" class="mb-2" />
                    <div>请从左侧选择一个用户</div>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-window-item>
      </v-window>
    </ComponentDisabled>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useProfileStore } from '@/stores'
import { useComponentState } from '@/composables/useComponentState'
import ComponentDisabled from '@/components/ComponentDisabled.vue'

const profileStore = useProfileStore()
const { status, error, errorType, refreshState } = useComponentState('profile')

const activeTab = ref('group')
const groupSearchQuery = ref('')
const userSearchQuery = ref('')
const selectedGroupId = ref<string | null>(null)
const selectedUserId = ref<string | null>(null)
const selectedUserGroupId = ref<string | undefined>(undefined)

const filteredGroupList = computed(() => {
  if (!groupSearchQuery.value) return profileStore.groupList
  const query = groupSearchQuery.value.toLowerCase()
  return profileStore.groupList.filter(g => 
    (g.group_name?.toLowerCase().includes(query)) || 
    g.group_id.toLowerCase().includes(query)
  )
})

const filteredUserList = computed(() => {
  if (!userSearchQuery.value) return profileStore.userList
  const query = userSearchQuery.value.toLowerCase()
  return profileStore.userList.filter(u => 
    (u.nickname?.toLowerCase().includes(query)) || 
    u.user_id.toLowerCase().includes(query)
  )
})

const loadGroupList = () => {
  profileStore.fetchGroupList()
}

const loadUserList = () => {
  profileStore.fetchUserList()
}

const selectGroup = (groupId: string) => {
  selectedGroupId.value = groupId
  profileStore.fetchGroupProfile(groupId)
}

const selectUser = (userId: string, groupId?: string) => {
  selectedUserId.value = userId
  selectedUserGroupId.value = groupId
  profileStore.fetchUserProfile(userId, groupId)
}

const loadGroupProfile = () => {
  if (selectedGroupId.value) {
    profileStore.fetchGroupProfile(selectedGroupId.value)
  }
}

const loadUserProfile = () => {
  if (selectedUserId.value) {
    profileStore.fetchUserProfile(selectedUserId.value, selectedUserGroupId.value)
  }
}

const formatTime = (timestamp?: string): string => {
  if (!timestamp) return '未知时间'
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
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
  if (activeTab.value === 'group') {
    loadGroupList()
    if (selectedGroupId.value) loadGroupProfile()
  } else {
    loadUserList()
    if (selectedUserId.value) loadUserProfile()
  }
}

watch(activeTab, (newTab) => {
  if (newTab === 'group' && profileStore.groupList.length === 0) {
    loadGroupList()
  } else if (newTab === 'user' && profileStore.userList.length === 0) {
    loadUserList()
  }
})

onMounted(() => {
  loadGroupList()
  window.addEventListener('iris:refresh', handleRefresh)
})
</script>

<style scoped>
.profile-view {
  height: 100%;
}

.list-card {
  max-height: calc(100vh - 200px);
  display: flex;
  flex-direction: column;
}

.list-card :deep(.v-card-text) {
  flex: 1;
  overflow-y: auto;
}

.profile-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.profile-header {
  display: flex;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid rgb(var(--v-theme-surface-variant));
}

.info-card {
  transition: all 0.2s ease;
}

.info-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  margin: -4px;
}
</style>
