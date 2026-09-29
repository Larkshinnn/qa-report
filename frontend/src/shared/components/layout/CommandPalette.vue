<script setup lang="ts">
import { computed, nextTick, ref, useId, watch } from 'vue'
import { useRouter } from 'vue-router'
import { PhArrowElbowDownLeft, PhMagnifyingGlass, PhClipboardText } from '@phosphor-icons/vue'
import { commandNavigation, matchesCommand } from '../../navigation'
import type { NavigationItem } from '../../navigation'
import { qaApi } from '../../../modules/qa-reports/api'
import { useUiStore } from '../../stores/ui'
import UiModal from '../ui/UiModal.vue'
const ui = useUiStore()
const router = useRouter()
const query = ref('')
const active = ref(0)
const id = useId()
const recent = ref<NavigationItem[]>([])
const recentError = ref('')
async function loadRecent(): Promise<void> {
  recentError.value = ''
  try {
    const result = await qaApi.list({ page_size: '5' })
    recent.value = result.reports.map((report) => ({
      label: `${report.report_date} · ${report.title}`,
      path: `/qa-reports/${report.id}`,
      icon: PhClipboardText,
      keywords: 'laporan terbaru recent',
    }))
  } catch {
    recent.value = []
    recentError.value = 'Laporan terbaru belum dapat dimuat. Buka QA Reports untuk mencoba kembali.'
  }
}
const matches = computed(() =>
  [...commandNavigation, ...recent.value].filter((item) => matchesCommand(item, query.value)),
)
watch(query, () => {
  active.value = 0
})
watch(
  () => ui.paletteOpen,
  (open) => {
    if (open) {
      query.value = ''
      active.value = 0
      void loadRecent()
    }
  },
)
async function choose(index: number): Promise<void> {
  const item = matches.value[index]
  if (!item) return
  ui.paletteOpen = false
  await router.push(item.path)
}
async function navigate(event: KeyboardEvent): Promise<void> {
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    const offset = event.key === 'ArrowDown' ? 1 : -1
    active.value =
      (active.value + offset + matches.value.length) % Math.max(1, matches.value.length)
    await nextTick()
    document.getElementById(`${id}-${active.value}`)?.scrollIntoView({ block: 'nearest' })
  } else if (event.key === 'Enter') {
    event.preventDefault()
    void choose(active.value)
  }
}
</script>
<template>
  <UiModal
    v-model="ui.paletteOpen"
    title="Pindah ke mana?"
    description="Cari halaman atau lima laporan terbaru. Untuk pencarian tiket, buka QA Reports."
    size="md"
  >
    <div class="command-input">
      <PhMagnifyingGlass
        :size="20"
        aria-hidden="true"
      />
      <input
        v-model="query"
        autofocus
        aria-label="Cari halaman atau alat"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded="true"
        :aria-controls="`${id}-list`"
        :aria-activedescendant="matches.length ? `${id}-${active}` : undefined"
        placeholder="Cari laporan atau tiket…"
        @keydown="navigate"
      />
    </div>
    <ul
      :id="`${id}-list`"
      role="listbox"
      aria-label="Hasil pencarian"
      class="command-list"
    >
      <li
        v-for="(item, index) in matches"
        :id="`${id}-${index}`"
        :key="item.path"
        role="option"
        :aria-selected="index === active"
      >
        <button
          type="button"
          tabindex="-1"
          @click="choose(index)"
          @pointermove="active = index"
        >
          <component
            :is="item.icon"
            :size="20"
          />
          <span>{{ item.label }}</span>
          <PhArrowElbowDownLeft
            v-if="index === active"
            :size="16"
          />
        </button>
      </li>
    </ul>
    <p
      v-if="!matches.length"
      class="no-results"
    >
      Tidak ditemukan. Coba nama alat atau halaman lain.
    </p>
    <div class="command-help">
      <span>
        <kbd>↑</kbd>
        <kbd>↓</kbd>
        navigasi
      </span>
      <span>
        <kbd>Enter</kbd>
        buka
      </span>
      <span>
        <kbd>Esc</kbd>
        tutup
      </span>
    </div>
    <p
      v-if="recentError"
      class="small muted mt-4"
      role="status"
    >
      {{ recentError }}
    </p>
  </UiModal>
</template>
<style scoped>
.command-input {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  color: var(--color-text-muted);
}
.command-input:focus-within {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
.command-input input {
  width: 100%;
  min-width: 0;
  outline: 0;
  background: transparent;
  border: 0;
  color: var(--color-text);
  font-size: 14px;
}
.command-list {
  padding: 0;
  margin: 14px 0;
  list-style: none;
  max-height: 310px;
  overflow-y: auto;
}
.command-list button {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 12px;
  border: 0;
  background: transparent;
  color: var(--color-text);
  min-height: 44px;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 14px;
  text-align: left;
}
.command-list button span {
  flex: 1;
}
.command-list [aria-selected='true'] button {
  background: var(--color-surface-subtle);
  color: var(--color-primary);
}
.command-help {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 12px;
  color: var(--color-text-muted);
  border-top: 1px solid var(--color-border);
  padding-top: 16px;
}
.no-results {
  padding: 20px 0;
  font-size: 14px;
  color: var(--color-text-muted);
}
</style>
