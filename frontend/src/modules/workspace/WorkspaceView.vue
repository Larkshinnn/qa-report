<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { errorMessage } from '../../shared/api'
import UiBreadcrumbs from '../../shared/components/ui/UiBreadcrumbs.vue'
import UiCard from '../../shared/components/ui/UiCard.vue'
import UiErrorState from '../../shared/components/ui/UiErrorState.vue'
import UiInput from '../../shared/components/ui/UiInput.vue'
import UiButton from '../../shared/components/ui/UiButton.vue'
import UiSkeleton from '../../shared/components/ui/UiSkeleton.vue'
import { workspaceApi, type WorkspaceSummary } from './api'
import { localDate } from '../qa-reports/api'

const month = ref(localDate().slice(0, 7))
const data = ref<WorkspaceSummary>()
const loading = ref(false)
const error = ref('')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    data.value = await workspaceApi.summary(month.value)
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat('id-ID', { day: 'numeric', month: 'short' }).format(
    new Date(`${value}T12:00:00`),
  )
}

onMounted(load)
</script>

<template>
  <UiBreadcrumbs :items="[{ label: 'Workspace' }]" />
  <div class="page-header">
    <div>
      <h1>Workspace bersama</h1>
      <p>Lihat progres bulanan tim. Laporan anggota lain hanya ditampilkan sebagai ringkasan.</p>
    </div>
  </div>
  <form class="month-controls" @submit.prevent="load">
    <UiInput v-model="month" label="Bulan" type="month" required min="1900-01" max="2100-12" />
    <UiButton type="submit" variant="secondary" :loading="loading">
      Tampilkan
    </UiButton>
  </form>
  <UiSkeleton v-if="loading" :lines="5" />
  <UiErrorState v-else-if="error" :message="error" retryable @retry="load" />
  <template v-else-if="data">
    <p class="small muted">{{ data.users.length }} akun · {{ data.month }}</p>
    <div v-if="data.users.length" class="user-list">
      <UiCard v-for="user in data.users" :key="user.account_id" padding="md">
        <div class="user-heading">
          <div>
            <h2>{{ user.display_name }}</h2>
            <p class="small muted">{{ user.email }}</p>
          </div>
          <strong>{{ user.total_hours.toFixed(1) }} / {{ data.hours_target }} jam</strong>
        </div>
        <meter
          class="hours-meter"
          :value="user.total_hours"
          :max="data.hours_target"
          min="0"
          :aria-label="`${user.display_name}: ${user.total_hours} dari ${data.hours_target} jam`"
        />
        <dl class="user-metrics">
          <div><dt>Laporan</dt><dd>{{ user.report_count }}</dd></div>
          <div><dt>Aktivitas</dt><dd>{{ user.activity_count }}</dd></div>
          <div><dt>Pass rate</dt><dd>{{ user.activity_count ? `${user.pass_rate}%` : '—' }}</dd></div>
          <div><dt>Issue</dt><dd>{{ user.issue_count }}</dd></div>
        </dl>
        <div class="report-days">
          <span class="small muted">Tanggal laporan</span>
          <span v-if="user.report_dates.length" class="day-list">
            <span v-for="day in user.report_dates" :key="day" class="day-chip">{{ dateLabel(day) }}</span>
          </span>
          <span v-else class="small muted">Belum ada laporan bulan ini</span>
        </div>
      </UiCard>
    </div>
    <UiCard v-else padding="md"><p>Belum ada akun terdaftar.</p></UiCard>
  </template>
</template>

<style scoped>
.month-controls { display: flex; align-items: end; gap: 14px; margin: 24px 0; }
.user-list { display: grid; gap: 14px; margin-top: 18px; }
.user-heading { display: flex; justify-content: space-between; gap: 16px; align-items: start; }
.user-heading h2 { margin: 0 0 4px; font-size: 18px; }
.user-heading p { margin: 0; }
.user-heading strong { color: var(--color-primary); white-space: nowrap; }
.hours-meter { width: 100%; height: 16px; margin: 14px 0; accent-color: var(--color-primary); }
.user-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 0; }
.user-metrics dt { color: var(--color-text-muted); font-size: 12px; }
.user-metrics dd { margin: 4px 0 0; font-size: 17px; font-weight: 600; }
.report-days { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; border-top: 1px solid var(--color-border); padding-top: 12px; margin-top: 14px; }
.day-list { display: flex; gap: 6px; flex-wrap: wrap; }
.day-chip { padding: 3px 8px; border: 1px solid var(--color-border); border-radius: 999px; font-size: 12px; }
@media (max-width: 560px) { .user-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); } .user-heading { flex-direction: column; } }
</style>
