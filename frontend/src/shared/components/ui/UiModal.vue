<script setup lang="ts">
import { onBeforeUnmount, ref, useId, watchEffect } from 'vue'
import { PhX } from '@phosphor-icons/vue'
import UiButton from './UiButton.vue'
withDefaults(
  defineProps<{
    title: string
    description?: string
    dismissible?: boolean
    size?: 'sm' | 'md' | 'lg'
  }>(),
  { dismissible: true, size: 'md' },
)
const open = defineModel<boolean>({ required: true })
const dialog = ref<HTMLDialogElement>()
const titleId = useId()
watchEffect(
  () => {
    if (open.value && dialog.value && !dialog.value.open) dialog.value.showModal()
    else if (!open.value && dialog.value?.open) dialog.value.close()
  },
  { flush: 'post' },
)
onBeforeUnmount(() => dialog.value?.close())
</script>
<template>
  <Teleport to="body">
    <dialog
      ref="dialog"
      :class="['ui-modal', `modal-${size}`]"
      :aria-labelledby="titleId"
      :aria-describedby="description ? `${titleId}-description` : undefined"
      @cancel.prevent="dismissible && (open = false)"
      @close="open = false"
      @click.self="dismissible && (open = false)"
    >
      <div class="modal-inner">
        <div class="modal-heading">
          <div>
            <h2 :id="titleId">{{ title }}</h2>
            <p
              v-if="description"
              :id="`${titleId}-description`"
            >
              {{ description }}
            </p>
          </div>
          <UiButton
            v-if="dismissible"
            icon-only
            label="Tutup dialog"
            variant="ghost"
            @click="open = false"
          >
            <PhX :size="20" />
          </UiButton>
        </div>
        <slot v-if="open" />
        <div
          v-if="$slots.footer"
          class="modal-footer"
        >
          <slot name="footer" />
        </div>
      </div>
    </dialog>
  </Teleport>
</template>
<style scoped>
.ui-modal {
  margin: auto;
  padding: 0;
  width: min(560px, calc(100% - 32px));
  max-height: calc(100dvh - 48px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-panel);
  background: var(--color-surface);
  color: var(--color-text);
  box-shadow: var(--shadow-floating);
}
.ui-modal::backdrop {
  background: var(--color-overlay);
}
.modal-sm {
  width: min(440px, calc(100% - 32px));
}
.modal-lg {
  width: min(780px, calc(100% - 32px));
}
.modal-inner {
  padding: 24px;
}
.modal-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
  align-items: flex-start;
}
.modal-heading p {
  margin-top: 6px;
  color: var(--color-text-muted);
  font-size: 14px;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}
</style>
