<script setup lang="ts">
import { computed, useId } from 'vue'
import { safeCoverageUrl, type ItemInput } from '../api'
import { fieldLabel } from '../templates'
import UiInput from '../../../shared/components/ui/UiInput.vue'
import UiSelect from '../../../shared/components/ui/UiSelect.vue'
import UiTextarea from '../../../shared/components/ui/UiTextarea.vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
const item = defineModel<ItemInput>({ required: true })
const collapsed = defineModel<boolean>('collapsed', { default: false })
const props = defineProps<{
  index: number
  count: number
  busy: boolean
  fields: string[]
  guidanceOptions: readonly string[]
}>()
const summary = computed(() =>
  [
    item.value.activity_code || `Aktivitas ${props.index + 1}`,
    ...(props.fields.includes('environment') ? [item.value.environment] : []),
    ...(props.fields.includes('result')
      ? [item.value.result]
      : props.fields.includes('current_status')
        ? [item.value.current_status]
        : []),
  ]
    .filter(Boolean)
    .join(' · '),
)
function updateCustom(key: string, value: string): void {
  item.value.template_values = { ...item.value.template_values, [key]: value }
}
const emit = defineEmits<{ remove: []; move: [direction: -1 | 1] }>()
const uid = useId()
const environments = ['Dev', 'Staging', 'Prod']
const results = ['Pass', 'Fail', 'In progress', 'Blocked']
function selectEnvironment(value: string): void {
  item.value.environment = value === '__custom' ? '' : value
}
function selectResult(value: string): void {
  item.value.result = value === '__custom' ? '' : value
}
function selectGuidance(value: string): void {
  item.value.pic_guidance = value === '__custom' ? null : value
}
</script>
<template>
  <fieldset
    class="activity-editor"
    :disabled="busy"
  >
    <legend>Aktivitas {{ index + 1 }}</legend>
    <div class="activity-heading">
      <UiButton
        class="activity-toggle"
        variant="ghost"
        :aria-expanded="!collapsed"
        :aria-controls="`${uid}-fields`"
        :label="`${collapsed ? 'Buka' : 'Lipat'} aktivitas ${index + 1}`"
        @click="collapsed = !collapsed"
      >
        <span class="activity-summary">{{ collapsed ? 'Buka' : 'Lipat' }} · {{ summary }}</span>
      </UiButton>
      <div class="qa-actions">
        <UiButton
          variant="ghost"
          size="sm"
          :disabled="index === 0 || busy"
          :label="`Naikkan aktivitas ${index + 1}`"
          @click="emit('move', -1)"
        >
          Naik
        </UiButton>
        <UiButton
          variant="ghost"
          size="sm"
          :disabled="index === count - 1 || busy"
          :label="`Turunkan aktivitas ${index + 1}`"
          @click="emit('move', 1)"
        >
          Turun
        </UiButton>
        <UiButton
          variant="quiet"
          size="sm"
          :disabled="busy"
          :label="`Hapus aktivitas ${index + 1}`"
          @click="emit('remove')"
        >
          Hapus
        </UiButton>
      </div>
    </div>
    <div
      v-show="!collapsed"
      :id="`${uid}-fields`"
      class="qa-form-grid"
    >
      <div
        v-for="field in fields"
        :key="field"
        :class="{
          'activity-long-field': ![
            'activity_code',
            'environment',
            'result',
            'current_status',
          ].includes(field),
        }"
      >
        <UiInput
          v-if="field === 'activity_code'"
          v-model="item.activity_code"
          label="Activity / kode tiket"
          required
          maxlength="100"
          placeholder="AMTSK-166"
        />
        <div
          v-else-if="field === 'environment'"
          class="stack compact-stack"
        >
          <UiSelect
            :model-value="environments.includes(item.environment) ? item.environment : '__custom'"
            label="Environment"
            required
            :options="[
              ...environments.map((value) => ({ value, label: value })),
              { value: '__custom', label: 'Custom' },
            ]"
            @update:model-value="selectEnvironment"
          />
          <UiInput
            v-if="!environments.includes(item.environment)"
            v-model="item.environment"
            label="Nama environment custom"
            required
            maxlength="50"
          />
        </div>
        <div
          v-else-if="field === 'result'"
          class="stack compact-stack"
        >
          <UiSelect
            :model-value="results.includes(item.result) ? item.result : '__custom'"
            label="Result"
            required
            :options="[
              ...results.map((value) => ({ value, label: value })),
              { value: '__custom', label: 'Custom' },
            ]"
            @update:model-value="selectResult"
          />
          <UiInput
            v-if="!results.includes(item.result)"
            v-model="item.result"
            label="Hasil custom"
            required
            maxlength="50"
          />
        </div>
        <UiTextarea
          v-else-if="field === 'current_issue'"
          :model-value="item.current_issue ?? ''"
          label="Current issues"
          maxlength="10000"
          :rows="3"
          hint="Opsional, tanpa mengulang kode tiket. Format Slack: *tebal*, _miring_, `kode`."
          placeholder="Some results from API are stuck in in progress status / Passed on production"
          @update:model-value="item.current_issue = $event"
        />
        <UiInput
          v-else-if="field === 'current_status'"
          :model-value="item.current_status ?? ''"
          label="Current Status"
          maxlength="100"
          :hint="
            fields.includes('result')
              ? 'Kosongkan untuk mengikuti hasil pengujian.'
              : 'Isi kondisi terbaru aktivitas ini. Tidak perlu mengisi Result terpisah.'
          "
          placeholder="Passed prod atau In progress"
          @update:model-value="item.current_status = $event"
        />
        <div
          v-else-if="field === 'coverage_links'"
          class="stack compact-stack"
        >
          <div class="section-heading">
            <h3>Test Coverage</h3>
            <UiButton
              variant="ghost"
              size="sm"
              :disabled="item.links.length >= 50 || busy"
              @click="item.links.push({ url: '', label: null })"
            >
              Tambah link
            </UiButton>
          </div>
          <p
            v-if="!item.links.length"
            class="small muted"
          >
            Belum ada link coverage. Kamu bisa menambahkannya nanti.
          </p>
          <div
            v-for="(link, linkIndex) in item.links"
            :key="`${uid}-${linkIndex}`"
            class="coverage-row"
          >
            <UiInput
              :model-value="link.label ?? ''"
              :label="`Judul link ${linkIndex + 1}`"
              maxlength="255"
              placeholder="Contoh: Test case pembayaran"
              hint="Kosongkan untuk memakai URL sebagai judul."
              @update:model-value="link.label = $event || null"
            />
            <UiInput
              v-model="link.url"
              :label="`URL coverage ${linkIndex + 1}`"
              maxlength="4096"
              placeholder="https://…"
              :hint="
                link.url && !safeCoverageUrl(link.url)
                  ? 'URL belum valid. Tetap tersimpan sebagai teks, tidak sebagai tautan aktif.'
                  : undefined
              "
            />
            <UiButton
              variant="ghost"
              size="sm"
              :label="`Hapus link ${linkIndex + 1} dari aktivitas ${index + 1}`"
              :disabled="busy"
              @click="item.links.splice(linkIndex, 1)"
            >
              Hapus link
            </UiButton>
          </div>
        </div>
        <UiTextarea
          v-else
          :model-value="item.template_values?.[field] ?? ''"
          :label="fieldLabel(field)"
          :rows="3"
          maxlength="10000"
          hint="Isian untuk aktivitas ini."
          @update:model-value="updateCustom(field, $event)"
        />
      </div>
      <section class="manmonth-fields activity-long-field">
        <div>
          <h3>Detail manmonth</h3>
          <p class="small muted">Semua field opsional dan tidak muncul di daily report.</p>
        </div>
        <div class="qa-form-grid">
          <UiInput
            :model-value="item.duration_hours?.toString() ?? ''"
            label="Durasi pengerjaan (jam)"
            type="number"
            min="0"
            step="0.25"
            hint="Contoh: 1.5"
            @update:model-value="item.duration_hours = $event === '' ? null : Number($event)"
          />
          <UiTextarea
            :model-value="item.obstacle ?? ''"
            label="Obstacle (manmonth)"
            :rows="3"
            maxlength="10000"
            @update:model-value="item.obstacle = $event || null"
          />
          <UiTextarea
            :model-value="item.next_step ?? ''"
            label="Next Step / Action (manmonth)"
            :rows="3"
            maxlength="10000"
            @update:model-value="item.next_step = $event || null"
          />
          <div class="stack compact-stack">
            <UiSelect
              :model-value="
                props.guidanceOptions.includes(item.pic_guidance ?? '')
                  ? (item.pic_guidance ?? '')
                  : '__custom'
              "
              label="PIC / Guidance (manmonth)"
              :options="[
                ...props.guidanceOptions.map((value) => ({ value, label: value })),
                { value: '__custom', label: 'Custom' },
              ]"
              @update:model-value="selectGuidance"
            />
            <UiInput
              v-if="!props.guidanceOptions.includes(item.pic_guidance ?? '')"
              :model-value="item.pic_guidance ?? ''"
              label="PIC / Guidance custom"
              maxlength="10000"
              @update:model-value="item.pic_guidance = $event || null"
            />
          </div>
          <UiTextarea
            :model-value="item.deliverable ?? ''"
            label="Deliverable (manmonth)"
            :rows="3"
            maxlength="10000"
            @update:model-value="item.deliverable = $event || null"
          />
        </div>
      </section>
    </div>
  </fieldset>
