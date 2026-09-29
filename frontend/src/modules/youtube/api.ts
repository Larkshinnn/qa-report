import { api } from '../../shared/api'

export interface YouTubeStatus {
  connected: boolean
  channel_title: string | null
  connected_by: string | null
  connected_at: string | null
  can_connect: boolean
}

export interface YouTubeVideo {
  video_id: string
  title: string
  description: string
  thumbnail_url: string | null
  published_at: string | null
  privacy_status: string
}

export interface YouTubeVideoPage {
  videos: YouTubeVideo[]
  next_page_token: string | null
}

export const youtubeApi = {
  status: (): Promise<YouTubeStatus> => api('/youtube/status'),
  videos: (pageToken?: string): Promise<YouTubeVideoPage> =>
    api(`/youtube/videos${pageToken ? `?${new URLSearchParams({ page_token: pageToken })}` : ''}`),
  upload: (form: FormData): Promise<{ video_id: string; url: string }> =>
    api('/youtube/videos', { method: 'POST', body: form }),
  disconnect: (): Promise<void> => api('/youtube/connection', { method: 'DELETE' }),
}
