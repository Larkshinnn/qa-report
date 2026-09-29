<script setup lang="ts">
import { useId } from 'vue'
import UiField from './UiField.vue'
defineOptions({ inheritAttrs: false })
defineProps<{
  label: string
  hint?: string
  error?: string
  required?: boolean
  type?: string
  id?: string
}>()
const value = defineModel<string>({ default: '' })
const generatedId = useId()
</script>
<template>
  <UiField
    :id="id ?? generatedId"
    :label="label"
    :hint="hint"
    :error="error"
    :required="required"
  >
    <input
      v-bind="$attrs"
      :id="id ?? generatedId"
      v-model="value"
      class="field-control"
      :type="type ?? 'text'"
      :required="required"
      :aria-invalid="!!error || undefined"
      :aria-describedby="error || hint ? `${id ?? generatedId}-description` : undefined"
    />
  </UiField>
</template>
