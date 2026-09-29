<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '../../../shared/composables/useToast'
import DeleteReportButton from '../components/DeleteReportButton.vue'
import { downloadFile, errorMessage } from '../../../shared/api'
import { qaApi, statusLabel, type ReportPage, type ReportSummary } from '../api'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiBreadcrumbs from '../../../shared/components/ui/UiBreadcrumbs.vue'
import UiCard from '../../../shared/components/ui/UiCard.vue'
import UiInput from '../../../shared/components/ui/UiInput.vue'
import UiBadge from '../../../shared/components/ui/UiBadge.vue'
import UiDataTable from '../../../shared/components/ui/UiDataTable.vue'
import UiErrorState from '../../../shared/components/ui/UiErrorState.vue'
import '../styles.css'
const router = useRouter()
const { notify } = useToast()
const filters = reactive({ search: '', start: '', end: '', environment: '', result: '' })
const applied = ref<Record<string, string>>({})
const data = ref<ReportPage>({ reports: [], total: 0, page: 1, page_size: 20 })
const loading = ref(false)
const error = ref('')
const page = ref(1)
const backupBusy = ref(false)
const backupError = ref('')
const importFile = ref<HTMLInputElement>()
const pages = computed(() => Math.max(1, Math.ceil(data.value.total / 20)))
const columns: { key: keyof ReportSummary; label: string }[] = [
  { key: 'report_date', label: 'Tanggal' },
  { key: 'title', label: 'Laporan' },
  { key: 'item_count', label: 'Aktivitas' },
  { key: 'status', label: 'Status' },
  { key: 'id', label: 'Aksi' },
]
let request = 0
async function load(): Promise<void> {
  const current = ++request
  loading.value = true
  error.value = ''
  try {
    const result = await qaApi.list({ ...applied.value, page: String(page.value), order: 'desc' })
    if (current === request) {
      data.value = result
      if (page.value > pages.value) {
        page.value = pages.value
        await load()
      }
    }
  } catch (cause) {
    if (current === request) error.value = errorMessage(cause)
  } finally {
    if (current === request) loading.value = false
  }
}
function apply(): void {
  applied.value = Object.fromEntries(
    Object.entries(filters)
      .filter(([, value]) => value.trim())
      .map(([key, value]) => [key, value.trim()]),
  )
  page.value = 1
  void load()
}
function reset(): void {
  Object.assign(filters, { search: '', start: '', end: '', environment: '', result: '' })
  apply()
}
function changePage(change: number): void {
  page.value += change
  void load()
}
function deleted(): void {
  notify('Laporan dihapus permanen.')
  void load()
}
async function downloadBackup(): Promise<void> {
  backupBusy.value = true
  backupError.value = ''
  try {
    downloadFile(await qaApi.backup(), `qa-reports-backup-${new Date().toISOString().slice(0, 10)}.json`)
    notify('Backup QA Report berhasil diunduh.')
  } catch (cause) {
    backupError.value = errorMessage(cause)
  } finally {
    backupBusy.value = false
  }
}
async function importBackup(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (file.size > 10 * 1024 * 1024) {
    backupError.value = 'File backup maksimal 10 MB.'
    return
  }
  if (!window.confirm(`Import backup "${file.name}"? Laporan dan template yang sudah ada akan dilewati.`)) return
  backupBusy.value = true
  backupError.value = ''
  try {
    const result = await qaApi.restore(await file.text())
    notify(`${result.restored} laporan dipulihkan; ${result.skipped} data yang sudah ada dilewati.`)
    await load()
  } catch (cause) {
    backupError.value = errorMessage(cause)
  } finally {
    backupBusy.value = false
  }
}
onMounted(load)
</script>
<template>
  <UiBreadcrumbs :items="[{ label: 'Laporan' }]" />
  <div class="page-header">
    <div>
      <h1>QA Reports</h1>
      <p>Daftar berdasarkan tanggal laporan, dari terbaru ke terlama.</p>
    </div>
    <div class="qa-actions">
      <UiButton variant="secondary" :loading="backupBusy" @click="downloadBackup">Unduh backup</UiButton>
      <UiButton variant="secondary" :loading="backupBusy" @click="importFile?.click()">Import backup</UiButton>
      <input ref="importFile" class="visually-hidden" type="file" accept="application/json,.json" @change="importBackup" />
      <UiButton @click="router.push('/qa-reports/new')">Tambah laporan</UiButton>
    </div>
  </div>
  <UiErrorState v-if="backupError" :message="backupError" />
  <nav
    class="qa-nav"
    aria-label="Navigasi laporan"
  >
    <RouterLink to="/qa-reports">Daftar laporan</RouterLink>
    <RouterLink to="/qa-reports/monthly">Ringkasan bulanan</RouterLink>
    <RouterLink to="/qa-reports/templates">Template laporan</RouterLink>
  </nav>
  <div class="stack">
    <details>
      <summary class="qa-filter-toggle">Filter laporan</summary>
      <UiCard
        padding="md"
        tone="subtle"
      >
        <form
          class="stack"
          @submit.prevent="apply"
        >
          <div class="qa-filters">
            <UiInput
              v-model="filters.search"
              label="Cari kode tiket"
              placeholder="Contoh: QA-142"
              maxlength="100"
            />
            <UiInput
              v-model="filters.start"
              label="Dari tanggal"
              type="date"
              :max="filters.end || '2100-12-31'"
              min="1900-01-01"
            />
            <UiInput
              v-model="filters.end"
              label="Sampai tanggal"
              type="date"
              :min="filters.start || '1900-01-01'"
              max="2100-12-31"
            />
            <UiInput
              v-model="filters.environment"
              label="Environment"
              placeholder="Semua environment"
              list="history-environments"
            />
            <UiInput
              v-model="filters.result"
              label="Hasil"
              placeholder="Semua hasil"
              list="history-results"
            />
            <div class="qa-actions">
              <UiButton
                type="submit"
                variant="secondary"
                :loading="loading"
              >
                Cari laporan
              </UiButton>
              <UiButton
                variant="ghost"
                :disabled="loading"
                @click="reset"
              >
                Reset
              </UiButton>
            </div>
          </div>
        </form>
      </UiCard>
    </details>
    <datalist id="history-environments">
      <option>Dev</option>
      <option>Staging</option>
      <option>Prod</option>
    </datalist>
    <datalist id="history-results">
      <option>Pass</option>
      <option>Fail</option>
      <option>In progress</option>
      <option>Blocked</option>
    </datalist>
    <section aria-label="Daftar laporan">
      <UiDataTable
        :rows="data.reports"
        :columns="columns"
        row-key="id"
        caption="Riwayat laporan QA"
        :paginate="false"
        :loading="loading"
        :error="error"
        @retry="load"
      >
        <template #cell-title="{ row }">
          <RouterLink
            :to="`/qa-reports/${row.id}`"
            class="qa-link"
          >
            {{ row.title }}
          </RouterLink>
        </template>
        <template #cell-status="{ row }">
          <UiBadge
            :tone="
              row.status === 'sent' ? 'success' : row.status === 'finalized' ? 'info' : 'neutral'
            "
          >
            {{ statusLabel(row.status) }}
          </UiBadge>
        </template>
        <template #cell-id="{ row }">
          <DeleteReportButton
            :report-id="row.id"
            :report-title="row.title"
            @deleted="deleted"
          />
        </template>
      </UiDataTable>
      <div
        v-if="!loading && !error && data.total"
        class="qa-pagination"
      >
        <span>{{ data.total }} laporan · terbaru di atas</span>
        <div class="qa-actions">
          <UiButton
            variant="ghost"
            :disabled="page === 1"
            @click="changePage(-1)"
          >
            Sebelumnya
          </UiButton>
          <span aria-live="polite">{{ page }} / {{ pages }}</span>
          <UiButton
            variant="ghost"
            :disabled="page >= pages"
            @click="changePage(1)"
          >
            Berikutnya
          </UiButton>
        </div>
      </div>
    </section>
  </div>
</template>
<style scoped>
.visually-hidden { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
</style>
