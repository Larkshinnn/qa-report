<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import { PhArchive, PhDownloadSimple, PhUploadSimple } from '@phosphor-icons/vue'
import { backupApi, backupFilename, type ImportPreview } from '../api'
import { downloadFile, errorMessage } from '../../../shared/api'
import {
  defaultPalette,
  loadSavedPalettes,
  savedPalettesLimit,
  storeSavedPalettes,
  type SavedPalette,
} from '../../../shared/palettes'
import { useUiStore } from '../../../shared/stores/ui'
import { useToast } from '../../../shared/composables/useToast'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiModal from '../../../shared/components/ui/UiModal.vue'
import UiErrorState from '../../../shared/components/ui/UiErrorState.vue'

const emit = defineEmits<{ restored: [] }>()
const ui = useUiStore()
const { notify } = useToast()
const fileId = useId()
const busy = ref(false)
const dragging = ref(false)
const restoreMode = ref<'missing' | 'overwrite' | null>(null)
const error = ref('')
const confirmOpen = ref(false)
const pending = ref<File | null>(null)
const preview = ref<ImportPreview | null>(null)

const description = computed(() => {
  if (!pending.value || !preview.value) return ''
  return `${pending.value.name} siap diimport. Bandingkan isi ZIP dengan data saat ini sebelum melanjutkan.`
})
const comparisonRows = computed(() => {
  if (!preview.value) return []
  return [
    {
      label: 'Laporan',
      current: preview.value.existing_reports,
      archive: preview.value.reports,
      added: preview.value.new_reports,
    },
    {
      label: 'Template',
      current: preview.value.existing_templates,
      archive: preview.value.templates,
      added: preview.value.new_templates,
    },
    {
      label: 'Item Vault',
      current: preview.value.existing_vault_entries,
      archive: preview.value.vault_entries,
      added: preview.value.new_vault_entries,
    },
  ]
})

async function download(): Promise<void> {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    const archive = await backupApi.download({
      theme: ui.theme,
      color_palette: ui.colorPalette,
      saved_palettes: loadSavedPalettes(),
    })
    downloadFile(archive, backupFilename())
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}

