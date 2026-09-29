<script setup lang="ts">
import { useId } from 'vue'
defineOptions({ inheritAttrs: false })
defineProps<{ label: string; hint?: string; disabled?: boolean }>()
const checked = defineModel<boolean>({ default: false })
const id = useId()
</script>
<template>
  <label
    class="checkbox-field"
    :for="id"
  >
    <input
      v-bind="$attrs"
      :id="id"
      v-model="checked"
      type="checkbox"
      :disabled="disabled"
      :aria-describedby="hint ? `${id}-hint` : undefined"
    />
    <span>
      <span>{{ label }}</span>
      <span
        v-if="hint"
        :id="`${id}-hint`"
        class="field-hint"
      >
        {{ hint }}
      </span>
    </span>
  </label>
</template>
<style scoped>
.checkbox-field {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  font-size: 14px;
  cursor: pointer;
}
input {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary);
  flex-shrink: 0;
}
.field-hint {
  display: block;
  margin-top: 3px;
}
.checkbox-field:has(:disabled) {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
