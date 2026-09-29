<script setup lang="ts">
import { ref, useId } from 'vue'
import UiField from './UiField.vue'
defineOptions({ inheritAttrs: false })
withDefaults(
  defineProps<{
    label: string
    hint?: string
    error?: string
    required?: boolean
    id?: string
    rows?: string | number
  }>(),
  { rows: 4 },
)
const value = defineModel<string>({ default: '' })
const generatedId = useId()
const textarea = ref<HTMLTextAreaElement>()
defineExpose({ textarea })
</script>
<template>
  <UiField
    :id="id ?? generatedId"
    :label="label"
    :hint="hint"
    :error="error"
    :required="required"
  >
    <textarea
      ref="textarea"
      v-bind="$attrs"
      :id="id ?? generatedId"
      v-model="value"
      class="field-control"
      :rows="rows"
      :required="required"
      :aria-invalid="!!error || undefined"
      :aria-describedby="error || hint ? `${id ?? generatedId}-description` : undefined"
    />
  </UiField>
</template>
<style scoped>
textarea {
  resize: vertical;
  min-height: 110px;
}
</style>
