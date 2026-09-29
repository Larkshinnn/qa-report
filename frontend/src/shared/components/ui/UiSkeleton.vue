<script setup lang="ts">
withDefaults(defineProps<{ lines?: number; label?: string }>(), {
  lines: 3,
  label: 'Memuat konten',
})
</script>
<template>
  <div
    role="status"
    class="skeleton"
  >
    <span class="sr-only">{{ label }}</span>
    <span
      v-for="n in lines"
      :key="n"
      aria-hidden="true"
    />
  </div>
</template>
<style scoped>
.skeleton {
  display: grid;
  gap: 14px;
}
.skeleton > span[aria-hidden] {
  height: 16px;
  border-radius: 4px;
  background: var(--color-surface-subtle);
  animation: pulse 1.5s ease-in-out infinite alternate;
}
.skeleton > span:last-child {
  width: 65%;
}
@keyframes pulse {
  to {
    opacity: 0.5;
  }
}
</style>
