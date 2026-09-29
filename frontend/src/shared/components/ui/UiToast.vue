<script setup lang="ts">
import { PhCheckCircle, PhX } from '@phosphor-icons/vue'
import { useToast } from '../../composables/useToast'
import UiButton from './UiButton.vue'
const { messages, dismiss } = useToast()
</script>
<template>
  <div
    class="toast-host"
    role="status"
    aria-live="polite"
    aria-relevant="additions"
  >
    <div
      v-for="item in messages"
      :key="item.id"
      class="toast-message"
    >
      <PhCheckCircle
        :size="20"
        class="toast-icon"
      />
      <p>{{ item.message }}</p>
      <UiButton
        variant="ghost"
        icon-only
        label="Tutup notifikasi"
        @click="dismiss(item.id)"
      >
        <PhX :size="16" />
      </UiButton>
    </div>
  </div>
</template>
<style scoped>
.toast-host {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: var(--layer-notification);
  display: grid;
  gap: 12px;
  width: min(390px, calc(100% - 32px));
}
.toast-message {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 8px 8px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  box-shadow: var(--shadow-floating);
  font-size: 14px;
}
.toast-message p {
  flex: 1;
}
.toast-icon {
  color: var(--color-success);
}
</style>
