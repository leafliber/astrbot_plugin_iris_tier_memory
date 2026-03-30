<template>
  <div class="profile-view">
    <v-row>
      <!-- 群聊列表 -->
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
            <v-progress-linear
              v-if="profileStore.groupListLoading"
              indeterminate
              color="primary"
            />

            <v-list v-else-if="profileStore.groupList.length > 0" lines="two">
              <v-list-item
                v-for="group in profileStore.groupList"
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
              <div class="mt-2">暂无群聊数据</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 群聊画像详情 -->
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
                  <!-- 群聊ID -->
                  <v-col cols="12" sm="6">
                    <v-text-field
                      v-model="editProfile.group_id"
                      label="群聊 ID"
                      variant="outlined"
                      density="comfortable"
                      readonly
                    />
                  </v-col>

                  <!-- 群聊名称 -->
                  <v-col cols="12" sm="6">
                    <v-text-field
                      v-model="editProfile.group_name"
                      label="群聊名称"
                      variant="outlined"
                      density="comfortable"
                    />
                  </v-col>

                  <!-- 氛围 -->
                  <v-col cols="12" sm="6">
                    <v-text-field
                      v-model="editProfile.atmosphere"
                      label="群聊氛围"
                      variant="outlined"
                      density="comfortable"
                      placeholder="例如: 友好活跃"
                    />
                  </v-col>

                  <!-- 话题 -->
                  <v-col cols="12" sm="6">
                    <v-combobox
                      v-model="editProfile.topics"
                      label="话题标签"
                      variant="outlined"
                      density="comfortable"
                      multiple
                      chips
                      closable-chips
                      placeholder="添加话题标签"
                    />
                  </v-col>

                  <!-- 活跃用户 -->
                  <v-col cols="12">
                    <v-combobox
                      v-model="editProfile.active_users"
                      label="活跃用户"
                      variant="outlined"
                      density="comfortable"
                      multiple
                      chips
                      closable-chips
                      placeholder="添加活跃用户"
                    />
                  </v-col>

                  <!-- 最后活跃时间 -->
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
                    :loading="saving"
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useProfileStore, useAppStore } from '@/stores'
import type { GroupProfile } from '@/types'

const profileStore = useProfileStore()
const appStore = useAppStore()

const { selectedGroupId } = storeToRefs(appStore)

const saving = ref(false)
const editProfile = ref<Partial<GroupProfile>>({})

// 加载群聊列表
const loadGroupList = () => {
  profileStore.fetchGroupList()
}

// 选择群聊
const selectGroup = (groupId: string) => {
  appStore.selectGroup(groupId)
}

// 加载群聊画像
const loadGroupProfile = () => {
  if (selectedGroupId.value) {
    profileStore.fetchGroupProfile(selectedGroupId.value)
  }
}

// 保存群聊画像
const handleSaveGroupProfile = async () => {
  if (!selectedGroupId.value) return

  saving.value = true
  try {
    await profileStore.updateGroupProfile(selectedGroupId.value, editProfile.value)
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    saving.value = false
  }
}

// 格式化时间
const formatTime = (timestamp?: string): string => {
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN')
  } catch {
    return timestamp
  }
}

// 监听选中群聊变化
watch(selectedGroupId, (newId) => {
  if (newId) {
    profileStore.fetchGroupProfile(newId)
  }
}, { immediate: true })

// 监听画像数据变化，同步到编辑表单
watch(() => profileStore.currentGroupProfile, (newProfile) => {
  if (newProfile) {
    editProfile.value = { ...newProfile }
  } else {
    editProfile.value = {}
  }
}, { immediate: true, deep: true })

onMounted(() => {
  loadGroupList()
})
</script>
