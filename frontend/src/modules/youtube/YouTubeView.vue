<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { errorMessage } from '../../shared/api'
import { useToast } from '../../shared/composables/useToast'
import UiBreadcrumbs from '../../shared/components/ui/UiBreadcrumbs.vue'
import UiButton from '../../shared/components/ui/UiButton.vue'
import UiCard from '../../shared/components/ui/UiCard.vue'
import UiErrorState from '../../shared/components/ui/UiErrorState.vue'
import UiInput from '../../shared/components/ui/UiInput.vue'
import UiSelect from '../../shared/components/ui/UiSelect.vue'
import UiSkeleton from '../../shared/components/ui/UiSkeleton.vue'
import UiTextarea from '../../shared/components/ui/UiTextarea.vue'
import { youtubeApi, type YouTubeStatus, type YouTubeVideo } from './api'

const route = useRoute()
const { notify } = useToast()
const status = ref<YouTubeStatus>()
const videos = ref<YouTubeVideo[]>([])
const nextToken = ref<string | null>(null)
const pageTokens = ref<(string | undefined)[]>([undefined])
const pageIndex = ref(0)
const title = ref('')
const description = ref('')
const tags = ref('')
const privacy = ref('private')
const file = ref<File>()
const fileInput = ref<HTMLInputElement>()
const previewUrl = ref('')
const uploadedUrl = ref('')
const loading = ref(false)
const uploading = ref(false)
const error = ref('')
const connected = computed(() => status.value?.connected ?? false)
const canConnect = computed(() => status.value?.can_connect ?? false)

function connect(): void {
  const base = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
  window.location.assign(`${base}/youtube/connect`)
}

async function loadVideos(token?: string): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const page = await youtubeApi.videos(token)
    videos.value = page.videos
    nextToken.value = page.next_page_token
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    status.value = await youtubeApi.status()
    if (status.value.connected) await loadVideos(pageTokens.value[pageIndex.value])
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}

function selectFile(event: Event): void {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  const selected = (event.target as HTMLInputElement).files?.[0]
  file.value = selected
  previewUrl.value = selected ? URL.createObjectURL(selected) : ''
}

async function upload(): Promise<void> {
  if (!file.value || uploading.value) return
  uploading.value = true
  error.value = ''
  const form = new FormData()
  form.set('video', file.value)
  form.set('title', title.value)
  form.set('description', description.value)
  form.set('tags', tags.value)
  form.set('privacy_status', privacy.value)
  try {
    const result = await youtubeApi.upload(form)
    uploadedUrl.value = result.url
    notify('Video berhasil diunggah ke channel bersama.')
    title.value = ''
    description.value = ''
    tags.value = ''
    file.value = undefined
    if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
    if (fileInput.value) fileInput.value.value = ''
    pageTokens.value = [undefined]
    pageIndex.value = 0
    await loadVideos()
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    uploading.value = false
  }
}

async function disconnect(): Promise<void> {
  if (!window.confirm('Lepaskan koneksi channel YouTube bersama?')) return
  try {
    await youtubeApi.disconnect()
    status.value = await youtubeApi.status()
    videos.value = []
    notify('Koneksi YouTube dilepas.')
  } catch (cause) {
    error.value = errorMessage(cause)
  }
}

async function nextPage(): Promise<void> {
  if (!nextToken.value) return
  pageTokens.value = [...pageTokens.value.slice(0, pageIndex.value + 1), nextToken.value]
  pageIndex.value += 1
  await loadVideos(nextToken.value)
}

async function previousPage(): Promise<void> {
  if (pageIndex.value === 0) return
  pageIndex.value -= 1
  await loadVideos(pageTokens.value[pageIndex.value])
}

function dateLabel(value: string | null): string {
  return value ? new Intl.DateTimeFormat('id-ID', { dateStyle: 'medium' }).format(new Date(value)) : '—'
}

onBeforeUnmount(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})

onMounted(async () => {
  if (route.query.connected === '1') notify('Channel YouTube berhasil dihubungkan.')
  await load()
})
</script>

