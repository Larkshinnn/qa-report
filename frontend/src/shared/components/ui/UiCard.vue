<script setup lang="ts">
withDefaults(
  defineProps<{
    tone?: 'default' | 'subtle' | 'outlined'
    padding?: 'none' | 'sm' | 'md' | 'lg'
    interactive?: boolean
    as?: 'section' | 'article' | 'div'
    elevated?: boolean
  }>(),
  { tone: 'default', padding: 'md', as: 'section', interactive: false, elevated: false },
)
</script>

<template>
  <component
    :is="interactive ? 'button' : as"
    :type="interactive ? 'button' : undefined"
    :class="[
      'ui-card',
      `card-${tone}`,
      `card-padding-${padding}`,
      { 'card-interactive': interactive, 'card-elevated': elevated },
    ]"
  >
    <div
      v-if="$slots.header"
      class="card-header"
    >
      <slot name="header" />
    </div>
    <slot />
    <div
      v-if="$slots.footer"
      class="card-footer"
    >
      <slot name="footer" />
    </div>
  </component>
</template>

<style scoped>
.ui-card {
  display: block;
  min-width: 0;
  text-align: left;
  background: var(--color-surface);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-panel);
  color: var(--color-text);
}
.card-subtle {
  background: var(--color-surface-subtle);
  border-color: var(--color-border);
}
.card-outlined {
  background: transparent;
}
.card-padding-sm {
  padding: 16px;
}
.card-padding-md {
  padding: 24px;
}
.card-padding-lg {
  padding: 32px;
}
.card-header {
  margin-bottom: 20px;
}
.card-footer {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--color-border);
}
.card-elevated {
  box-shadow: var(--shadow-floating);
}
.card-interactive {
  width: 100%;
  transition:
    border-color var(--duration-fast) var(--ease-out),
    background-color var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}
.card-interactive:hover {
  border-color: var(--color-primary);
  background: var(--color-surface-accent);
  transform: translateY(-2px);
}
@media (max-width: 767px) {
  .card-padding-lg,
  .card-padding-md {
    padding: 20px;
  }
}
</style>
