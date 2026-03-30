import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { GroupProfile, UserProfile, GroupListItem } from '@/types'
import * as profileApi from '@/api/profile'

export const useProfileStore = defineStore('profile', () => {
  // 群聊列表
  const groupList = ref<GroupListItem[]>([])
  const groupListLoading = ref(false)

  // 当前群聊画像
  const currentGroupProfile = ref<GroupProfile | null>(null)
  const groupProfileLoading = ref(false)

  // 当前用户画像
  const currentUserProfile = ref<UserProfile | null>(null)
  const userProfileLoading = ref(false)

  // 获取群聊列表
  const fetchGroupList = async () => {
    groupListLoading.value = true
    try {
      groupList.value = await profileApi.getGroupList()
    } catch (error) {
      console.error('获取群聊列表失败:', error)
      groupList.value = []
    } finally {
      groupListLoading.value = false
    }
  }

  // 获取群聊画像
  const fetchGroupProfile = async (groupId: string) => {
    groupProfileLoading.value = true
    try {
      currentGroupProfile.value = await profileApi.getGroupProfile(groupId)
    } catch (error) {
      console.error('获取群聊画像失败:', error)
      currentGroupProfile.value = null
    } finally {
      groupProfileLoading.value = false
    }
  }

  // 更新群聊画像
  const updateGroupProfile = async (groupId: string, data: Partial<GroupProfile>) => {
    await profileApi.updateGroupProfile(groupId, data)
    await fetchGroupProfile(groupId)
  }

  // 获取用户画像
  const fetchUserProfile = async (userId: string, groupId?: string) => {
    userProfileLoading.value = true
    try {
      currentUserProfile.value = await profileApi.getUserProfile(userId, groupId)
    } catch (error) {
      console.error('获取用户画像失败:', error)
      currentUserProfile.value = null
    } finally {
      userProfileLoading.value = false
    }
  }

  // 更新用户画像
  const updateUserProfile = async (userId: string, data: Partial<UserProfile>, groupId?: string) => {
    await profileApi.updateUserProfile(userId, data, groupId)
    await fetchUserProfile(userId, groupId)
  }

  return {
    groupList,
    groupListLoading,
    currentGroupProfile,
    groupProfileLoading,
    currentUserProfile,
    userProfileLoading,
    fetchGroupList,
    fetchGroupProfile,
    updateGroupProfile,
    fetchUserProfile,
    updateUserProfile
  }
})