</template>
<style scoped>
.activity-editor {
  border: 0;
  border-top: 1px solid var(--color-border);
  padding: 24px 0 0;
  min-width: 0;
  display: grid;
  gap: 20px;
}
legend {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-primary);
  padding-right: 16px;
}
.activity-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.compact-stack {
  gap: 12px;
}
.activity-long-field {
  grid-column: 1 / -1;
}
.manmonth-fields {
  display: grid;
  gap: 16px;
  padding-top: 20px;
  border-top: 1px solid var(--color-border);
}
.manmonth-fields h3 {
  font-size: 14px;
}
.activity-toggle {
  min-width: 0;
  max-width: 100%;
}
.activity-toggle :deep(.button-content) {
  min-width: 0;
}
.activity-summary {
  white-space: normal;
  overflow-wrap: anywhere;
  text-align: left;
}
.coverage-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr)) auto;
  gap: 12px;
  align-items: start;
}
.coverage-row > :last-child {
  margin-top: 25px;
}
.section-heading {
  margin: 0;
}
.section-heading h3 {
  font-size: 14px;
}
@media (max-width: 767px) {
  .coverage-row {
    grid-template-columns: minmax(0, 1fr);
  }
  .coverage-row > :last-child {
    margin: 0;
    justify-self: start;
  }
}
</style>
