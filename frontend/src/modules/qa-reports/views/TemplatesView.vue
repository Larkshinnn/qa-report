<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage } from '../../../shared/api'
import { useToast } from '../../../shared/composables/useToast'
import UiBreadcrumbs from '../../../shared/components/ui/UiBreadcrumbs.vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiDataTable from '../../../shared/components/ui/UiDataTable.vue'
import UiEmptyState from '../../../shared/components/ui/UiEmptyState.vue'
import UiConfirmDialog from '../../../shared/components/ui/UiConfirmDialog.vue'
import { qaApi, type ReportTemplate } from '../api'
import { rememberTemplate } from '../templates'
import '../styles.css'

const router = useRouter()
const { notify } = useToast()
const templates = ref<ReportTemplate[]>([])
const loading = ref(true)
const error = ref('')
const busy = ref(false)
const selected = ref<ReportTemplate>()
const removeOpen = ref(false)
const removeError = ref('')
const columns = [
  { key: 'name', label: 'Template', sortable: true },
  { key: 'usage_count', label: 'Digunakan', sortable: true },
  { key: 'updated_at', label: 'Diperbarui', sortable: true },
  { key: 'id', label: 'Aksi' },
] as const
const dateFormat = new Intl.DateTimeFormat('id-ID', { dateStyle: 'medium' })

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    templates.value = await qaApi.listTemplates()
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}
function useTemplate(template: ReportTemplate): void {
  rememberTemplate(template.id)
  void router.push({ path: '/qa-reports/new', query: { template: template.id } })
}
function requestRemove(template: ReportTemplate): void {
  selected.value = template
  removeError.value = ''
  removeOpen.value = true
}
async function remove(): Promise<void> {
  if (!selected.value || busy.value) return
  const id = selected.value.id
  busy.value = true
  removeError.value = ''
  try {
    await qaApi.removeTemplate(id)
    templates.value = templates.value.filter((template) => template.id !== id)
    removeOpen.value = false
    notify('Template dihapus. Laporan lama tetap menyimpan formatnya.')
  } catch (cause) {
    removeError.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}
onMounted(load)
</script>

<template>
  <UiBreadcrumbs :items="[{ label: 'Laporan', to: '/qa-reports' }, { label: 'Template' }]" />
  <div class="page-header">
    <div>
      <h1>Template laporan</h1>
      <p>Kelola format laporanmu. Pilih template untuk langsung mulai mengisi laporan.</p>
    </div>
    <UiButton @click="router.push('/qa-reports/templates/new')">Tambah template</UiButton>
  </div>
  <nav
    class="qa-nav"
    aria-label="Navigasi laporan"
  >
    <RouterLink to="/qa-reports">Daftar laporan</RouterLink>
    <RouterLink to="/qa-reports/monthly">Ringkasan bulanan</RouterLink>
    <RouterLink to="/qa-reports/templates">Template laporan</RouterLink>
  </nav>
  <section
    class="stack template-table"
    aria-label="Daftar template"
  >
    <UiEmptyState
      v-if="!loading && !error && !templates.length"
      title="Belum ada template"
      description="Tambah template pertamamu. Contoh format QA sudah disiapkan untuk kamu sesuaikan."
    />
    <UiDataTable
      v-else
      :rows="templates"
      :columns="columns"
      row-key="id"
      :page-size="20"
      caption="Template laporan QA"
      :loading="loading"
      :error="error"
      @retry="load"
    >
      <template #cell-name="{ row }">
        <div class="template-name">
          <RouterLink
            class="qa-link"
            :to="`/qa-reports/templates/${row.id}/edit`"
          >
            {{ row.name }}
          </RouterLink>
          <p
            v-if="row.description"
            class="small muted"
          >
            {{ row.description }}
          </p>
        </div>
      </template>
      <template #cell-usage_count="{ row }">{{ row.usage_count }} laporan</template>
      <template #cell-updated_at="{ row }">
        <time :datetime="row.updated_at">{{ dateFormat.format(new Date(row.updated_at)) }}</time>
      </template>
      <template #cell-id="{ row }">
        <div class="qa-actions">
          <UiButton
            variant="secondary"
            size="sm"
            :aria-label="`Gunakan template ${row.name}`"
            :disabled="busy"
            @click="useTemplate(row)"
          >
            Gunakan
          </UiButton>
          <RouterLink
            class="qa-link"
            :aria-label="`Edit template ${row.name}`"
            :to="`/qa-reports/templates/${row.id}/edit`"
          >
            Edit
          </RouterLink>
          <UiButton
            variant="danger"
            size="sm"
            :aria-label="`Hapus template ${row.name}`"
            :disabled="busy"
            @click="requestRemove(row)"
          >
            Hapus
          </UiButton>
        </div>
      </template>
    </UiDataTable>
    <p class="small muted">
      Format standar QA selalu tersedia saat membuat laporan. Mengubah template tidak mengubah
      laporan lama.
    </p>
  </section>
  <UiConfirmDialog
    v-model="removeOpen"
    title="Hapus template ini?"
    :description="`${selected?.name ?? 'Template'} akan dihapus. Laporan lama tetap menyimpan formatnya.`"
    confirm-label="Hapus template"
    :busy="busy"
    :error="removeError"
    @confirm="remove"
  />
</template>

<style scoped>
.template-table {
  min-width: 0;
}
.template-name {
  min-width: 180px;
  max-width: 32rem;
  white-space: normal;
  overflow-wrap: anywhere;
}
.template-name p {
  margin-top: 6px;
}
</style>
