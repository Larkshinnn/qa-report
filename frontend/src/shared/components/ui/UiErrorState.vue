<script setup lang="ts">
import { PhWarningCircle } from '@phosphor-icons/vue'
import UiButton from './UiButton.vue'
defineProps<{ message: string; retryable?: boolean }>()
const emit = defineEmits<{ retry: [] }>()
</script>
<template>
  <div
    class="error-state"
    role="alert"
  >
    <PhWarningCircle :size="22" />
    <p>{{ message }}</p>
    <UiButton
      v-if="retryable"
      variant="secondary"
      size="sm"
      @click="emit('retry')"
    >
      Coba lagi
    </UiButton>
  </div>
</template>
<style scoped>
.error-state {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-control);
  color: var(--color-danger);
  font-size: 14px;
}
.error-state p {
  flex: 1;
}
</style>
