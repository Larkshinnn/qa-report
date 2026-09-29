<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage } from '../../../shared/api'
import { useToast } from '../../../shared/composables/useToast'
import UiBreadcrumbs from '../../../shared/components/ui/UiBreadcrumbs.vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiCard from '../../../shared/components/ui/UiCard.vue'
import UiErrorState from '../../../shared/components/ui/UiErrorState.vue'
import { qaApi, type ZipImportPreview } from '../api'

const router = useRouter()
const { notify } = useToast()
const inputId = useId()
const filePicker = ref<HTMLInputElement>()
const file = ref<File>()
const preview = ref<ZipImportPreview>()
const busy = ref(false)
const dragging = ref(false)
const error = ref('')
const reports = computed(() => preview.value?.reports ?? [])

async function inspect(candidate?: File): Promise<void> {
  file.value = undefined
  preview.value = undefined
  error.value = ''
  if (!candidate) return
  if (!candidate.name.toLowerCase().endsWith('.zip')) {
    error.value = 'Pilih file backup dengan format .zip.'
    return
  }
  if (candidate.size > 100 * 1024 * 1024) {
    error.value = 'Ukuran ZIP maksimal 100 MB.'
    return
  }
  busy.value = true
  try {
    preview.value = await qaApi.previewZip(candidate)
    file.value = candidate
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}

function choose(event: Event): void {
  const input = event.target as HTMLInputElement
  const candidate = input.files?.[0]
  input.value = ''
  void inspect(candidate)
}

function drop(event: DragEvent): void {
  dragging.value = false
  void inspect(event.dataTransfer?.files[0])
}

function activatePicker(event: KeyboardEvent): void {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    filePicker.value?.click()
  }
}

