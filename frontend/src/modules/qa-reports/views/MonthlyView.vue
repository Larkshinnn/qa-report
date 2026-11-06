<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { qaApi, localDate, safeCoverageUrl, type CsvPreviewRow, type Metrics } from '../api'
import { downloadFile, errorMessage } from '../../../shared/api'
import { useToast } from '../../../shared/composables/useToast'
import UiModal from '../../../shared/components/ui/UiModal.vue'
import UiTextarea from '../../../shared/components/ui/UiTextarea.vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiBreadcrumbs from '../../../shared/components/ui/UiBreadcrumbs.vue'
import UiInput from '../../../shared/components/ui/UiInput.vue'
import UiCard from '../../../shared/components/ui/UiCard.vue'
import UiSkeleton from '../../../shared/components/ui/UiSkeleton.vue'
import UiErrorState from '../../../shared/components/ui/UiErrorState.vue'
import UiEmptyState from '../../../shared/components/ui/UiEmptyState.vue'
import UiDataTable from '../../../shared/components/ui/UiDataTable.vue'
import '../styles.css'
const month = ref(localDate().slice(0, 7))
const data = ref<Metrics>()
const csvRows = ref<CsvPreviewRow[]>([])
const error = ref('')
const exportError = ref('')
const loading = ref(false)
const exporting = ref(false)
const exportingManmonth = ref(false)
const peak = computed(() => Math.max(1, ...(data.value?.trend.map((day) => day.count) ?? [])))
type ManmonthPreviewRow = CsvPreviewRow & { number: number; day: string; actions: string }
const manmonthRows = computed<ManmonthPreviewRow[]>(() =>
  csvRows.value.map((row, index) => ({
    ...row,
    actions: '',
    number: index + 1,
    date: new Intl.DateTimeFormat('id-ID', {
      weekday: 'long',
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    }).format(new Date(`${row.date}T12:00:00`)),
    day: new Intl.DateTimeFormat('id-ID', { weekday: 'long' }).format(
      new Date(`${row.date}T12:00:00`),
    ),
  })),
)
const manmonthColumns: { key: keyof ManmonthPreviewRow & string; label: string }[] = [
  { key: 'number', label: 'No' },
  { key: 'date', label: 'Tanggal' },
  { key: 'day', label: 'Hari' },
  { key: 'duration_hours', label: 'Durasi Pengerjaan (Hour)' },
  { key: 'activity', label: 'Ticket / Task Ref' },
  { key: 'current_issue', label: 'Task Summary (Progress)' },
  { key: 'obstacle', label: 'Kendala (Obstacle)' },
  { key: 'next_step', label: 'Next Step / Action' },
  { key: 'pic_guidance', label: 'PIC / Guidance' },
  { key: 'coverage_links', label: 'Notion / Reference Link' },
  { key: 'deliverable', label: 'Deliverable' },
  { key: 'current_status', label: 'Status' },
  { key: 'actions', label: 'Aksi' },
]
type LongColumn =
  | 'activity'
  | 'current_issue'
  | 'obstacle'
  | 'next_step'
  | 'pic_guidance'
  | 'coverage_links'
  | 'deliverable'
  | 'current_status'
const longColumnKeys: LongColumn[] = [
  'activity',
  'current_issue',
  'obstacle',
  'next_step',
  'pic_guidance',
  'coverage_links',
  'deliverable',
  'current_status',
]
const longColumns = manmonthColumns.filter((column): column is { key: LongColumn; label: string } =>
  (longColumnKeys as string[]).includes(column.key),
)
const LONG_CHARS = 120
const LONG_LINES = 3
function isLong(value: unknown): boolean {
  const text = String(value ?? '')
  return text.length > LONG_CHARS || text.split('\n').length > LONG_LINES
}

const { notify } = useToast()
const detail = ref<{ label: string; date: string; key: string; value: string }>()
const detailOpen = ref(false)
function showDetail(label: string, key: string, row: ManmonthPreviewRow): void {
  detail.value = { label, key, date: row.date, value: String(row[key as LongColumn] ?? '') }
  detailOpen.value = true
}

