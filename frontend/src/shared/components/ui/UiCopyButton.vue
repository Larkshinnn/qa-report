<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { PhCopy, PhCheck } from '@phosphor-icons/vue'
import UiButton from './UiButton.vue'
const props = withDefaults(defineProps<{ value: string; label?: string }>(), { label: 'Salin' })
const copied = ref(false)
const error = ref('')
let timer: ReturnType<typeof setTimeout> | undefined
async function copy(): Promise<void> {
  error.value = ''
  try {
    await navigator.clipboard.writeText(props.value)
    copied.value = true
    clearTimeout(timer)
    timer = setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    error.value = 'Clipboard tidak tersedia. Pilih teks dan salin secara manual.'
  }
}
onBeforeUnmount(() => clearTimeout(timer))
</script>
<template>
  <div class="copy-control">
    <UiButton
      variant="secondary"
      size="sm"
      @click="copy"
    >
      <component
        :is="copied ? PhCheck : PhCopy"
        :size="16"
      />
      {{ copied ? 'Tersalin' : label }}
    </UiButton>
    <span
      role="status"
      class="sr-only"
    >
      {{ copied ? 'Teks tersalin' : '' }}
    </span>
    <p
      v-if="error"
      role="alert"
      class="field-error"
    >
      {{ error }}
    </p>
  </div>
</template>
<style scoped>
.copy-control {
  display: grid;
  gap: 8px;
}
</style>
