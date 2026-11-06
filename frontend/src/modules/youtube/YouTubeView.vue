<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import { useRoute } from 'vue-router'
import { apiBase, errorMessage } from '../../shared/api'
import { useToast } from '../../shared/composables/useToast'
import UiBreadcrumbs from '../../shared/components/ui/UiBreadcrumbs.vue'
import UiButton from '../../shared/components/ui/UiButton.vue'
import UiCard from '../../shared/components/ui/UiCard.vue'
import UiConfirmDialog from '../../shared/components/ui/UiConfirmDialog.vue'
import UiModal from '../../shared/components/ui/UiModal.vue'
import UiErrorState from '../../shared/components/ui/UiErrorState.vue'
import UiInput from '../../shared/components/ui/UiInput.vue'
import UiSelect from '../../shared/components/ui/UiSelect.vue'
import UiSkeleton from '../../shared/components/ui/UiSkeleton.vue'
import UiTextarea from '../../shared/components/ui/UiTextarea.vue'
import { youtubeApi, type PrivacyStatus, type YouTubeStatus, type YouTubeVideo } from './api'

const route = useRoute()
const { notify } = useToast()
const status = ref<YouTubeStatus>()
const videos = ref<YouTubeVideo[]>([])
const truncated = ref(false)
const title = ref('')
const description = ref('')
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
const needsReconnect = (message: string): boolean => message.includes('menghubungkan ulang')
const connectionExpired = computed(() => needsReconnect(error.value))
const maxVideoBytes = 512 * 1024 * 1024

const privacyOptions = [
  { value: 'private', label: 'Private' },
  { value: 'unlisted', label: 'Unlisted' },
  { value: 'public', label: 'Public' },
]
const TICKET_PREFIXES = ['OGTSK', 'RATSK', 'AMTSK', 'TLTSK'] as const
const PAGE_SIZE = 10
const search = ref('')
const ticketFilter = ref('')
const privacyFilter = ref('')
const page = ref(1)

function videoText(video: YouTubeVideo): string {
  return `${video.title}\n${video.description}`
}
function hasTicket(video: YouTubeVideo, prefix: string): boolean {
  return new RegExp(`\\b${prefix}`, 'i').test(videoText(video))
}
const ticketOptions = computed(() => [
  { value: '', label: `Semua tiket (${videos.value.length})` },
  ...TICKET_PREFIXES.map((prefix) => ({
    value: prefix,
    label: `${prefix} (${videos.value.filter((video) => hasTicket(video, prefix)).length})`,
  })),
])
const filteredVideos = computed(() => {
  const terms = search.value.trim().toLowerCase().split(/\s+/).filter(Boolean)
  return videos.value.filter((video) => {
    if (ticketFilter.value && !hasTicket(video, ticketFilter.value)) return false
    if (privacyFilter.value && video.privacy_status !== privacyFilter.value) return false
    const text = videoText(video).toLowerCase()
    return terms.every((term) => text.includes(term))
  })
})
const hasFilters = computed(() => !!(search.value.trim() || ticketFilter.value || privacyFilter.value))
const totalPages = computed(() => Math.max(1, Math.ceil(filteredVideos.value.length / PAGE_SIZE)))
const pagedVideos = computed(() =>
  filteredVideos.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE),
)
const pageNumbers = computed<(number | '…')[]>(() => {
  const total = totalPages.value
  const current = page.value
  const pages = [...new Set([1, current - 1, current, current + 1, total])]
    .filter((value) => value >= 1 && value <= total)
    .sort((a, b) => a - b)
  return pages.flatMap((value, index) =>
    index && value - pages[index - 1]! > 1 ? (['…', value] as const) : [value],
  )
})
watch([search, ticketFilter, privacyFilter], () => {
  page.value = 1
})
watch(totalPages, (value) => {
  page.value = Math.min(page.value, value)
})
function resetFilters(): void {
  search.value = ''
  ticketFilter.value = ''
  privacyFilter.value = ''
}

const editTarget = ref<YouTubeVideo>()
const editOpen = ref(false)
const editTitle = ref('')
const editDescription = ref('')
const editPrivacy = ref<string>('private')
const saving = ref(false)
const editError = ref('')
const deleteTarget = ref<YouTubeVideo>()
const deleteOpen = ref(false)
const deleting = ref(false)
const deleteError = ref('')

