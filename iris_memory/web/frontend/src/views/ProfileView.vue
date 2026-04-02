<template>
  <div class="profile-view">
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
      <!-- 群聊画像 -->
      <v-window-item value="group">
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

                <v-list v-else-if="filteredGroupList.length > 0" lines="two">
                  <v-list-item
                    v-for="group in filteredGroupList"
                    :key="group.group_id"
                    :active="selectedGroupId === group.group_id"
                    @click="selectGroup(group.group_id)"
                  >
                    <template #prepend>
                      <v-avatar color="primary" variant="tonal">
                        <v-icon icon="mdi-account-group" />
                      </v-avatar>
                    </template>

                    <v-list-item-title>{{ group.group_name || group.group_id }}</v-list-item-title>
                    <v-list-item-subtitle>
                      {{ group.member_count ? `成员: ${group.member_count}` : '' }}
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
                <span>群聊画像</span>
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

                  <div v-else-if="profileStore.currentGroupProfile">
                    <v-row>
                      <v-col cols="12" sm="6">
                        <v-text-field
                          :model-value="profileStore.currentGroupProfile.group_id"
                          label="群聊 ID"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12" sm="6">
                        <v-text-field
                          :model-value="profileStore.currentGroupProfile.group_name || '-'"
                          label="群聊名称"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentGroupProfile.current_topic || '-'"
                          label="当前话题"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentGroupProfile.atmosphere_tags?.join(', ') || '-'"
                          label="氛围标签"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentGroupProfile.interests?.join(', ') || '-'"
                          label="兴趣标签"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentGroupProfile.active_users?.join(', ') || '-'"
                          label="活跃用户"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentGroupProfile.active_time_slots?.join(', ') || '-'"
                          label="活跃时段"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentGroupProfile.common_expressions?.join(', ') || '-'"
                          label="常用语/梗"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentGroupProfile.long_term_tags?.join(', ') || '-'"
                          label="核心特征标签"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentGroupProfile.blacklist_topics?.join(', ') || '-'"
                          label="禁忌话题"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12" v-if="profileStore.currentGroupProfile.last_interaction_time">
                        <v-text-field
                          :model-value="formatTime(profileStore.currentGroupProfile.last_interaction_time)"
                          label="最后活跃时间"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>
                    </v-row>
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

      <!-- 用户画像 -->
      <v-window-item value="user">
        <v-row>
          <v-col cols="12" md="4">
            <v-card color="surface" variant="flat">
              <v-card-title class="d-flex align-center">
                <span>用户列表</span>
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

                <v-list v-else-if="filteredUserList.length > 0" lines="two">
                  <v-list-item
                    v-for="user in filteredUserList"
                    :key="user.user_id"
                    :active="selectedUserId === user.user_id"
                    @click="selectUser(user.user_id, user.group_id)"
                  >
                    <template #prepend>
                      <v-avatar color="secondary" variant="tonal">
                        <v-icon icon="mdi-account" />
                      </v-avatar>
                    </template>

                    <v-list-item-title>{{ user.nickname || user.user_id }}</v-list-item-title>
                    <v-list-item-subtitle>
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
                <span>用户画像</span>
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

                  <div v-else-if="profileStore.currentUserProfile">
                    <v-row>
                      <v-col cols="12" sm="6">
                        <v-text-field
                          :model-value="profileStore.currentUserProfile.user_id"
                          label="用户 ID"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12" sm="6">
                        <v-text-field
                          :model-value="profileStore.currentUserProfile.user_name || '-'"
                          label="昵称"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentUserProfile.historical_names?.join(', ') || '-'"
                          label="历史曾用名"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentUserProfile.current_emotional_state || '-'"
                          label="当前情感状态"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentUserProfile.personality_tags?.join(', ') || '-'"
                          label="性格标签"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentUserProfile.interests?.join(', ') || '-'"
                          label="兴趣爱好"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentUserProfile.occupation || '-'"
                          label="职业/身份"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentUserProfile.language_style || '-'"
                          label="语言风格"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentUserProfile.bot_relationship || '-'"
                          label="与Bot关系"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentUserProfile.taboo_topics?.join(', ') || '-'"
                          label="禁忌话题"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-text-field
                          :model-value="profileStore.currentUserProfile.important_events?.join(', ') || '-'"
                          label="重要事件"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12" v-if="profileStore.currentUserProfile.last_interaction_time">
                        <v-text-field
                          :model-value="formatTime(profileStore.currentUserProfile.last_interaction_time)"
                          label="最后活跃时间"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>
                    </v-row>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useProfileStore } from '@/stores'

const profileStore = useProfileStore()

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
}

const selectUser = (userId: string, groupId?: string) => {
  selectedUserId.value = userId
  selectedUserGroupId.value = groupId
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
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN')
  } catch {
    return timestamp
  }
}

watch(selectedGroupId, (newId) => {
  if (newId) {
    profileStore.fetchGroupProfile(newId)
  }
}, { immediate: true })

watch(selectedUserId, (newId) => {
  if (newId) {
    profileStore.fetchUserProfile(newId, selectedUserGroupId.value)
  }
}, { immediate: true })

onMounted(() => {
  loadGroupList()
  loadUserList()
})
</script>
