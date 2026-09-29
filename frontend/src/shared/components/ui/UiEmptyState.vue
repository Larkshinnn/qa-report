<script setup lang="ts">
defineProps<{ title: string; description: string; compact?: boolean }>()
</script>
<template>
  <div :class="['empty-state', { compact }]">
    <div
      v-if="$slots.icon"
      class="empty-icon"
      aria-hidden="true"
    >
      <slot name="icon" />
    </div>
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
    <div
      v-if="$slots.action"
      class="empty-action"
    >
      <slot name="action" />
    </div>
  </div>
</template>
<style scoped>
.empty-state {
  padding: 32px 16px;
  text-align: center;
  display: grid;
  justify-items: center;
  gap: 10px;
}
.empty-icon {
  color: var(--color-secondary);
  margin-bottom: 5px;
}
.empty-state p {
  color: var(--color-text-muted);
  font-size: 14px;
  max-width: 38ch;
}
.empty-action {
  margin-top: 10px;
}
.compact {
  padding: 20px 8px;
}
</style>