const editRow = ref<CsvPreviewRow>()
const editOpen = ref(false)
const saving = ref(false)
const editError = ref('')
const editForm = reactive({
  activity_code: '',
  duration_hours: '',
  current_issue: '',
  obstacle: '',
  next_step: '',
  pic_guidance: '',
  links: '',
  deliverable: '',
  current_status: '',
})
const editDateLabel = computed(() =>
  editRow.value
    ? new Intl.DateTimeFormat('id-ID', { dateStyle: 'full' }).format(
        new Date(`${editRow.value.date}T12:00:00`),
      )
    : '',
)
function openEdit(rowId: string): void {
  const row = csvRows.value.find((entry) => entry.row_id === rowId)
  if (!row || !row.editable) return
  editRow.value = row
  Object.assign(editForm, {
    activity_code: row.activity,
    duration_hours: row.duration_hours?.toString() ?? '',
    current_issue: row.current_issue,
    obstacle: row.obstacle,
    next_step: row.next_step,
    pic_guidance: row.pic_guidance,
    links: row.coverage_links,
    deliverable: row.deliverable,
    current_status: row.current_status,
  })
  editError.value = ''
  editOpen.value = true
}
async function saveEdit(): Promise<void> {
  const row = editRow.value
  if (!row || saving.value) return
  const [reportId, itemId] = row.row_id.split(':')
  const links = editForm.links
    .split('\n')
    .map((link) => link.trim())
    .filter(Boolean)
  const invalid = links.find((link) => !safeCoverageUrl(link))
  if (invalid) {
    editError.value = `Link tidak valid: ${invalid}. Gunakan URL http(s) lengkap, satu per baris.`
    return
  }
  const duration = editForm.duration_hours.trim() === '' ? null : Number(editForm.duration_hours)
  if (duration !== null && (!Number.isFinite(duration) || duration < 0)) {
    editError.value = 'Durasi harus berupa angka 0 atau lebih.'
    return
  }
  if (!reportId || !itemId) return
  saving.value = true
  editError.value = ''
  try {
    const updated = await qaApi.updateRow(reportId, itemId, {
      activity_code: editForm.activity_code.trim(),
      duration_hours: duration,
      current_issue: editForm.current_issue || null,
      obstacle: editForm.obstacle || null,
      next_step: editForm.next_step || null,
      pic_guidance: editForm.pic_guidance || null,
      deliverable: editForm.deliverable || null,
      current_status: editForm.current_status.trim() || null,
      links,
    })
    csvRows.value = csvRows.value.map((entry) => (entry.row_id === updated.row_id ? updated : entry))
    editOpen.value = false
    notify('Baris manmonth diperbarui.')
    if (data.value) {
      const month = data.value.month
      qaApi
        .metrics(month)
        .then((result) => {
          if (data.value?.month === month) data.value = result
        })
        .catch(() => undefined)
    }
  } catch (cause) {
    editError.value = errorMessage(cause)
  } finally {
    saving.value = false
  }
}
let request = 0
async function load(): Promise<void> {
  const current = ++request
  loading.value = true
  error.value = ''
  exportError.value = ''
  try {
    const [result, rows] = await Promise.all([
      qaApi.metrics(month.value),
      qaApi.csvRows(month.value),
    ])
    if (current === request) {
      data.value = result
      csvRows.value = rows
    }
  } catch (cause) {
    if (current === request) error.value = errorMessage(cause)
  } finally {
    if (current === request) loading.value = false
  }
}
async function exportCsv(): Promise<void> {
  if (!data.value) return
  exporting.value = true
  exportError.value = ''
  try {
    downloadFile(await qaApi.csv(data.value.month), `qa-reports-${data.value.month}.csv`)
  } catch (cause) {
    exportError.value = errorMessage(cause)
  } finally {
    exporting.value = false
  }
}
async function exportManmonth(): Promise<void> {
  if (!data.value) return
  exportingManmonth.value = true
  exportError.value = ''
  try {
    downloadFile(await qaApi.manmonth(data.value.month), `manmonth-${data.value.month}.xlsx`)
  } catch (cause) {
    exportError.value = errorMessage(cause)
  } finally {
    exportingManmonth.value = false
  }
}
onMounted(load)
</script>
<template>
  <UiBreadcrumbs
    :items="[{ label: 'Laporan', to: '/qa-reports' }, { label: 'Ringkasan bulanan' }]"
  />
  <div class="page-header">
    <div>
      <h1>Ringkasan bulanan</h1>
      <p>Jumlah aktivitas, hasil pengujian, dan issue dari laporan harianmu.</p>
    </div>
  </div>
  <nav
    class="qa-nav"
    aria-label="Navigasi laporan"
  >
    <RouterLink to="/qa-reports">Daftar laporan</RouterLink>
    <RouterLink to="/qa-reports/monthly">Ringkasan bulanan</RouterLink>
    <RouterLink to="/qa-reports/templates">Template laporan</RouterLink>
  </nav>
  <form
    class="month-controls"
    @submit.prevent="load"
  >
    <UiInput
      v-model="month"
      label="Bulan laporan"
      type="month"
      required
      min="1900-01"
      max="2100-12"
    />
    <UiButton
      type="submit"
      variant="secondary"
      :loading="loading"
    >
      Tampilkan
    </UiButton>
    <UiButton
      variant="ghost"
      :disabled="!data || loading || !!error"
      :loading="exporting"
      @click="exportCsv"
    >
      Ekspor CSV
    </UiButton>
    <UiButton
      variant="primary"
      :disabled="!data || loading || !!error"
      :loading="exportingManmonth"
      @click="exportManmonth"
    >
      Ekspor manmonth
    </UiButton>
  </form>
  <UiSkeleton
    v-if="loading"
    :lines="6"
  />
  <UiErrorState
    v-else-if="error"
    :message="error"
    retryable
    @retry="load"
  />
  <div
    v-else-if="data"
    class="stack"
  >
    <UiErrorState
      v-if="exportError"
      :message="exportError"
    />
    <p class="small muted">Periode {{ data.month }} · mencakup semua laporan tersimpan</p>
    <dl class="metric-strip">
      <div>
        <dt>Total aktivitas</dt>
        <dd>{{ data.total }}</dd>
      </div>
      <div>
        <dt>Pass rate</dt>
        <dd>{{ data.total ? `${data.pass_rate}%` : '—' }}</dd>
      </div>
      <div>
        <dt>Aktivitas dengan issue</dt>
        <dd>{{ data.issue_count }}</dd>
      </div>
      <div>
        <dt>Entri tiket berulang</dt>
        <dd>{{ data.repeated_entries }}</dd>
      </div>
    </dl>
    <UiCard padding="md" class="hours-card">
      <div class="section-heading">
        <div>
          <h2>Target jam kerja</h2>
          <p>{{ data.total_hours.toFixed(1) }} dari {{ data.hours_target }} jam minimum bulan ini</p>
        </div>
        <strong :class="data.hours_target_met ? 'target-met' : 'target-pending'">
          {{ data.hours_target_met ? 'Target tercapai' : `${Math.max(0, data.hours_target - data.total_hours).toFixed(1)} jam lagi` }}
        </strong>
      </div>
      <meter
        class="hours-meter"
        :value="data.total_hours"
        :max="data.hours_target"
        min="0"
        :aria-label="`${data.total_hours} dari ${data.hours_target} jam`"
      />
    </UiCard>
    <p class="small muted">
      Pass rate = hasil Pass ÷ aktivitas dengan Result terisi. Result yang tidak dipakai template
      tidak dihitung. Tiket yang diuji ulang pada tanggal sama tetap dihitung sebagai entri
      terpisah.
    </p>
    <UiEmptyState
      v-if="!data.total"
      title="Belum ada aktivitas pada bulan ini"
      description="Aktivitas akan muncul setelah kamu menyimpan laporan harian."
    >
      <template #action>
        <RouterLink
          to="/qa-reports"
          class="qa-link"
        >
          Buka laporan harian
        </RouterLink>
      </template>
    </UiEmptyState>
    <template v-else>
      <UiCard padding="md">
        <div class="section-heading">
          <div>
            <h2>Aktivitas per hari</h2>
            <p>Satu batang mewakili jumlah entri pada tanggal tersebut.</p>
          </div>
          <span class="small muted">Puncak {{ peak }} aktivitas</span>
        </div>
        <div
          class="trend-chart"
          role="img"
          :aria-label="`Tren ${data.month}, total ${data.total} aktivitas. Rincian tersedia dalam tabel di bawah.`"
        >
          <div
            v-for="day in data.trend"
            :key="day.date"
            class="trend-day"
            :title="`${day.date}: ${day.count} aktivitas`"
          >
            <div class="bar-track">
              <span
                class="bar"
                :style="{ height: `${(day.count / peak) * 100}%` }"
              />
            </div>
            <span>{{ Number(day.date.slice(-2)) }}</span>
          </div>
        </div>
        <details class="trend-details">
          <summary>Lihat angka per tanggal</summary>
          <UiDataTable
            :rows="data.trend"
            :columns="[
              { key: 'date', label: 'Tanggal' },
              { key: 'count', label: 'Aktivitas' },
            ]"
            row-key="date"
            caption="Jumlah aktivitas per tanggal"
            :page-size="31"
          />
        </details>
      </UiCard>
      <div class="qa-form-grid">
        <section
          v-for="group in [
            { title: 'Menurut environment', rows: data.environments },
            { title: 'Menurut hasil', rows: data.results },
          ]"
          :key="group.title"
        >
          <h2 class="mb-5">{{ group.title }}</h2>
          <dl class="breakdown">
            <div
              v-for="row in group.rows"
              :key="row.label"
            >
              <dt>{{ row.label }}</dt>
              <dd>
                <meter
                  :value="row.count"
                  :max="data.total"
                  min="0"
                  :aria-label="`${row.label}: ${row.count} dari ${data.total}`"
                />
                <span>{{ row.count }}</span>
              </dd>
            </div>
          </dl>
        </section>
      </div>
      <UiCard padding="md">
        <div class="section-heading">
          <div>
            <h2>Preview manmonth</h2>
            <p>Pratinjau mengikuti kolom pada file ekspor manmonth.</p>
          </div>
        </div>
        <UiDataTable
          :rows="manmonthRows"
          :columns="manmonthColumns"
          row-key="row_id"
          caption="Preview isi laporan manmonth bulanan"
          :page-size="10"
        >
          <template
            v-for="column in longColumns"
            :key="column.key"
            #[`cell-${column.key}`]="{ row, value }"
          >
            <div class="clamp-cell">
              <span :class="{ clamped: isLong(value) }">{{ value || '—' }}</span>
              <button
                v-if="isLong(value)"
                type="button"
                class="view-more"
                @click="showDetail(column.label, column.key, row)"
              >
                Lihat selengkapnya
              </button>
            </div>
          </template>
          <template #cell-actions="{ row }">
            <UiButton
              size="sm"
              variant="secondary"
              :disabled="!row.editable"
              :title="row.editable ? undefined : 'Laporan sudah dikunci dan tidak dapat diedit'"
              @click="openEdit(row.row_id)"
            >
              Edit
            </UiButton>
          </template>
        </UiDataTable>
      </UiCard>
      <UiModal
        v-model="detailOpen"
        :title="detail?.label ?? ''"
        :description="detail?.date"
        size="lg"
      >
        <div
          v-if="detail?.key === 'coverage_links'"
          class="detail-body"
        >
          <template
            v-for="(link, index) in detail.value.split('\n')"
            :key="index"
          >
            <a
              v-if="safeCoverageUrl(link)"
              :href="link"
              target="_blank"
              rel="noopener noreferrer"
            >{{ link }}</a>
            <span v-else>{{ link }}</span>
          </template>
        </div>
        <p
          v-else
          class="detail-body"
        >
          {{ detail?.value }}
        </p>
      </UiModal>
      <UiModal
        v-model="editOpen"
        title="Edit baris manmonth"
        :description="editDateLabel"
        size="lg"
        :dismissible="!saving"
      >
        <form
          id="manmonth-row-form"
          class="edit-row-form"
          @submit.prevent="saveEdit"
        >
          <div class="edit-row-pair">
            <UiInput
              v-model="editForm.activity_code"
              label="Ticket / Task Ref"
              maxlength="100"
            />
            <UiInput
              v-model="editForm.duration_hours"
              label="Durasi Pengerjaan (Hour)"
              type="number"
              min="0"
              step="0.25"
            />
          </div>
          <UiTextarea
            v-model="editForm.current_issue"
            label="Task Summary (Progress)"
            :rows="4"
            maxlength="10000"
          />
          <UiTextarea
            v-model="editForm.obstacle"
            label="Kendala (Obstacle)"
            :rows="2"
            maxlength="10000"
          />
          <UiTextarea
            v-model="editForm.next_step"
            label="Next Step / Action"
            :rows="2"
            maxlength="10000"
          />
          <UiTextarea
            v-model="editForm.pic_guidance"
            label="PIC / Guidance"
            :rows="2"
            maxlength="10000"
          />
          <UiTextarea
            v-model="editForm.links"
            label="Notion / Reference Link"
            hint="Satu URL per baris."
            :rows="3"
          />
          <UiTextarea
            v-model="editForm.deliverable"
            label="Deliverable"
            :rows="2"
            maxlength="10000"
          />
          <UiInput
            v-model="editForm.current_status"
            label="Status"
            maxlength="100"
            hint="Kosongkan untuk mengikuti hasil pengujian."
          />
          <p
            v-if="editError"
            class="field-error"
            role="alert"
          >
            {{ editError }}
          </p>
        </form>
        <template #footer>
          <UiButton
            variant="secondary"
            :disabled="saving"
            @click="editOpen = false"
          >
            Batal
          </UiButton>
          <UiButton
            type="submit"
            form="manmonth-row-form"
            :loading="saving"
          >
            Simpan
          </UiButton>
        </template>
      </UiModal>
    </template>
  </div>
