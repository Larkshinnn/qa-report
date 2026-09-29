<script setup lang="ts" generic="T extends object">
import { computed, ref, watch } from 'vue'
import { PhArrowDown, PhArrowUp, PhCaretLeft, PhCaretRight } from '@phosphor-icons/vue'
import UiButton from './UiButton.vue'
import UiSkeleton from './UiSkeleton.vue'
import UiEmptyState from './UiEmptyState.vue'
import UiErrorState from './UiErrorState.vue'
const props = withDefaults(
  defineProps<{
    rows: readonly T[]
    columns: readonly { key: keyof T & string; label: string; sortable?: boolean }[]
    rowKey: keyof T & string
    caption: string
    pageSize?: number
    loading?: boolean
    error?: string
    paginate?: boolean
  }>(),
  { pageSize: 10, loading: false, paginate: true },
)
const emit = defineEmits<{ retry: [] }>()
const page = ref(1)
const sortKey = ref<string>('')
const ascending = ref(true)
const size = computed(() => Math.max(1, Math.floor(props.pageSize)))
const totalPages = computed(() => Math.max(1, Math.ceil(props.rows.length / size.value)))
watch(totalPages, (value) => {
  page.value = Math.min(page.value, value)
})
const ordered = computed(() => {
  if (!sortKey.value) return props.rows
  const key = sortKey.value as keyof T
  return [...props.rows].sort((a, b) => {
    const left = a[key],
      right = b[key]
    const result =
      typeof left === 'number' && typeof right === 'number'
        ? left - right
        : String(left ?? '').localeCompare(String(right ?? ''), 'id', { numeric: true })
    return ascending.value ? result : -result
  })
})
const visibleRows = computed(() =>
  props.paginate
    ? ordered.value.slice((page.value - 1) * size.value, page.value * size.value)
    : ordered.value,
)
function sort(key: string): void {
  ascending.value = sortKey.value === key ? !ascending.value : true
  sortKey.value = key
  page.value = 1
}
</script>
<template>
  <div
    class="data-table"
    :aria-busy="loading || undefined"
  >
    <UiSkeleton
      v-if="loading"
      :lines="4"
    />
    <UiErrorState
      v-else-if="error"
      :message="error"
      retryable
      @retry="emit('retry')"
    />
    <UiEmptyState
      v-else-if="!rows.length"
      title="Belum ada data"
      description="Data akan ditampilkan di sini setelah tersedia."
    />
    <template v-else>
      <div
        class="table-scroll"
        role="region"
        :aria-label="caption"
        tabindex="0"
      >
        <table>
          <caption class="sr-only">
            {{ caption }}
          </caption>
          <thead>
            <tr>
              <th
                v-for="column in columns"
                :key="column.key"
                scope="col"
                :aria-sort="
                  column.sortable
                    ? sortKey === column.key
                      ? ascending
                        ? 'ascending'
                        : 'descending'
                      : 'none'
                    : undefined
                "
              >
                <button
                  v-if="column.sortable"
                  type="button"
                  @click="sort(column.key)"
                >
                  {{ column.label }}
                  <component
                    :is="ascending ? PhArrowUp : PhArrowDown"
                    v-if="sortKey === column.key"
                    :size="13"
                  />
                </button>
                <span v-else>{{ column.label }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in visibleRows"
              :key="String(row[rowKey])"
            >
              <td
                v-for="column in columns"
                :key="column.key"
              >
                <slot
                  :name="`cell-${column.key}`"
                  :row="row"
                  :value="row[column.key]"
                >
                  {{ row[column.key] }}
                </slot>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div
        v-if="paginate"
        class="table-footer"
      >
        <span>
          {{ (page - 1) * size + 1 }}-{{ Math.min(page * size, rows.length) }} dari
          {{ rows.length }}
        </span>
        <div class="cluster">
          <span aria-live="polite">Halaman {{ page }} / {{ totalPages }}</span>
          <UiButton
            variant="ghost"
            icon-only
            label="Halaman sebelumnya"
            :disabled="page === 1"
            @click="page--"
          >
            <PhCaretLeft :size="16" />
          </UiButton>
          <UiButton
            variant="ghost"
            icon-only
            label="Halaman berikutnya"
            :disabled="page === totalPages"
            @click="page++"
          >
            <PhCaretRight :size="16" />
          </UiButton>
        </div>
      </div>
    </template>
  </div>
</template>
<style scoped>
.data-table {
  min-width: 0;
}
.table-scroll {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}
th {
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  background: transparent;
  border-block: 1px solid var(--color-border-strong);
}
th,
td {
  padding: 14px 16px;
  white-space: nowrap;
}
th button {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 28px;
  text-align: left;
  border: none;
  color: inherit;
  background: transparent;
}
tbody tr + tr {
  border-top: 1px solid var(--color-ledger-line);
}
tbody tr:hover {
  background: var(--color-surface-accent);
}
.table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  color: var(--color-text-muted);
  font-size: 13px;
  flex-wrap: wrap;
}
</style>