<template>
  <UiBreadcrumbs :items="[{ label: 'YouTube' }]" />
  <div class="page-header">
    <div>
      <h1>YouTube bersama</h1>
      <p>Kelola konten pada satu channel bersama. Semua anggota dapat melihat dan mengunggah video.</p>
    </div>
  </div>
  <UiErrorState v-if="error" :message="error" retryable @retry="load" />
  <UiSkeleton v-else-if="!status || loading" :lines="4" />
  <template v-else>
    <UiCard padding="md" class="connection-card">
      <div class="connection-copy">
        <template v-if="connected">
          <strong>Terhubung ke {{ status.channel_title }}</strong>
          <span class="small muted">Dihubungkan oleh {{ status.connected_by }}</span>
        </template>
        <template v-else>
          <strong>Channel YouTube belum dihubungkan</strong>
          <span class="small muted">Admin perlu menghubungkan akun pemilik channel satu kali.</span>
        </template>
      </div>
      <div class="button-row">
        <UiButton v-if="!connected && canConnect" @click="connect">Hubungkan channel</UiButton>
        <UiButton v-if="connected && canConnect" variant="secondary" @click="disconnect">Lepas koneksi</UiButton>
      </div>
    </UiCard>
    <template v-if="connected">
      <UiCard padding="md" class="upload-card">
        <h2>Upload video</h2>
        <p v-if="uploadedUrl" class="upload-success">
          Upload berhasil. <a :href="uploadedUrl" target="_blank" rel="noopener noreferrer">Buka video di YouTube</a>
        </p>
        <div class="upload-layout">
          <form class="upload-form" @submit.prevent="upload">
            <UiInput v-model="title" class="title-input" label="Judul video" required maxlength="100" />
            <UiTextarea v-model="description" label="Deskripsi" :rows="4" maxlength="5000" />
            <UiInput v-model="tags" label="Tag" hint="Pisahkan dengan koma" maxlength="1000" />
            <UiSelect
              v-model="privacy"
              label="Privasi video"
              :options="[
                { value: 'private', label: 'Private' },
                { value: 'unlisted', label: 'Unlisted' },
                { value: 'public', label: 'Public' },
              ]"
            />
            <label class="file-field">
              <span>File video <span aria-hidden="true">*</span></span>
              <input ref="fileInput" class="field-control" type="file" accept="video/*" required @change="selectFile" />
              <small v-if="file" class="muted">{{ file.name }} · {{ (file.size / 1048576).toFixed(1) }} MB</small>
              <small v-else class="muted">Maksimal 512 MB per video.</small>
            </label>
            <UiButton class="upload-submit" type="submit" :loading="uploading" :disabled="!file || !title.trim()">Upload ke YouTube</UiButton>
          </form>
          <aside class="video-preview" aria-label="Preview video">
            <div class="preview-frame">
              <video v-if="previewUrl" :src="previewUrl" controls preload="metadata" />
              <div v-else class="preview-empty">
                <strong>Preview video</strong>
                <span class="small muted">Pilih file untuk melihat pratinjau</span>
              </div>
            </div>
            <div class="preview-copy">
              <strong>{{ title || 'Judul video' }}</strong>
              <span class="small muted">Pratinjau sebelum diupload · {{ privacy }}</span>
              <p>{{ description || 'Deskripsi video akan tampil di sini.' }}</p>
            </div>
          </aside>
        </div>
      </UiCard>
      <section class="content-section">
        <div class="section-heading">
          <div><h2>Konten channel</h2><p>Video terbaru dari channel YouTube bersama.</p></div>
          <UiButton variant="secondary" :loading="loading" @click="loadVideos(pageTokens[pageIndex])">Muat ulang</UiButton>
        </div>
        <UiSkeleton v-if="loading" :lines="3" />
        <UiErrorState v-else-if="error" :message="error" retryable @retry="loadVideos(pageTokens[pageIndex])" />
        <UiCard v-else-if="!videos.length" padding="md"><p>Belum ada video di channel ini.</p></UiCard>
        <div v-else class="video-list">
          <UiCard v-for="video in videos" :key="video.video_id" padding="md" class="video-row">
            <img v-if="video.thumbnail_url" :src="video.thumbnail_url" :alt="`Thumbnail ${video.title}`" />
            <div class="video-copy">
              <a :href="`https://youtu.be/${video.video_id}`" target="_blank" rel="noopener noreferrer"><strong>{{ video.title }}</strong></a>
              <span class="small muted">{{ dateLabel(video.published_at) }} · {{ video.privacy_status }}</span>
              <p>{{ video.description || 'Tanpa deskripsi.' }}</p>
            </div>
          </UiCard>
        </div>
        <div v-if="videos.length" class="pagination">
          <UiButton variant="ghost" :disabled="pageIndex === 0 || loading" @click="previousPage">Sebelumnya</UiButton>
          <span class="small muted">Halaman {{ pageIndex + 1 }}</span>
          <UiButton variant="ghost" :disabled="!nextToken || loading" @click="nextPage">Berikutnya</UiButton>
        </div>
      </section>
    </template>
  </template>
</template>

<style scoped>
.connection-card,.section-heading,.connection-copy,.button-row,.pagination { display:flex; align-items:center; justify-content:space-between; gap:14px; }
.connection-copy { align-items:flex-start; flex-direction:column; }
.upload-card,.content-section { margin-top:28px; }
.upload-card h2,.section-heading h2 { margin:0; }
.upload-layout { display:grid; grid-template-columns:minmax(280px,.9fr) minmax(0,1.1fr); gap:28px; align-items:start; margin-top:18px; }
.upload-form { display:grid; grid-template-columns:minmax(0,1fr); gap:16px; }
.upload-form :deep(.title-input) { max-width:360px; font-size:14px; }
.upload-submit { justify-self:start; }
.file-field { display:grid; gap:8px; font-size:14px; font-weight:500; }
.file-field small { font-weight:400; }
.video-preview { min-width:0; }
.preview-frame { display:grid; place-items:center; width:100%; aspect-ratio:16/9; overflow:hidden; border-radius:var(--radius-panel); background:var(--color-surface-subtle); }
.preview-frame video { width:100%; height:100%; object-fit:contain; background:#080808; }
.preview-empty { display:grid; gap:8px; text-align:center; }
.preview-copy { display:grid; gap:6px; margin-top:12px; }
.preview-copy p { margin:0; white-space:pre-wrap; overflow-wrap:anywhere; color:var(--color-text-muted); font-size:13px; }
.video-list { display:grid; gap:12px; }
.video-row { display:grid; grid-template-columns:200px minmax(0,1fr); gap:16px; }
.video-row img { width:100%; aspect-ratio:16/9; object-fit:cover; border-radius:var(--radius-control); }
.video-copy { display:grid; gap:7px; min-width:0; }
.video-copy a { color:var(--color-primary); }
.video-copy p { margin:0; white-space:pre-wrap; overflow-wrap:anywhere; font-size:14px; }
.pagination { justify-content:flex-end; margin-top:16px; }
.upload-success { color:var(--color-success); }
@media(max-width:760px) { .upload-layout,.video-row { grid-template-columns:minmax(0,1fr); } .connection-card { align-items:flex-start; flex-direction:column; } }
</style>
