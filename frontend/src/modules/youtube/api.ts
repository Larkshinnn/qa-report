import { api } from '../../shared/api'

export interface YouTubeStatus {
  connected: boolean
  channel_title: string | null
  connected_by: string | null
  connected_at: string | null
  can_connect: boolean
}

export type PrivacyStatus = 'private' | 'unlisted' | 'public'

export interface YouTubeVideo {
  video_id: string
  title: string
  description: string
  thumbnail_url: string | null
  published_at: string | null
  privacy_status: string
}

export interface YouTubeVideoList {
  videos: YouTubeVideo[]
  truncated: boolean
}

export interface YouTubeVideoUpdate {
  title: string
  description: string
  privacy_status: PrivacyStatus
}

export const youtubeApi = {
  status: (): Promise<YouTubeStatus> => api('/youtube/status'),
  videos: (): Promise<YouTubeVideoList> => api('/youtube/videos'),
  upload: (form: FormData): Promise<{ video_id: string; url: string }> =>
    api('/youtube/videos', { method: 'POST', body: form }),
  update: (videoId: string, body: YouTubeVideoUpdate): Promise<YouTubeVideo> =>
    api(`/youtube/videos/${encodeURIComponent(videoId)}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  remove: (videoId: string): Promise<void> =>
    api(`/youtube/videos/${encodeURIComponent(videoId)}`, { method: 'DELETE' }),
  disconnect: (): Promise<void> => api('/youtube/connection', { method: 'DELETE' }),
}
