<script setup lang="ts">
defineProps<{ id: string; label: string; hint?: string; error?: string; required?: boolean }>()
</script>
<template>
  <div class="field">
    <label
      :for="id"
      class="field-label"
    >
      {{ label }}
      <span
        v-if="required"
        aria-hidden="true"
      >
        *
      </span>
    </label>
    <slot />
    <p
      v-if="error"
      :id="`${id}-description`"
      class="field-error"
      role="alert"
    >
      {{ error }}
    </p>
    <p
      v-else-if="hint"
      :id="`${id}-description`"
      class="field-hint"
    >
      {{ hint }}
    </p>
  </div>
</template>
