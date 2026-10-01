<script setup lang="ts">
import { nextTick, ref, useId } from 'vue'
import UiField from './UiField.vue'
defineOptions({ inheritAttrs: false })
const props = withDefaults(
  defineProps<{
    label: string
    hint?: string
    error?: string
    required?: boolean
    id?: string
    rows?: string | number
    tabIndent?: boolean
  }>(),
  { rows: 4, tabIndent: false },
)
const value = defineModel<string>({ default: '' })
const generatedId = useId()
const textarea = ref<HTMLTextAreaElement>()
defineExpose({ textarea })

function onKeydown(event: KeyboardEvent): void {
  if (!props.tabIndent || event.key !== 'Tab') return
  const target = event.currentTarget as HTMLTextAreaElement
  const start = target.selectionStart
  const end = target.selectionEnd
  const lineStart = target.value.lastIndexOf('\n', start - 1) + 1

  if (event.shiftKey) {
    if (target.value[lineStart] !== '\t') return
    event.preventDefault()
    value.value = target.value.slice(0, lineStart) + target.value.slice(lineStart + 1)
    void nextTick(() =>
      target.setSelectionRange(Math.max(lineStart, start - 1), Math.max(lineStart, end - 1)),
    )
    return
  }

  event.preventDefault()
  value.value = target.value.slice(0, start) + '\t' + target.value.slice(start)
  void nextTick(() => target.setSelectionRange(start + 1, end + 1))
}
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
      @keydown="onKeydown"
    />
  </UiField>
</template>
<style scoped>
textarea {
  resize: vertical;
  min-height: 110px;
}
</style>
