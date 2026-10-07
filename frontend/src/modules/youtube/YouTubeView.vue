<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useId } from 'vue'
import { useRoute } from 'vue-router'
import { apiBase, errorMessage } from '../../shared/api'
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
const fileInputId = useId()
const previewUrl = ref('')
const uploadedUrl = ref('')
const loading = ref(false)
const uploading = ref(false)
const dragging = ref(false)
const dragDepth = ref(0)
const error = ref('')
const fileError = ref('')
const connected = computed(() => status.value?.connected ?? false)
const canConnect = computed(() => status.value?.can_connect ?? false)
const connectionExpired = computed(() =>
  error.value.startsWith('Koneksi YouTube kedaluwarsa.'),
)
const maxVideoBytes = 512 * 1024 * 1024

function connect(): void {
  window.location.assign(`${apiBase}/youtube/connect`)
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

function clearFile(): void {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  file.value = undefined
  previewUrl.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

function chooseFile(candidate?: File): void {
  if (!candidate || uploading.value) return
  fileError.value = ''
  if (!candidate.type.startsWith('video/')) {
    clearFile()
    fileError.value = 'Pilih file video dengan tipe MIME video.'
    return
  }
  if (!candidate.size || candidate.size > maxVideoBytes) {
    clearFile()
    fileError.value = 'Ukuran video harus antara 1 byte dan 512 MB.'
    return
  }
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  file.value = candidate
  previewUrl.value = URL.createObjectURL(candidate)
}

function selectFile(event: Event): void {
  const input = event.target as HTMLInputElement
  const candidate = input.files?.[0]
  input.value = ''
  chooseFile(candidate)
}

function activateFilePicker(event: KeyboardEvent): void {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    fileInput.value?.click()
  }
}

function dragEnter(event: DragEvent): void {
  event.preventDefault()
  if (uploading.value) return
  dragDepth.value += 1
  dragging.value = true
}

function dragLeave(event: DragEvent): void {
  event.preventDefault()
  dragDepth.value = Math.max(0, dragDepth.value - 1)
  if (!dragDepth.value) dragging.value = false
}

function dragOver(event: DragEvent): void {
  event.preventDefault()
  if (event.dataTransfer) event.dataTransfer.dropEffect = uploading.value ? 'none' : 'copy'
}

function dropFile(event: DragEvent): void {
  event.preventDefault()
  dragDepth.value = 0
  dragging.value = false
  chooseFile(event.dataTransfer?.files[0])
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
  <div v-if="error" class="youtube-error">
    <UiErrorState :message="error" retryable @retry="load" />
    <UiButton v-if="connectionExpired && canConnect" @click="connect">Hubungkan ulang channel</UiButton>
  </div>
  <UiSkeleton v-else-if="!status || loading" :lines="4" />
  <template v-if="status && (error || !loading)">
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
        <UiButton v-if="connected && canConnect" @click="connect">Hubungkan ulang</UiButton>
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
            <label
              :id="fileInputId + '-dropzone'"
              class="file-drop-zone"
              :class="{ 'file-drop-active': dragging, 'file-drop-disabled': uploading }"
              :for="fileInputId"
              role="button"
              tabindex="0"
              aria-label="Pilih atau jatuhkan file video, maksimal 512 megabyte"
              @dragenter="dragEnter"
              @dragover="dragOver"
              @dragleave="dragLeave"
              @drop="dropFile"
              @keydown="activateFilePicker"
            >
              <input
                :id="fileInputId"
                ref="fileInput"
                class="visually-hidden"
                type="file"
                accept="video/*"
                :disabled="uploading"
                @change="selectFile"
              />
              <strong>{{ dragging ? 'Lepaskan video untuk memilih file' : file?.name || 'Tarik dan lepas video di sini' }}</strong>
              <span v-if="file" class="small muted">{{ (file.size / 1048576).toFixed(1) }} MB · klik untuk mengganti</span>
              <span v-else class="small muted">atau klik untuk memilih · maksimal 512 MB</span>
            </label>
            <p v-if="fileError" class="file-error" role="alert">{{ fileError }}</p>
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
        <UiCard v-else-if="!error && !videos.length" padding="md"><p>Belum ada video di channel ini.</p></UiCard>
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
.youtube-error { display:flex; align-items:center; flex-wrap:wrap; gap:12px; }
.connection-card,.section-heading,.connection-copy,.button-row,.pagination { display:flex; align-items:center; justify-content:space-between; gap:14px; }
.connection-copy { align-items:flex-start; flex-direction:column; }
.upload-card,.content-section { margin-top:28px; }
.upload-card h2,.section-heading h2 { margin:0; }
.upload-layout { display:grid; grid-template-columns:minmax(280px,.9fr) minmax(0,1.1fr); gap:28px; align-items:start; margin-top:18px; }
.upload-form { display:grid; grid-template-columns:minmax(0,1fr); gap:16px; }
.upload-form :deep(.title-input) { max-width:360px; font-size:14px; }
.upload-submit { justify-self:start; }
.file-drop-zone { display:grid; place-content:center; gap:8px; min-height:136px; padding:20px; border:1px dashed var(--color-border-strong); border-radius:var(--radius-panel); background:var(--color-surface-subtle); color:var(--color-text); text-align:center; cursor:pointer; transition:background-color var(--duration-fast) var(--ease-out),border-color var(--duration-fast) var(--ease-out); }
.file-drop-zone strong { color:var(--color-primary); overflow-wrap:anywhere; }
.file-drop-zone:hover,.file-drop-active { border-color:var(--color-primary); background:var(--color-surface-accent); }
.file-drop-zone:focus-visible { outline:2px solid var(--color-focus); outline-offset:3px; }
.file-drop-disabled { opacity:.6; cursor:progress; }
.file-error { color:var(--color-danger); font-size:13px; }
.visually-hidden { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0; }
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
