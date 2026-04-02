import type { GroupProfile, UserProfile, GroupListItem, UserListItem } from '@/types'
import apiClient from './request'

interface ApiBaseResponse {
  success: boolean
  error?: string
}

interface GroupProfileApiResponse extends ApiBaseResponse {
  profile: GroupProfile
}

interface UserProfileApiResponse extends ApiBaseResponse {
  profile: UserProfile
}

interface GroupListApiResponse extends ApiBaseResponse {
  groups: GroupListItem[]
}

interface UserListApiResponse extends ApiBaseResponse {
  users: UserListItem[]
}

export const getGroupProfile = async (groupId: string): Promise<GroupProfile> => {
  const response = await apiClient.get(`/profile/group/${groupId}`) as unknown as GroupProfileApiResponse
  if (!response.success) {
    throw new Error(response.error || '获取群聊画像失败')
  }
  return response.profile || {}
}

export const updateGroupProfile = async (groupId: string, data: Partial<GroupProfile>): Promise<void> => {
  const response = await apiClient.put(`/profile/group/${groupId}`, data) as unknown as ApiBaseResponse
  if (!response.success) {
    throw new Error(response.error || '更新群聊画像失败')
  }
}

export const getUserProfile = async (userId: string, groupId?: string): Promise<UserProfile> => {
  const params = groupId ? { group_id: groupId } : {}
  const response = await apiClient.get(`/profile/user/${userId}`, { params }) as unknown as UserProfileApiResponse
  if (!response.success) {
    throw new Error(response.error || '获取用户画像失败')
  }
  return response.profile || {}
}

export const updateUserProfile = async (userId: string, data: Partial<UserProfile>, groupId?: string): Promise<void> => {
  const params = groupId ? { group_id: groupId } : {}
  const response = await apiClient.put(`/profile/user/${userId}`, data, { params }) as unknown as ApiBaseResponse
  if (!response.success) {
    throw new Error(response.error || '更新用户画像失败')
  }
}

export const getGroupList = async (): Promise<GroupListItem[]> => {
  const response = await apiClient.get('/profile/groups') as unknown as GroupListApiResponse
  if (!response.success) {
    throw new Error(response.error || '获取群聊列表失败')
  }
  return response.groups || []
}

export const getUserList = async (groupId?: string): Promise<UserListItem[]> => {
  const params = groupId ? { group_id: groupId } : {}
  const response = await apiClient.get('/profile/users', { params }) as unknown as UserListApiResponse
  if (!response.success) {
    throw new Error(response.error || '获取用户列表失败')
  }
  return response.users || []
}
