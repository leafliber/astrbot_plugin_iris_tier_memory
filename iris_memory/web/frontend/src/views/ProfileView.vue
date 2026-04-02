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
                          v-model="editGroupProfile.group_id"
                          label="群聊 ID"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12" sm="6">
                        <v-text-field
                          v-model="editGroupProfile.group_name"
                          label="群聊名称"
                          variant="outlined"
                          density="comfortable"
                        />
                      </v-col>

                      <v-col cols="12" sm="6">
                        <v-text-field
                          v-model="editGroupProfile.atmosphere"
                          label="群聊氛围"
                          variant="outlined"
                          density="comfortable"
                          placeholder="例如: 友好活跃"
                        />
                      </v-col>

                      <v-col cols="12" sm="6">
                        <v-combobox
                          v-model="editGroupProfile.topics"
                          label="话题标签"
                          variant="outlined"
                          density="comfortable"
                          multiple
                          chips
                          closable-chips
                          placeholder="添加话题标签"
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-combobox
                          v-model="editGroupProfile.active_users"
                          label="活跃用户"
                          variant="outlined"
                          density="comfortable"
                          multiple
                          chips
                          closable-chips
                          placeholder="添加活跃用户"
                        />
                      </v-col>

                      <v-col cols="12" v-if="profileStore.currentGroupProfile.last_active_time">
                        <v-text-field
                          :model-value="formatTime(profileStore.currentGroupProfile.last_active_time)"
                          label="最后活跃时间"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>
                    </v-row>

                    <v-divider class="my-4" />

                    <div class="d-flex justify-end">
                      <v-btn
                        color="primary"
                        :loading="savingGroup"
                        @click="handleSaveGroupProfile"
                      >
                        <v-icon icon="mdi-content-save" class="mr-1" />
                        保存修改
                      </v-btn>
                    </div>
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
                          v-model="editUserProfile.user_id"
                          label="用户 ID"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>

                      <v-col cols="12" sm="6">
                        <v-text-field
                          v-model="editUserProfile.nickname"
                          label="昵称"
                          variant="outlined"
                          density="comfortable"
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-combobox
                          v-model="editUserProfile.interests"
                          label="兴趣标签"
                          variant="outlined"
                          density="comfortable"
                          multiple
                          chips
                          closable-chips
                          placeholder="添加兴趣标签"
                        />
                      </v-col>

                      <v-col cols="12">
                        <v-combobox
                          v-model="editUserProfile.personality_tags"
                          label="性格标签"
                          variant="outlined"
                          density="comfortable"
                          multiple
                          chips
                          closable-chips
                          placeholder="添加性格标签"
                        />
                      </v-col>

                      <v-col cols="12" v-if="profileStore.currentUserProfile.last_active_time">
                        <v-text-field
                          :model-value="formatTime(profileStore.currentUserProfile.last_active_time)"
                          label="最后活跃时间"
                          variant="outlined"
                          density="comfortable"
                          readonly
                        />
                      </v-col>
                    </v-row>

                    <v-divider class="my-4" />

                    <div class="d-flex justify-end">
                      <v-btn
                        color="primary"
                        :loading="savingUser"
                        @click="handleSaveUserProfile"
                      >
                        <v-icon icon="mdi-content-save" class="mr-1" />
                        保存修改
                      </v-btn>
                    </div>
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
import type { GroupProfile, UserProfile } from '@/types'

const profileStore = useProfileStore()

const activeTab = ref('group')
const groupSearchQuery = ref('')
const userSearchQuery = ref('')
const selectedGroupId = ref<string | null>(null)
const selectedUserId = ref<string | null>(null)
const selectedUserGroupId = ref<string | undefined>(undefined)
const savingGroup = ref(false)
const savingUser = ref(false)
const editGroupProfile = ref<Partial<GroupProfile>>({})
const editUserProfile = ref<Partial<UserProfile>>({})

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

const handleSaveGroupProfile = async () => {
  if (!selectedGroupId.value) return
  savingGroup.value = true
  try {
    await profileStore.updateGroupProfile(selectedGroupId.value, editGroupProfile.value)
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    savingGroup.value = false
  }
}

const handleSaveUserProfile = async () => {
  if (!selectedUserId.value) return
  savingUser.value = true
  try {
    await profileStore.updateUserProfile(selectedUserId.value, editUserProfile.value, selectedUserGroupId.value)
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    savingUser.value = false
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

watch(() => profileStore.currentGroupProfile, (newProfile) => {
  if (newProfile) {
    editGroupProfile.value = { ...newProfile }
  } else {
    editGroupProfile.value = {}
  }
}, { immediate: true, deep: true })

watch(() => profileStore.currentUserProfile, (newProfile) => {
  if (newProfile) {
    editUserProfile.value = { ...newProfile }
  } else {
    editUserProfile.value = {}
  }
}, { immediate: true, deep: true })

onMounted(() => {
  loadGroupList()
  loadUserList()
})
</script>