</template>
<style scoped>
.month-controls {
  display: flex;
  align-items: end;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 32px;
}
.metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  padding: 24px 0;
  border-block: 1px solid var(--color-border);
  gap: 24px;
}
.hours-card { margin-bottom: 4px; }
.hours-meter { display: block; width: 100%; height: 18px; margin-top: 16px; accent-color: var(--color-primary); }
.target-met { color: var(--color-success, var(--color-primary)); }
.target-pending { color: var(--color-text-muted); }
dt {
  font-size: 14px;
  color: var(--color-text-muted);
}
.metric-strip dd {
  font-size: 34px;
  font-weight: 500;
  margin-top: 12px;
  letter-spacing: -0.04em;
  color: var(--color-primary);
}
.trend-chart {
  display: flex;
  height: 200px;
  gap: 5px;
  padding-top: 20px;
}
.trend-day {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  gap: 10px;
  text-align: center;
  font-size: 11px;
  color: var(--color-text-muted);
}
.bar-track {
  flex: 1;
  display: flex;
  align-items: end;
  border-bottom: 1px solid var(--color-border);
}
.bar {
  display: block;
  width: 100%;
  background: var(--color-primary);
  border-radius: 3px 3px 0 0;
}
.trend-details {
  margin-top: 24px;
  font-size: 14px;
}
summary {
  cursor: pointer;
  color: var(--color-primary);
  padding: 12px 0;
}
.breakdown {
  display: grid;
  gap: 20px;
}
.breakdown > div {
  display: grid;
  grid-template-columns: minmax(100px, 1fr) minmax(0, 2fr);
  align-items: center;
  gap: 12px;
}
.breakdown dd {
  display: flex;
  gap: 16px;
  align-items: center;
  font-size: 14px;
}
meter {
  flex: 1;
  min-width: 0;
  height: 16px;
  accent-color: var(--color-secondary);
}
meter::-webkit-meter-bar {
  background: var(--color-surface-subtle);
  border: 0;
}
meter::-webkit-meter-optimum-value {
  background: var(--color-secondary);
}
.clamp-cell {
  display: grid;
  justify-items: start;
  gap: 4px;
  min-width: 160px;
  max-width: 300px;
}
.clamp-cell > span {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.clamped {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.view-more {
  padding: 0;
  border: 0;
  background: none;
  color: var(--color-primary);
  font-size: 12px;
  cursor: pointer;
}
.view-more:hover {
  text-decoration: underline;
}
.detail-body {
  display: grid;
  gap: 6px;
  max-height: 60vh;
  overflow-y: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: 14px;
}
.detail-body a {
  color: var(--color-primary);
}
.edit-row-form {
  display: grid;
  gap: 14px;
  max-height: 62vh;
  overflow-y: auto;
  padding-right: 4px;
}
.edit-row-pair {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 14px;
}
@media (max-width: 767px) {
  .metric-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .edit-row-pair {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 520px) {
  .trend-chart {
    gap: 3px;
  }
  .trend-day:not(:first-child):not(:last-child):nth-child(even) > span {
    visibility: hidden;
  }
}
</style>