function openEdit(video: YouTubeVideo): void {
  editTarget.value = video
  editTitle.value = video.title
  editDescription.value = video.description
  editPrivacy.value = ['private', 'unlisted', 'public'].includes(video.privacy_status)
    ? video.privacy_status
    : 'private'
  editError.value = ''
  editOpen.value = true
}

async function saveEdit(): Promise<void> {
  const target = editTarget.value
  if (!target || saving.value || !editTitle.value.trim()) return
  saving.value = true
  editError.value = ''
  try {
    const updated = await youtubeApi.update(target.video_id, {
      title: editTitle.value.trim(),
      description: editDescription.value,
      privacy_status: editPrivacy.value as PrivacyStatus,
    })
    videos.value = videos.value.map((video) =>
      video.video_id === updated.video_id
        ? { ...updated, thumbnail_url: updated.thumbnail_url ?? video.thumbnail_url }
        : video,
    )
    editOpen.value = false
    notify('Perubahan video disimpan.')
  } catch (cause) {
    editError.value = errorMessage(cause)
  } finally {
    saving.value = false
  }
}

function askDelete(video: YouTubeVideo): void {
  deleteTarget.value = video
  deleteError.value = ''
  deleteOpen.value = true
}

async function confirmDelete(): Promise<void> {
  const target = deleteTarget.value
  if (!target || deleting.value) return
  deleting.value = true
  deleteError.value = ''
  try {
    await youtubeApi.remove(target.video_id)
    videos.value = videos.value.filter((video) => video.video_id !== target.video_id)
    deleteOpen.value = false
    notify('Video dihapus dari channel.')
  } catch (cause) {
    deleteError.value = errorMessage(cause)
  } finally {
    deleting.value = false
  }
}

function connect(): void {
  window.location.assign(`${apiBase}/youtube/connect`)
}

