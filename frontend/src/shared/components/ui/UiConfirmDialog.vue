<script setup lang="ts">
import UiModal from './UiModal.vue'
import UiButton from './UiButton.vue'
withDefaults(
  defineProps<{
    title: string
    description: string
    confirmLabel?: string
    busy?: boolean
    error?: string
  }>(),
  { confirmLabel: 'Hapus', busy: false },
)
const open = defineModel<boolean>({ required: true })
const emit = defineEmits<{ confirm: [] }>()
</script>
<template>
  <UiModal
    v-model="open"
    :title="title"
    :description="description"
    size="sm"
    :dismissible="!busy"
  >
    <p
      v-if="error"
      role="alert"
      class="field-error"
    >
      {{ error }}
    </p>
    <template #footer>
      <UiButton
        variant="secondary"
        :disabled="busy"
        autofocus
        @click="open = false"
      >
        Batal
      </UiButton>
      <UiButton
        variant="danger-solid"
        :loading="busy"
        @click="emit('confirm')"
      >
        {{ confirmLabel }}
      </UiButton>
    </template>
  </UiModal>
</template>