async function restore(mode: 'missing' | 'overwrite'): Promise<void> {
  if (!file.value || busy.value) return
  const prompt = mode === 'overwrite'
    ? `Ganti ${preview.value?.existing_reports ?? 0} laporan yang tanggalnya sudah ada, lalu tambahkan laporan baru? Laporan pada tanggal lain tidak berubah.`
    : `Tambahkan ${preview.value?.new_reports ?? 0} laporan baru dan lewati tanggal yang sudah ada?`
  if (!window.confirm(prompt)) return
  busy.value = true
  error.value = ''
  try {
    const result = await qaApi.importZip(file.value, mode)
    notify(`${result.added} laporan ditambahkan, ${result.overwritten} ditimpa, ${result.skipped} dilewati.`)
    await router.push('/qa-reports')
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat('id-ID', { dateStyle: 'medium' }).format(new Date(`${value}T12:00:00`))
}
</script>

<template>
  <UiBreadcrumbs :items="[{ label: 'Laporan', to: '/qa-reports' }, { label: 'Import backup' }]" />
  <div class="page-header">
    <div>
      <h1>Import backup ZIP</h1>
      <p>Pilih arsip berisi folder bulan, dengan satu file JSON untuk setiap tanggal laporan.</p>
    </div>
    <UiButton variant="ghost" @click="router.push('/qa-reports')">Kembali ke laporan</UiButton>
  </div>

  <label
    class="drop-zone"
    :class="{ 'drop-zone-active': dragging, 'drop-zone-disabled': busy }"
    :for="inputId"
    role="button"
    tabindex="0"
    @dragenter.prevent="dragging = true"
    @dragover.prevent="dragging = true"
    @dragleave.prevent="dragging = false"
    @drop.prevent="drop"
    @keydown="activatePicker"
  >
    <input :id="inputId" ref="filePicker" class="visually-hidden" type="file" accept=".zip,application/zip" :disabled="busy" @change="choose" />
    <strong>{{ busy ? 'Memeriksa isi ZIP…' : 'Taruh file ZIP di sini' }}</strong>
    <span class="muted">atau klik untuk memilih file · maksimal 100 MB</span>
    <span v-if="file" class="selected-file">{{ file.name }}</span>
  </label>

  <UiErrorState v-if="error" :message="error" />

  <section v-if="preview" class="preview-section" aria-labelledby="preview-heading">
    <div class="preview-heading">
      <div>
        <h2 id="preview-heading">Preview isi backup</h2>
        <p class="small muted">{{ preview.total_reports }} laporan · {{ preview.months.length }} bulan · {{ preview.new_reports }} baru · {{ preview.existing_reports }} tanggal sudah ada</p>
      </div>
      <div class="import-actions">
        <UiButton variant="secondary" :loading="busy" @click="restore('missing')">Tambah yang belum ada</UiButton>
        <UiButton variant="danger-solid" :loading="busy" @click="restore('overwrite')">Overwrite tanggal sama</UiButton>
      </div>
    </div>
    <p class="small muted">Overwrite mengganti laporan pada tanggal yang sama dan menambahkan tanggal baru. Tanggal lain tetap utuh.</p>
    <div class="month-list">
      <UiCard v-for="month in preview.months" :key="month.month" padding="md" class="month-card">
        <strong>{{ month.month }}</strong><span class="small muted">{{ month.count }} laporan</span>
      </UiCard>
    </div>
    <div class="report-preview" aria-label="Preview daftar laporan dalam ZIP">
      <p v-if="!reports.length" class="empty-preview">ZIP ini belum berisi laporan.</p>
      <div v-for="report in reports" :key="report.report_date" class="report-row">
        <div>
          <strong>{{ dateLabel(report.report_date) }}</strong>
          <span>{{ report.title }}</span>
        </div>
        <span class="small muted">{{ report.activity_count }} aktivitas · {{ report.total_hours.toFixed(1) }} jam</span>
        <span class="small" :class="report.already_exists ? 'existing-tag' : 'new-tag'">
          {{ report.already_exists ? 'Tanggal sudah ada' : 'Baru' }}
        </span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.drop-zone { min-height: 220px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; padding: 28px; border: 1px dashed var(--color-border-strong); border-radius: var(--radius-panel); background: var(--color-surface-subtle); cursor: pointer; text-align: center; transition: border-color var(--duration-fast), background-color var(--duration-fast); }
.drop-zone:hover,.drop-zone:focus-visible,.drop-zone-active { border-color: var(--color-primary); background: var(--color-surface-accent); outline: none; }
.drop-zone-disabled { opacity: .7; pointer-events: none; }
.drop-zone strong { font-size: 18px; }
.selected-file { color: var(--color-primary); font-weight: 600; overflow-wrap: anywhere; }
.visually-hidden { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
.preview-section { margin-top: 30px; }
.preview-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 18px; }
.preview-heading h2 { margin: 0 0 5px; }
.preview-heading p { margin: 0; }
.import-actions { display: flex; flex-wrap: wrap; gap: 10px; }
.month-list { display: flex; flex-wrap: wrap; gap: 10px; margin: 18px 0; }
.month-card { display: flex; align-items: center; gap: 10px; }
.report-preview { max-height: 460px; overflow: auto; border-top: 1px solid var(--color-border); border-bottom: 1px solid var(--color-border); }
.report-row { display: grid; grid-template-columns: minmax(0,1fr) auto auto; align-items: center; gap: 18px; padding: 12px 4px; border-bottom: 1px solid var(--color-border); }
.report-row:last-child { border-bottom: 0; }
.empty-preview { padding: 18px 4px; color: var(--color-text-muted); }
.report-row > div { display: grid; gap: 3px; }
.existing-tag { color: var(--color-danger); }
.new-tag { color: var(--color-success); }
@media (max-width: 720px) { .preview-heading { flex-direction: column; } .report-row { grid-template-columns: minmax(0,1fr) auto; gap: 8px; } .report-row > :last-child { grid-column: 1 / -1; } }
</style>
