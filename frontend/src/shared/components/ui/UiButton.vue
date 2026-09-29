<script setup lang="ts">
withDefaults(
  defineProps<
    {
      variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'danger-solid' | 'quiet'
      size?: 'sm' | 'md' | 'lg'
      type?: 'button' | 'submit' | 'reset'
      disabled?: boolean
      loading?: boolean
      label?: string
    } & ({ iconOnly: true; label: string } | { iconOnly?: false; label?: string })
  >(),
  {
    variant: 'primary',
    size: 'md',
    type: 'button',
    disabled: false,
    loading: false,
    iconOnly: false,
  },
)
const emit = defineEmits<{ click: [event: MouseEvent] }>()
</script>

<template>
  <button
    :type="type"
    :class="['ui-button', `button-${variant}`, `button-${size}`, { 'button-icon': iconOnly }]"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    :aria-label="label"
    :title="iconOnly ? label : undefined"
    @click="!disabled && !loading && emit('click', $event)"
  >
    <span
      v-if="loading"
      class="button-progress"
      aria-hidden="true"
    />
    <span
      class="button-content"
      :class="{ 'button-content-loading': loading }"
    >
      <slot name="start" />
      <slot />
      <slot name="end" />
    </span>
  </button>
</template>

<style scoped>
.ui-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  padding: 10px 16px;
  min-height: 44px;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  transition:
    background-color var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out),
    color var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}
.button-content {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.button-primary {
  background: var(--color-primary);
  color: var(--color-on-primary);
}
.button-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}
.button-secondary {
  border-color: var(--color-border-strong);
  background: transparent;
  color: var(--color-text);
}
.button-ghost {
  background: transparent;
  color: var(--color-text-muted);
}
.button-quiet {
  background: var(--color-surface-subtle);
  color: var(--color-primary);
}
.button-secondary:hover:not(:disabled),
.button-ghost:hover:not(:disabled),
.button-quiet:hover:not(:disabled) {
  background: var(--color-surface-accent);
  color: var(--color-primary);
  border-color: var(--color-secondary);
}
.button-danger {
  border-color: var(--color-border-strong);
  background: transparent;
  color: var(--color-danger);
}
.button-danger:hover:not(:disabled) {
  border-color: var(--color-danger);
  background: color-mix(in srgb, var(--color-danger) 8%, transparent);
}
.button-danger-solid {
  background: var(--color-danger);
  color: var(--color-on-danger);
}
.button-danger-solid:hover:not(:disabled) {
  filter: brightness(0.93);
}
.ui-button:active:not(:disabled) {
  transform: scale(0.98);
}
.ui-button:disabled {
  opacity: 0.48;
  filter: saturate(0.5);
}
.ui-button[aria-busy='true'] {
  opacity: 1;
}
.button-sm {
  padding: 6px 12px;
  min-height: 36px;
  font-size: 13px;
}
.button-lg {
  min-height: 48px;
  padding: 12px 22px;
}
.button-icon {
  width: 44px;
  padding: 0;
}
.button-content-loading {
  opacity: 0;
}
.button-progress {
  position: absolute;
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (pointer: coarse) {
  .button-sm {
    min-height: 44px;
  }
}
</style>
