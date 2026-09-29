<script setup lang="ts">
import UiCopyButton from './UiCopyButton.vue'
withDefaults(defineProps<{ code: string; label: string; copyable?: boolean }>(), { copyable: true })
</script>
<template>
  <div class="code-block">
    <div class="code-heading">
      <span>{{ label }}</span>
      <UiCopyButton
        v-if="copyable"
        :value="code"
      />
    </div>
    <pre
      tabindex="0"
      :aria-label="label"
    ><code>{{ code }}</code></pre>
  </div>
</template>
<style scoped>
.code-block {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  min-width: 0;
  overflow: hidden;
}
.code-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--color-border);
  font-size: 12px;
  color: var(--color-text-muted);
}
pre {
  margin: 0;
  padding: 20px;
  background: var(--color-surface-subtle);
  font-size: 13px;
  line-height: 1.7;
  overflow-x: auto;
  max-height: 420px;
  tab-size: 2;
}
</style>