async function loadVideos(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const result = await youtubeApi.videos()
    videos.value = result.videos
    truncated.value = result.truncated
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
    if (status.value.connected) await loadVideos()
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
  form.set('privacy_status', privacy.value)
  try {
    const result = await youtubeApi.upload(form)
    uploadedUrl.value = result.url
    notify('Video berhasil diunggah ke channel bersama.')
    title.value = ''
    description.value = ''
    file.value = undefined
    if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
    if (fileInput.value) fileInput.value.value = ''
    page.value = 1
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
            <UiSelect v-model="privacy" label="Privasi video" :options="privacyOptions" />
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
          <div><h2>Konten channel</h2><p>Video dari channel YouTube bersama.</p></div>
          <UiButton variant="secondary" :loading="loading" @click="loadVideos">Muat ulang</UiButton>
        </div>
        <form class="video-filters" role="search" @submit.prevent>
          <UiInput v-model="search" class="filter-search" label="Cari video" type="search" placeholder="Judul, deskripsi, atau kode tiket" />
          <UiSelect v-model="ticketFilter" label="Tiket" :options="ticketOptions" />
          <UiSelect v-model="privacyFilter" label="Privasi" :options="[{ value: '', label: 'Semua privasi' }, ...privacyOptions]" />
          <UiButton v-if="hasFilters" variant="ghost" @click="resetFilters">Reset filter</UiButton>
        </form>
        <p v-if="truncated" class="small muted">Hanya 1000 video terbaru yang dimuat.</p>
        <UiSkeleton v-if="loading" :lines="3" />
        <UiCard v-else-if="!error && !videos.length" padding="md"><p>Belum ada video di channel ini.</p></UiCard>
        <UiCard v-else-if="!error && !filteredVideos.length" padding="md">
          <p>Tidak ada video yang cocok dengan filter.</p>
        </UiCard>
        <template v-else>
          <p class="small muted result-count" aria-live="polite">
            Menampilkan {{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, filteredVideos.length) }}
            dari {{ filteredVideos.length }} video<template v-if="hasFilters"> (total {{ videos.length }})</template>
          </p>
          <div class="video-list">
            <UiCard v-for="video in pagedVideos" :key="video.video_id" padding="md" class="video-row">
              <img v-if="video.thumbnail_url" :src="video.thumbnail_url" :alt="`Thumbnail ${video.title}`" />
              <div class="video-copy">
                <a :href="`https://youtu.be/${video.video_id}`" target="_blank" rel="noopener noreferrer"><strong>{{ video.title }}</strong></a>
                <span class="small muted">{{ dateLabel(video.published_at) }} · {{ video.privacy_status }}</span>
                <p>{{ video.description || 'Tanpa deskripsi.' }}</p>
              </div>
              <div class="video-actions">
                <UiButton size="sm" variant="secondary" @click="openEdit(video)">Edit</UiButton>
                <UiButton size="sm" variant="danger" @click="askDelete(video)">Hapus</UiButton>
              </div>
            </UiCard>
          </div>
          <nav v-if="totalPages > 1" class="pagination" aria-label="Halaman video">
            <UiButton variant="ghost" size="sm" :disabled="page === 1" @click="page--">Sebelumnya</UiButton>
            <template v-for="(item, index) in pageNumbers" :key="`${item}-${index}`">
              <span v-if="item === '…'" class="small muted">…</span>
              <UiButton
                v-else
                size="sm"
                :variant="item === page ? 'primary' : 'ghost'"
                :aria-current="item === page ? 'page' : undefined"
                @click="page = item"
              >
                {{ item }}
              </UiButton>
            </template>
            <UiButton variant="ghost" size="sm" :disabled="page === totalPages" @click="page++">Berikutnya</UiButton>
          </nav>
        </template>
      </section>
      <UiModal v-model="editOpen" title="Edit video" size="lg" :dismissible="!saving">
        <form id="edit-video-form" class="upload-form" @submit.prevent="saveEdit">
          <UiInput v-model="editTitle" label="Judul video" required maxlength="100" />
          <UiTextarea v-model="editDescription" label="Deskripsi" :rows="6" maxlength="5000" />
          <UiSelect v-model="editPrivacy" label="Privasi video" :options="privacyOptions" />
          <p v-if="editError" class="file-error" role="alert">{{ editError }}</p>
          <UiButton v-if="needsReconnect(editError) && canConnect" variant="secondary" @click="connect">Hubungkan ulang channel</UiButton>
        </form>
        <template #footer>
          <UiButton variant="secondary" :disabled="saving" @click="editOpen = false">Batal</UiButton>
          <UiButton type="submit" form="edit-video-form" :loading="saving" :disabled="!editTitle.trim()">Simpan perubahan</UiButton>
        </template>
      </UiModal>
      <UiConfirmDialog
        v-model="deleteOpen"
        title="Hapus video?"
        :description="`Video “${deleteTarget?.title ?? ''}” akan dihapus permanen dari YouTube dan tidak dapat dikembalikan.`"
        confirm-label="Hapus video"
        :busy="deleting"
        :error="deleteError"
        @confirm="confirmDelete"
      />
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
.video-row { display:grid; grid-template-columns:200px minmax(0,1fr) auto; gap:16px; }
.video-actions { display:flex; flex-direction:column; gap:8px; align-items:stretch; }
.video-filters { display:grid; grid-template-columns:minmax(220px,2fr) minmax(160px,1fr) minmax(140px,1fr) auto; align-items:end; gap:12px; margin:16px 0; }
.result-count { margin:0 0 12px; }
.video-row img { width:100%; aspect-ratio:16/9; object-fit:cover; border-radius:var(--radius-control); }
.video-copy { display:grid; gap:7px; min-width:0; }
.video-copy a { color:var(--color-primary); }
.video-copy p { margin:0; white-space:pre-wrap; overflow-wrap:anywhere; font-size:14px; }
.pagination { justify-content:flex-end; flex-wrap:wrap; gap:6px; margin-top:16px; }
.upload-success { color:var(--color-success); }
@media(max-width:760px) { .upload-layout,.video-row,.video-filters { grid-template-columns:minmax(0,1fr); } .video-actions { flex-direction:row; } .connection-card { align-items:flex-start; flex-direction:column; } }
</style>
