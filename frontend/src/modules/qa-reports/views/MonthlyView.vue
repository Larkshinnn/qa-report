<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { qaApi, localDate, type CsvPreviewRow, type Metrics } from '../api'
import { downloadFile, errorMessage } from '../../../shared/api'
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
const csvColumns: { key: keyof CsvPreviewRow; label: string }[] = [
  { key: 'date', label: 'Tanggal' },
  { key: 'title', label: 'Laporan' },
  { key: 'activity', label: 'Aktivitas' },
  { key: 'environment', label: 'Environment' },
  { key: 'result', label: 'Hasil' },
  { key: 'current_status', label: 'Status saat ini' },
  { key: 'current_issue', label: 'Issue saat ini' },
  { key: 'coverage_links', label: 'Coverage links' },
]
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
            <h2>Preview CSV</h2>
            <p>Data diurutkan dari tanggal paling awal ke paling akhir dalam bulan terpilih.</p>
          </div>
        </div>
        <UiDataTable
          :rows="csvRows"
          :columns="csvColumns"
          row-key="row_id"
          caption="Preview isi CSV laporan bulanan"
          :page-size="10"
        >
          <template #cell-current_issue="{ value }">
            <span class="csv-preview-cell">{{ value || '—' }}</span>
          </template>
          <template #cell-coverage_links="{ value }">
            <span class="csv-preview-cell">{{ value || '—' }}</span>
          </template>
        </UiDataTable>
      </UiCard>
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
.csv-preview-cell {
  display: block;
  min-width: 260px;
  max-width: 520px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
@media (max-width: 767px) {
  .metric-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
