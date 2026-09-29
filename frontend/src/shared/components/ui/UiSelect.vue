<script setup lang="ts">
import { useId } from 'vue'
import UiField from './UiField.vue'
defineOptions({ inheritAttrs: false })
defineProps<{
  label: string
  options: readonly { value: string; label: string; disabled?: boolean }[]
  hint?: string
  error?: string
  required?: boolean
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
    <select
      v-bind="$attrs"
      :id="id ?? generatedId"
      v-model="value"
      class="field-control"
      :required="required"
      :aria-invalid="!!error || undefined"
      :aria-describedby="error || hint ? `${id ?? generatedId}-description` : undefined"
    >
      <option
        v-for="option in options"
        :key="option.value"
        :value="option.value"
        :disabled="option.disabled"
      >
        {{ option.label }}
      </option>
    </select>
  </UiField>
</template>
