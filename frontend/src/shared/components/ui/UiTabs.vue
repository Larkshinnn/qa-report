<script setup lang="ts">
import { nextTick, useId } from 'vue'
const props = defineProps<{ label: string; tabs: readonly { value: string; label: string }[] }>()
const active = defineModel<string>({ required: true })
const id = useId()
async function move(event: KeyboardEvent, index: number): Promise<void> {
  let target: number
  if (event.key === 'ArrowRight') target = (index + 1) % props.tabs.length
  else if (event.key === 'ArrowLeft') target = (index - 1 + props.tabs.length) % props.tabs.length
  else if (event.key === 'Home') target = 0
  else if (event.key === 'End') target = props.tabs.length - 1
  else return
  event.preventDefault()
  const tab = props.tabs[target]
  if (!tab) return
  active.value = tab.value
  await nextTick()
  document.getElementById(`${id}-${tab.value}`)?.focus()
}
</script>
<template>
  <div class="ui-tabs">
    <div
      role="tablist"
      :aria-label="label"
      class="tab-list"
    >
      <button
        v-for="(tab, index) in tabs"
        :id="`${id}-${tab.value}`"
        :key="tab.value"
        type="button"
        role="tab"
        :aria-selected="active === tab.value"
        :aria-controls="`${id}-panel-${tab.value}`"
        :tabindex="active === tab.value ? 0 : -1"
        @click="active = tab.value"
        @keydown="move($event, index)"
      >
        {{ tab.label }}
      </button>
    </div>
    <section
      v-for="tab in tabs"
      v-show="active === tab.value"
      :id="`${id}-panel-${tab.value}`"
      :key="tab.value"
      role="tabpanel"
      :aria-labelledby="`${id}-${tab.value}`"
      tabindex="0"
      class="tab-panel"
    >
      <slot :name="tab.value" />
    </section>
  </div>
</template>
<style scoped>
.tab-list {
  display: flex;
  gap: 4px;
  overflow-x: auto;
  border-bottom: 1px solid var(--color-border);
}
.tab-list button {
  border: 0;
  border-bottom: 1px solid transparent;
  min-height: 48px;
  padding-inline: 14px;
  background: transparent;
  font-size: 14px;
  white-space: nowrap;
  color: var(--color-text-muted);
}
.tab-list button[aria-selected='true'] {
  color: var(--color-on-primary);
  background: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 600;
}
.tab-panel {
  padding-top: 24px;
}
</style>