async function inspect(file?: File): Promise<void> {
  pending.value = null
  preview.value = null
  error.value = ''
  if (!file || busy.value) return
  busy.value = true
  try {
    if (!file.name.toLowerCase().endsWith('.zip')) throw new Error('Pilih file backup ZIP.')
    if (file.size > 100 * 1024 * 1024) throw new Error('File backup ZIP maksimal 100 MB.')
    preview.value = await backupApi.preview(file)
    pending.value = file
    confirmOpen.value = true
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}

function choose(event: Event): void {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  void inspect(file)
}

function drop(event: DragEvent): void {
  dragging.value = false
  void inspect(event.dataTransfer?.files[0])
}

function mergePalettes(imported: SavedPalette[]): void {
  const current = loadSavedPalettes()
  const ids = new Set(current.map((palette) => palette.id))
  const names = new Set(current.map((palette) => palette.name.toLocaleLowerCase('id-ID')))
  for (const palette of imported) {
    const name = palette.name.toLocaleLowerCase('id-ID')
    if (!ids.has(palette.id) && !names.has(name)) {
      current.push(palette)
      ids.add(palette.id)
      names.add(name)
    }
  }
  storeSavedPalettes(current.slice(0, savedPalettesLimit))
}

async function restore(mode: 'missing' | 'overwrite'): Promise<void> {
  if (!pending.value || busy.value) return
  busy.value = true
  restoreMode.value = mode
  error.value = ''
  try {
    const result = await backupApi.restore(pending.value, mode)
    if (mode === 'overwrite') {
      ui.setTheme(result.theme.theme)
      ui.setColorPalette(result.theme.color_palette ?? defaultPalette)
      storeSavedPalettes(result.theme.saved_palettes)
    } else {
      mergePalettes(result.theme.saved_palettes)
    }
    confirmOpen.value = false
    pending.value = null
    notify(
      `${result.reports_restored} laporan dan ${result.vault_restored} item Vault diimport; ${result.reports_skipped + result.vault_skipped} data yang sudah ada dilewati.`,
    )
    emit('restored')
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
    restoreMode.value = null
  }
}
</script>

<template>
  <section
    class="backup-tools"
    aria-labelledby="backup-title"
  >
    <div class="backup-heading">
      <div>
        <h2 id="backup-title">Backup &amp; import</h2>
        <p class="small muted">
          Simpan atau pulihkan laporan, template, tema/palet, dan Vault dalam satu file ZIP.
        </p>
      </div>
      <span class="format-badge">ZIP · maks. 100 MB</span>
    </div>
    <div class="backup-actions">
      <article class="backup-card">
        <div class="action-heading">
          <span
            class="action-icon"
            aria-hidden="true"
          >
            <PhArchive :size="28" />
          </span>
          <h3>Backup data</h3>
        </div>
        <UiButton
          variant="secondary"
          :loading="busy"
          @click="download"
        >
          <template #start><PhDownloadSimple :size="18" /></template>
          Unduh backup ZIP
        </UiButton>
      </article>
      <article class="backup-card import-card">
        <div class="action-heading">
          <span
            class="action-icon"
            aria-hidden="true"
          >
            <PhUploadSimple :size="28" />
          </span>
          <h3>Import backup</h3>
        </div>
        <label
          :for="fileId"
          class="import-picker"
          :class="{
            'import-picker-disabled': busy,
            'import-picker-dragging': dragging && !busy,
          }"
          @dragenter.prevent="dragging = true"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="drop"
        >
          <input
            :id="fileId"
            class="file-input"
            type="file"
            accept=".zip,application/zip"
            :disabled="busy"
            @change="choose"
          />
          <PhUploadSimple
            :size="18"
            aria-hidden="true"
          />
          <span class="import-label">
            <strong>Drag &amp; drop file ZIP</strong>
            <small>atau klik untuk memilih file</small>
          </span>
        </label>
      </article>
    </div>
    <p class="security-note small muted">
      ZIP tidak diberi password. Rahasia Vault tetap berupa ciphertext; simpan file di tempat aman.
    </p>
    <UiErrorState
      v-if="error && !confirmOpen"
      :message="error"
    />
  </section>
  <UiModal
    v-model="confirmOpen"
    title="Import backup ZIP?"
    :description="description"
    :dismissible="!busy"
    size="lg"
  >
    <section
      v-if="preview"
      class="comparison"
      aria-labelledby="comparison-title"
    >
      <h3 id="comparison-title">Perbandingan data</h3>
      <div class="comparison-table-wrap">
        <table class="comparison-table">
          <thead>
            <tr>
              <th scope="col">Jenis data</th>
              <th scope="col">Saat ini</th>
              <th scope="col">Isi ZIP</th>
              <th scope="col">Data baru</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in comparisonRows"
              :key="row.label"
            >
              <th scope="row">{{ row.label }}</th>
              <td>{{ row.current }}</td>
              <td>{{ row.archive }}</td>
              <td>
                <span
                  class="new-count"
                  :class="{ 'new-count-empty': row.added === 0 }"
                >
                  +{{ row.added }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="comparison-hint">
        Tambahkan hanya memasukkan kolom Data baru. Overwrite mengganti data saat ini dengan kolom
        Isi ZIP.
      </p>
    </section>
    <div class="import-options">
      <p class="mode-option">
        <strong>Tambahkan yang belum ada</strong>
        mempertahankan data sekarang dan melewati laporan bertanggal sama, template bernama sama,
        serta item Vault dengan ID sama.
      </p>
      <p class="mode-option">
        <strong>Overwrite semua</strong>
        mengganti seluruh laporan, template, tema/palet, dan Vault dengan isi ZIP. Tindakan ini
        tidak dapat dibatalkan.
      </p>
      <p
        v-if="preview && !preview.vault_mergeable"
        class="warning"
      >
        Master lock Vault berbeda, sehingga Vault tidak dapat digabung. Gunakan overwrite jika kamu
        memang ingin mengganti Vault saat ini.
      </p>
    </div>
    <UiErrorState
      v-if="error"
      :message="error"
    />
    <template #footer>
      <UiButton
        variant="secondary"
        :disabled="busy"
        @click="confirmOpen = false"
      >
        Batal
      </UiButton>
      <UiButton
        variant="secondary"
        :loading="restoreMode === 'missing'"
        :disabled="preview ? !preview.vault_mergeable : true"
        @click="restore('missing')"
      >
        Tambahkan yang belum ada
      </UiButton>
      <UiButton
        variant="danger-solid"
        :loading="restoreMode === 'overwrite'"
        @click="restore('overwrite')"
      >
        Overwrite semua
      </UiButton>
    </template>
  </UiModal>
</template>

<style scoped>
.backup-tools {
  border-top: 1px solid var(--color-border);
  margin-top: 32px;
  padding-top: 30px;
}
.backup-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}
.backup-heading p {
  margin-top: 6px;
}
.format-badge {
  flex: 0 0 auto;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 5px 9px;
  background: var(--color-surface-subtle);
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
}
.backup-actions {
  display: grid;
  grid-template-columns: minmax(0, 0.82fr) minmax(0, 1.18fr);
  gap: 16px;
  margin-top: 20px;
}
.backup-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 22px;
  min-width: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-panel);
  padding: 20px;
  background: var(--color-surface);
}
.action-heading {
  display: flex;
  align-items: center;
  gap: 14px;
}
.action-heading h3 {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.02em;
}
.action-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: var(--radius-control);
  background: var(--color-surface-accent);
  color: var(--color-primary);
}
.import-picker {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  min-height: 108px;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface-subtle);
  color: var(--color-primary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition:
    background-color var(--duration-fast),
    border-color var(--duration-fast);
}
.import-picker:hover,
.import-picker:focus-within,
.import-picker-dragging {
  border-color: var(--color-primary);
  background: var(--color-surface-accent);
}
.import-label {
  display: grid;
  gap: 2px;
  text-align: left;
}
.import-label strong {
  font-size: 14px;
}
.import-label small {
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 400;
}
.import-picker-disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.file-input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}
.file-input:disabled {
  cursor: not-allowed;
}
.security-note {
  margin-top: 14px;
}
.comparison h3 {
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
}
.comparison-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
}
.comparison-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}
.comparison-table th,
.comparison-table td {
  padding: 11px 14px;
  border-bottom: 1px solid var(--color-border);
  text-align: right;
  white-space: nowrap;
}
.comparison-table th:first-child {
  text-align: left;
}
.comparison-table thead th {
  background: var(--color-surface-subtle);
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 600;
}
.comparison-table tbody th {
  font-weight: 500;
}
.comparison-table tbody tr:last-child > * {
  border-bottom: 0;
}
.new-count {
  color: var(--color-success);
  font-weight: 600;
}
.new-count-empty {
  color: var(--color-text-muted);
  font-weight: 400;
}
.comparison-hint {
  margin-top: 10px;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.5;
}
.import-options {
  display: grid;
  gap: 12px;
  margin-top: 20px;
}
.mode-option {
  border-left: 3px solid var(--color-border-strong);
  padding-left: 12px;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.55;
}
.mode-option strong {
  display: block;
  margin-bottom: 2px;
  color: var(--color-text);
}
.warning {
  color: var(--color-danger);
}
@media (max-width: 680px) {
  .backup-heading {
    display: grid;
  }
  .format-badge {
    justify-self: start;
  }
  .backup-actions {
    grid-template-columns: 1fr;
  }
}
</style>
