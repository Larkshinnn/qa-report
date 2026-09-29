<script setup lang="ts">
import { ref } from 'vue'
import { qaApi, type Report } from '../api'
import { errorMessage } from '../../../shared/api'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiConfirmDialog from '../../../shared/components/ui/UiConfirmDialog.vue'
import UiErrorState from '../../../shared/components/ui/UiErrorState.vue'
const props = defineProps<{
  reportId: string
  reportTitle: string
  report?: Report
  disabled?: boolean
}>()
const emit = defineEmits<{ deleted: [] }>()
const open = ref(false),
  busy = ref(false),
  error = ref(''),
  selected = ref<Report>()
async function ask(): Promise<void> {
  if (busy.value || props.disabled) return
  busy.value = true
  error.value = ''
  try {
    selected.value = props.report ?? (await qaApi.get(props.reportId))
    open.value = true
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}
async function remove(): Promise<void> {
  if (!selected.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await qaApi.remove(selected.value.id, selected.value.version)
    open.value = false
    emit('deleted')
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <UiButton
    variant="danger"
    :loading="busy"
    :disabled="disabled"
    :label="`Hapus laporan ${reportTitle}`"
    @click="ask"
  >
    Hapus laporan
  </UiButton>
  <UiErrorState
    v-if="error && !open"
    :message="error"
  />
  <UiConfirmDialog
    v-model="open"
    title="Hapus laporan ini?"
    :description="`Hapus ${selected?.title ?? reportTitle} (${selected?.report_date ?? ''}) beserta ${selected?.items.length ?? 0} aktivitas dan semua link? Isian lokal juga akan hilang. Tindakan ini permanen; pemulihan hanya tersedia jika kamu memiliki backup sebelumnya.`"
    confirm-label="Hapus permanen"
    :busy="busy"
    :error="error"
    @confirm="remove"
  />
</template>
