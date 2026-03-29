import api, { ApiResponse } from './request'

// 画像数据类型
export interface Profile {
  [key: string]: any
}

// 群聊画像类型
export interface GroupProfile extends Profile {
  group_id: string
  atmosphere?: string
  active_users?: string[]
  topics?: string[]
  last_active_time?: string
}

// 用户画像类型
export interface UserProfile extends Profile {
  user_id: string
  nickname?: string
  interests?: string[]
  personality_tags?: string[]
  last_active_time?: string
}

// 群聊列表项
export interface GroupListItem {
  group_id: string
  group_name?: string
  member_count?: number
}

// 画像 API
export const profileApi = {
  // 获取群聊画像
  getGroupProfile: async (groupId: string): Promise<ApiResponse<{ profile: GroupProfile }>> => {
    return api.get(`/profile/group/${groupId}`)
  },

  // 更新群聊画像
  updateGroupProfile: async (groupId: string, data: Partial<GroupProfile>): Promise<ApiResponse> => {
    return api.put(`/profile/group/${groupId}`, data)
  },

  // 获取用户画像
  getUserProfile: async (userId: string, groupId?: string): Promise<ApiResponse<{ profile: UserProfile }>> => {
    return api.get(`/profile/user/${userId}`, {
      params: { group_id: groupId }
    })
  },

  // 更新用户画像
  updateUserProfile: async (userId: string, data: Partial<UserProfile>, groupId?: string): Promise<ApiResponse> => {
    return api.put(`/profile/user/${userId}`, data, {
      params: { group_id: groupId }
    })
  },

  // 获取群聊列表
  listGroups: async (): Promise<ApiResponse<{ groups: GroupListItem[] }>> => {
    return api.get('/profile/groups')
  }
}
