import type { ApiResponse, GroupProfile, UserProfile, GroupListItem } from '@/types'
import apiClient from './request'

// 获取群聊画像
export const getGroupProfile = async (groupId: string): Promise<GroupProfile> => {
  const response = await apiClient.get<unknown>(`/profile/group/${groupId}`) as ApiResponse<{ profile: GroupProfile }>
  if (!response.success) {
    throw new Error(response.error || '获取群聊画像失败')
  }
  return response.profile || {}
}

// 更新群聊画像
export const updateGroupProfile = async (groupId: string, data: Partial<GroupProfile>): Promise<void> => {
  const response = await apiClient.put<unknown>(`/profile/group/${groupId}`, data) as ApiResponse<void>
  if (!response.success) {
    throw new Error(response.error || '更新群聊画像失败')
  }
}

// 获取用户画像
export const getUserProfile = async (userId: string, groupId?: string): Promise<UserProfile> => {
  const params = groupId ? { group_id: groupId } : {}
  const response = await apiClient.get<unknown>(`/profile/user/${userId}`, { params }) as ApiResponse<{ profile: UserProfile }>
  if (!response.success) {
    throw new Error(response.error || '获取用户画像失败')
  }
  return response.profile || {}
}

// 更新用户画像
export const updateUserProfile = async (userId: string, data: Partial<UserProfile>, groupId?: string): Promise<void> => {
  const params = groupId ? { group_id: groupId } : {}
  const response = await apiClient.put<unknown>(`/profile/user/${userId}`, data, { params }) as ApiResponse<void>
  if (!response.success) {
    throw new Error(response.error || '更新用户画像失败')
  }
}

// 获取群聊列表
export const getGroupList = async (): Promise<GroupListItem[]> => {
  const response = await apiClient.get<unknown>('/profile/groups') as ApiResponse<{ groups: GroupListItem[] }>
  if (!response.success) {
    throw new Error(response.error || '获取群聊列表失败')
  }
  return response.groups || []
}
