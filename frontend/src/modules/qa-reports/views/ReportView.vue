<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { ApiError, downloadFile, errorMessage } from '../../../shared/api'
import { useAuthStore } from '../../../shared/stores/auth'
import { useToast } from '../../../shared/composables/useToast'
import {
  qaApi,
  localDate,
  yesterday,
  type ItemInput,
  type Report,
  type ReportSave,
  type ReportPreview as Preview,
  type ReportTemplate,
} from '../api'
import ActivityEditor from '../components/ActivityEditor.vue'
import ReportPreview from '../components/ReportPreview.vue'
import DeleteReportButton from '../components/DeleteReportButton.vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiBreadcrumbs from '../../../shared/components/ui/UiBreadcrumbs.vue'
import UiCard from '../../../shared/components/ui/UiCard.vue'
import UiInput from '../../../shared/components/ui/UiInput.vue'
import UiSelect from '../../../shared/components/ui/UiSelect.vue'
import UiTextarea from '../../../shared/components/ui/UiTextarea.vue'
import {
  customKeys,
  templateFields as getTemplateFields,
  fieldLabel,
  renderTemplate,
  rememberedTemplate,
  rememberTemplate,
  starterBody,
} from '../templates'
import UiSkeleton from '../../../shared/components/ui/UiSkeleton.vue'
import UiEmptyState from '../../../shared/components/ui/UiEmptyState.vue'
import UiErrorState from '../../../shared/components/ui/UiErrorState.vue'
import UiConfirmDialog from '../../../shared/components/ui/UiConfirmDialog.vue'
import '../styles.css'

interface EditableItem extends ItemInput {
  key: number
  collapsed: boolean
}
const route = useRoute(),
  router = useRouter(),
  auth = useAuthStore()
const { notify } = useToast()
const report = ref<Report>()
const title = ref(''),
  reportDate = ref(''),
  author = ref('')
const templates = ref<ReportTemplate[]>([])
const selectedTemplateId = ref('')
const templateValues = ref<Record<string, string>>({})
const templateError = ref('')
const templateBody = computed(() =>
  selectedTemplateId.value === '__saved'
    ? (report.value?.template_body ?? '')
    : (templates.value.find((template) => template.id === selectedTemplateId.value)?.body ?? ''),
)
const fields = computed(() => getTemplateFields(templateBody.value || starterBody))
const templateFields = computed(() => fields.value.report)
const activityCustomFields = computed(() => {
  const custom = new Set(customKeys(templateBody.value))
  return fields.value.activity.filter((key) => custom.has(key))
})
const templateOptions = computed(() => [
  { value: '', label: 'Format standar QA' },
  ...(report.value?.template_body
    ? [{ value: '__saved', label: `${report.value.template_name} · format tersimpan` }]
    : []),
  ...templates.value.map((template) => ({ value: template.id, label: template.name })),
])
const items = ref<EditableItem[]>([])
const baseline = ref('')
const ready = ref(false),
  editing = ref(true),
  loading = ref(true),
  busy = ref(false)
const error = ref(''),
  existingId = ref('')
const preview = ref<Preview>(),
  previewError = ref(''),
  previewLoading = ref(false)
const guidanceOptionDraft = ref('')
const guidanceOptions = ref<string[]>([])
const editor = ref<HTMLFormElement>()
const step = ref(1)
const stepHeading = ref<HTMLElement>()
const pageHeading = ref<HTMLElement>()
const steps = computed(() => [
  'Identitas laporan',
  ...(fields.value.hasActivities ? ['Isian per aktivitas'] : []),
])
const lastStep = computed(() => step.value === steps.value.length)
const showActivities = computed(() => fields.value.hasActivities && step.value === 2)
const nextLabel = computed(() => (lastStep.value ? 'Simpan laporan' : 'Lanjut ke aktivitas'))
const removeIndex = ref<number>(),
  removeOpen = ref(false),
  discardOpen = ref(false)
let resolveDiscard: ((result: boolean) => void) | undefined
let key = 0,
  loadId = 0,
  previewId = 0
const payload = computed<ReportSave>(() => ({
  title: title.value,
  report_date: reportDate.value,
  author_name: author.value || null,
  ...(selectedTemplateId.value === '__saved'
    ? {}
    : selectedTemplateId.value || report.value?.template_body
      ? { template_id: selectedTemplateId.value || null }
      : {}),
  ...(templateBody.value
    ? {
        template_values: Object.fromEntries(
          templateFields.value.map((key) => [key, templateValues.value[key] ?? '']),
        ),
      }
    : {}),
  version: report.value?.version ?? 1,
  items: (templateBody.value && !fields.value.hasActivities && !report.value
    ? []
    : items.value
  ).map((item) => ({
    id: item.id,
    activity_code: item.activity_code,
    environment:
      templateBody.value && !fields.value.activity.includes('environment') && !item.id
        ? ''
        : item.environment,
    result:
      templateBody.value && !fields.value.activity.includes('result') && !item.id
        ? ''
        : item.result,
    current_status: item.current_status || null,
    current_issue: item.current_issue || null,
    ...(item.duration_hours == null ? {} : { duration_hours: item.duration_hours }),
    ...(item.obstacle ? { obstacle: item.obstacle } : {}),
    ...(item.next_step ? { next_step: item.next_step } : {}),
    ...(item.pic_guidance ? { pic_guidance: item.pic_guidance } : {}),
    ...(item.deliverable ? { deliverable: item.deliverable } : {}),
    ...(templateBody.value || Object.keys(item.template_values ?? {}).length
      ? {
          template_values: Object.fromEntries(
            activityCustomFields.value.map((key) => [key, item.template_values?.[key] ?? '']),
          ),
        }
      : {}),
    links: item.links
      .filter((link) => link.url.trim())
      .map((link) => ({ url: link.url, label: link.label || null })),
  })),
}))
const livePreview = computed(() => {
  if (!templateBody.value) return ''
  try {
    return renderTemplate(
      templateBody.value,
      payload.value,
      payload.value.items,
      payload.value.template_values,
    )
  } catch (cause) {
    return errorMessage(cause)
  }
})
const dirty = computed(() => ready.value && JSON.stringify(payload.value) !== baseline.value)
const duplicates = computed(() => {
  const codes = items.value.map((item) => item.activity_code.trim()).filter(Boolean)
  return codes.length - new Set(codes).size
})
const guidanceStorageKey = 'qa-report-pic-guidance-options'
const existingGuidanceOptions = computed(() => [
  ...new Set(
    items.value
      .map((item) => item.pic_guidance?.trim() ?? '')
      .filter((value) => value && !guidanceOptions.value.includes(value)),
  ),
])
const activityGuidanceOptions = computed(() => [
  ...guidanceOptions.value,
  ...existingGuidanceOptions.value,
])
function loadGuidanceOptions(): string[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(guidanceStorageKey) ?? 'null')
    return Array.isArray(value)
      ? [
          ...new Set(
            value
              .filter((item): item is string => typeof item === 'string')
              .map((item) => item.trim())
              .filter(Boolean),
          ),
        ]
      : []
  } catch {
    return []
  }
}
function saveGuidanceOptions(): void {
  try {
    localStorage.setItem(guidanceStorageKey, JSON.stringify(guidanceOptions.value))
  } catch {
    /* Preference storage is optional. */
  }
}
function addGuidanceOption(): void {
  const value = guidanceOptionDraft.value.trim()
  if (!value || activityGuidanceOptions.value.includes(value)) return
  guidanceOptions.value = [...guidanceOptions.value, value]
  guidanceOptionDraft.value = ''
  saveGuidanceOptions()
}
function removeGuidanceOption(value: string): void {
  guidanceOptions.value = guidanceOptions.value.filter((option) => option !== value)
  saveGuidanceOptions()
}
function blankItem(): EditableItem {
  return {
    key: ++key,
    collapsed: false,
    activity_code: '',
    environment: 'Dev',
    result: 'In progress',
    current_status: null,
    current_issue: null,
    duration_hours: null,
    obstacle: null,
    next_step: null,
    pic_guidance: null,
    deliverable: null,
    template_values: {},
    links: [{ url: '', label: null }],
  }
}
function setReport(value: Report): void {
  report.value = value
  title.value = value.title
  reportDate.value = value.report_date
  author.value = value.author_name ?? ''
  selectedTemplateId.value = value.template_body ? '__saved' : ''
  templateValues.value = { ...value.template_values }
  items.value = value.items.map((item) => ({
    ...item,
    template_values: {
      ...Object.fromEntries(
        activityCustomFields.value.map((key) => [key, value.template_values?.[key] ?? '']),
      ),
      ...item.template_values,
    },
    links: item.links.map((link) => ({ ...link })),
    key: ++key,
    collapsed: value.items.length > 1,
  }))
  if (
    !items.value.length &&
    value.status === 'draft' &&
    (!templateBody.value || fields.value.hasActivities)
  )
    items.value = [blankItem()]
  baseline.value = JSON.stringify(payload.value)
}
function updateAuthor(value: string): void {
  if (title.value === `${author.value} Daily QA Report` || !title.value)
    title.value = `${value} Daily QA Report`
  author.value = value
}
async function loadPreview(): Promise<Preview | undefined> {
  if (!report.value || (!report.value.items.length && !report.value.template_body)) return
  const current = ++previewId
  const id = report.value.id,
    version = report.value.version
  previewLoading.value = true
  previewError.value = ''
  try {
    const value = await qaApi.preview(id)
    if (current === previewId && report.value?.id === id && report.value.version === version) {
      preview.value = value
      return value
    }
  } catch (cause) {
    if (current === previewId) previewError.value = errorMessage(cause)
  } finally {
    if (current === previewId) previewLoading.value = false
  }
}
async function loadTemplates(): Promise<void> {
  templateError.value = ''
  try {
    templates.value = await qaApi.listTemplates()
  } catch (cause) {
    templateError.value = `Template belum dapat dimuat. ${errorMessage(cause)}`
    templates.value = []
  }
}
async function load(): Promise<void> {
  const current = ++loadId
  ++previewId
  previewLoading.value = false
  loading.value = true
  ready.value = false
  step.value = 1
  error.value = ''
  existingId.value = ''
  preview.value = undefined
  previewError.value = ''
  guidanceOptionDraft.value = ''
  guidanceOptions.value = loadGuidanceOptions()
  try {
    const [value] = await Promise.all([
      route.params.id ? qaApi.get(String(route.params.id)) : Promise.resolve(undefined),
      loadTemplates(),
    ])
    if (current !== loadId) return
    if (value) {
      setReport(value)
      editing.value = value.status === 'draft' && (!route.params.id || route.query.edit === '1')
    } else {
      report.value = undefined
      author.value = auth.displayName
      title.value = `${auth.displayName} Daily QA Report`
      reportDate.value = localDate()
      selectedTemplateId.value =
        typeof route.query.template === 'string'
          ? route.query.template
          : templates.value.some((template) => template.id === rememberedTemplate())
            ? rememberedTemplate()
            : ''
      templateValues.value = {}
      items.value = [blankItem()]
      editing.value = true
      baseline.value = JSON.stringify(payload.value)
    }
    ready.value = true
    await loadPreview()
  } catch (cause) {
    if (current === loadId) error.value = errorMessage(cause)
  } finally {
    if (current === loadId) loading.value = false
  }
}
async function validateStep(): Promise<boolean> {
  if (!editor.value) return false
  if (selectedTemplateId.value && selectedTemplateId.value !== '__saved' && !templateBody.value) {
    error.value =
      'Template pilihan tidak tersedia. Pilih format lain atau coba muat ulang template.'
    return false
  }
  const invalid = [
    ...editor.value.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(
      'input, select, textarea',
    ),
  ].find((control) => control.willValidate && !control.validity.valid)
  if (invalid) {
    const groups = [...editor.value.querySelectorAll('fieldset.activity-editor')]
    const index = groups.indexOf(invalid.closest('fieldset.activity-editor')!)
    if (items.value[index]) items.value[index].collapsed = false
    await nextTick()
    invalid.reportValidity()
    return false
  }
  if (showActivities.value && !items.value.length) {
    error.value = 'Tambahkan minimal satu aktivitas sebelum menyimpan.'
    return false
  }
  return true
}
async function changeStep(value: number): Promise<void> {
  if (busy.value) return
  step.value = value
  expandAll(true)
  await nextTick()
  stepHeading.value?.focus()
}
async function submitStep(): Promise<void> {
  const current = step.value
  if (busy.value || !(await validateStep()) || busy.value || step.value !== current) return
  if (!lastStep.value) await changeStep(step.value + 1)
  else await save()
}
async function startEditing(): Promise<void> {
  editing.value = true
  await changeStep(1)
}
async function save(exportAfter = false): Promise<void> {
  if (busy.value || !lastStep.value || !(await validateStep()) || busy.value) return
  busy.value = true
  error.value = ''
  existingId.value = ''
  preview.value = undefined
  try {
    const { version, ...draft } = payload.value
    const templateChoice = selectedTemplateId.value
    setReport(
      report.value
        ? await qaApi.save(report.value.id, { ...draft, version })
        : await qaApi.create(draft),
    )
    if (templateChoice !== '__saved') rememberTemplate(templateChoice)
    notify('Laporan tersimpan.')
    editing.value = false
    const savedPreview = await loadPreview()
    if (exportAfter && savedPreview && report.value) {
      downloadFile(
        new Blob([savedPreview.slack_mrkdwn], { type: 'text/markdown;charset=utf-8' }),
        `qa-report-${report.value.report_date}-slack.md`,
      )
    }
  } catch (cause) {
    error.value = errorMessage(cause)
    if (cause instanceof ApiError) existingId.value = cause.existingId ?? ''
  } finally {
    busy.value = false
  }
  if (!error.value && report.value) {
    await router.replace(`/qa-reports/${report.value.id}`)
    await nextTick()
    pageHeading.value?.focus()
  }
}
async function addItem(): Promise<void> {
  expandAll(false)
  items.value.push(blankItem())
  await nextTick()
  editor.value
    ?.querySelectorAll<HTMLElement>('fieldset.activity-editor')
    .item(items.value.length - 1)
    ?.querySelector<HTMLInputElement>('input')
    ?.focus()
}
function requestRemove(index: number): void {
  removeIndex.value = index
  removeOpen.value = true
}
function removeItem(): void {
  if (removeIndex.value !== undefined) items.value.splice(removeIndex.value, 1)
  removeOpen.value = false
}
function move(index: number, direction: -1 | 1): void {
  const item = items.value.splice(index, 1)[0]
  if (item) items.value.splice(index + direction, 0, item)
}
function expandAll(expanded: boolean): void {
  items.value.forEach((item) => {
    item.collapsed = !expanded
  })
}
async function deleted(): Promise<void> {
  baseline.value = JSON.stringify(payload.value)
  notify('Laporan dihapus permanen.')
  await router.push('/qa-reports')
}
async function copyYesterday(): Promise<void> {
  busy.value = true
  error.value = ''
  try {
    const date = yesterday(reportDate.value)
    const previous = (await qaApi.list({ start: date, end: date })).reports[0]
    if (!previous) {
      error.value = `Tidak ada laporan pada ${date}.`
      return
    }
    const source = await qaApi.get(previous.id)
    if (!source.items.length) {
      error.value = 'Laporan kemarin belum memiliki aktivitas.'
      return
    }
    const empty =
      items.value.length === 1 &&
      !items.value[0]?.activity_code &&
      !items.value[0]?.current_issue &&
      !items.value[0]?.current_status &&
      !Object.values(items.value[0]?.template_values ?? {}).some(Boolean) &&
      !items.value[0]?.links.some((link) => link.url)
    if (items.value.length + source.items.length - Number(empty) > 500) {
      error.value = 'Maksimal 500 aktivitas per laporan.'
      return
    }
    if (empty) items.value = []
    items.value.push(
      ...source.items.map((item) => ({
        ...item,
        id: undefined,
        key: ++key,
        collapsed: true,
        template_values: {
          ...Object.fromEntries(
            activityCustomFields.value.map((key) => [key, source.template_values?.[key] ?? '']),
          ),
          ...item.template_values,
        },
        links: item.links.map((link) => ({ ...link })),
      })),
    )
    notify('Aktivitas kemarin disalin. Periksa isinya, lalu simpan.')
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}
function confirmDiscard(): Promise<boolean> {
  if (busy.value) return Promise.resolve(false)
  if (!dirty.value) return Promise.resolve(true)
  discardOpen.value = true
  return new Promise((resolve) => {
    resolveDiscard = resolve
  })
}
function discard(): void {
  resolveDiscard?.(true)
  resolveDiscard = undefined
  discardOpen.value = false
}
watch(discardOpen, (value) => {
  if (!value && resolveDiscard) {
    resolveDiscard(false)
    resolveDiscard = undefined
  }
})
function unload(event: BeforeUnloadEvent): void {
  if (dirty.value) {
    event.preventDefault()
    event.returnValue = ''
  }
}
onBeforeRouteLeave(confirmDiscard)
onBeforeRouteUpdate(confirmDiscard)
watch(
  () => route.path,
  () => {
    // Save already populated this report; changing its URL must not reload and overwrite new input.
    if (ready.value && report.value && report.value.id === route.params.id) return
    void load()
  },
)
onMounted(() => {
  void load()
  window.addEventListener('beforeunload', unload)
})
onUnmounted(() => window.removeEventListener('beforeunload', unload))
</script>
<template>
  <UiBreadcrumbs
    :items="[
      { label: 'Laporan', to: '/qa-reports' },
      { label: report?.title ?? (route.params.id ? 'Detail laporan' : 'Laporan baru') },
    ]"
  />
  <div class="page-header">
    <div>
      <h1
        ref="pageHeading"
        tabindex="-1"
      >
        {{ report?.title ?? 'Laporan QA baru' }}
      </h1>
      <p>
        {{
          editing
            ? 'Lengkapi isian laporan sesuai template pilihanmu.'
            : 'Laporan tersimpan. Salin, ekspor, atau edit kembali bila perlu.'
        }}
      </p>
    </div>
    <div class="qa-actions">
      <UiButton
        v-if="report"
        variant="secondary"
        :disabled="busy"
        @click="router.push('/qa-reports/new')"
      >
        Laporan tanggal lain
      </UiButton>
      <UiButton
        variant="secondary"
        :disabled="busy"
        @click="router.push('/qa-reports')"
      >
        Kembali ke daftar laporan
      </UiButton>
      <DeleteReportButton
        v-if="report"
        :report-id="report.id"
        :report-title="report.title"
        :report="report"
        :disabled="busy"
        @deleted="deleted"
      />
    </div>
  </div>
  <UiSkeleton
    v-if="loading"
    :lines="6"
  />
  <UiErrorState
    v-else-if="!ready"
    :message="error || 'Laporan belum dapat dimuat.'"
    retryable
    @retry="load"
  />
  <div
    v-else
    class="daily-workspace"
    :class="{ 'report-readonly': !editing }"
  >
    <div class="stack">
      <UiErrorState
        v-if="error && !editing"
        :message="error"
      />
      <p
        v-if="report"
        class="small muted"
      >
        {{ report.report_date }} · {{ report.items.length }} aktivitas tersimpan
      </p>
      <p
        v-if="report && report.status !== 'draft'"
        class="qa-notice"
      >
        Laporan lama ini sudah dikunci. Isinya tetap bisa disalin dan diekspor.
      </p>
      <UiButton
        v-if="!editing && report?.status === 'draft'"
        variant="secondary"
        :disabled="busy"
        @click="startEditing"
      >
        Edit laporan
      </UiButton>
      <form
        v-if="editing"
        ref="editor"
        class="stack"
        novalidate
        @submit.prevent="submitStep"
      >
        <ol
          class="report-steps"
          aria-label="Tahapan laporan"
        >
          <li
            v-for="(label, index) in steps"
            :key="label"
            :aria-current="step === index + 1 ? 'step' : undefined"
            :class="{ active: step === index + 1, complete: step > index + 1 }"
          >
            <span class="step-number">{{ index + 1 }}</span>
            <span>
              {{ label }}
              <span
                v-if="step > index + 1"
                class="sr-only"
              >
                , sudah diisi
              </span>
            </span>
          </li>
        </ol>
        <div>
          <h2
            ref="stepHeading"
            tabindex="-1"
          >
            {{ step }}. {{ steps[step - 1] }}
          </h2>
          <p class="small muted step-hint">
            {{
              step === 1
                ? 'Pilih format, lalu lengkapi judul, tanggal, dan identitas laporan.'
                : 'Isi setiap aktivitas sesuai urutan placeholder di template. Kolom yang tidak dipakai tidak ditampilkan.'
            }}
          </p>
          <p
            v-if="step > 1"
            class="small muted step-hint"
          >
            {{ reportDate }} · {{ items.length }} aktivitas · {{ title }}
          </p>
        </div>
        <UiCard
          v-if="step === 1"
          padding="md"
        >
          <fieldset
            class="metadata"
            :disabled="busy"
          >
            <legend>Identitas laporan</legend>
            <div class="qa-form-grid">
              <UiInput
                v-if="!templateBody || templateBody.includes('author_name')"
                :model-value="author"
                label="Nama pelapor"
                placeholder="Gideon"
                maxlength="200"
                @update:model-value="updateAuthor"
              />
              <UiInput
                v-model="reportDate"
                label="Tanggal laporan"
                type="date"
                required
                min="1900-01-01"
                max="2100-12-31"
              />
              <div class="report-title">
                <UiInput
                  v-model="title"
                  label="Judul laporan"
                  required
                  maxlength="255"
                />
              </div>
              <div class="report-title template-picker">
                <UiSelect
                  v-model="selectedTemplateId"
                  label="Format laporan"
                  hint="Kolom dan tahapan pengisian otomatis mengikuti template pilihanmu."
                  :options="templateOptions"
                />
                <UiErrorState
                  v-if="templateError"
                  :message="templateError"
                  retryable
                  @retry="loadTemplates"
                />
                <RouterLink
                  to="/qa-reports/templates"
                  class="qa-link small"
                >
                  Kelola template
                </RouterLink>
              </div>
            </div>
          </fieldset>
        </UiCard>
        <UiCard
          v-if="step === 1 && templateFields.length"
          tone="subtle"
        >
          <fieldset
            class="metadata stack"
            :disabled="busy"
          >
            <legend>Isian template</legend>
            <p class="small muted">
              Cukup isi sekali untuk seluruh laporan. Kolom yang tidak dibutuhkan boleh dikosongkan.
            </p>
            <UiTextarea
              v-for="field in templateFields"
              :key="field"
              :model-value="templateValues[field] ?? ''"
              :label="fieldLabel(field)"
              :rows="2"
              maxlength="10000"
              hint="Tab untuk indentasi list Slack; Shift+Tab mengurangi indentasi."
              tab-indent
              @update:model-value="templateValues[field] = $event"
            />
          </fieldset>
        </UiCard>
        <section
          v-if="showActivities"
          class="stack"
        >
          <div class="qa-actions">
            <UiButton
              variant="ghost"
              :disabled="busy"
              @click="expandAll(true)"
            >
              Buka semua aktivitas
            </UiButton>
            <UiButton
              variant="ghost"
              :disabled="busy"
              @click="expandAll(false)"
            >
              Lipat semua aktivitas
            </UiButton>
          </div>
          <p
            v-if="duplicates"
            class="qa-notice"
          >
            {{ duplicates }} entri menggunakan kode yang sama. Semua tetap disimpan sebagai
            pengujian terpisah.
          </p>
          <div class="guidance-settings stack">
            <div>
              <h3>Opsi PIC / Guidance</h3>
              <p class="small muted">
                Tambahkan pilihan yang akan muncul di dropdown setiap activity. Nilai yang sudah
                dipakai tetap tersedia otomatis.
              </p>
            </div>
            <div class="qa-form-grid guidance-option-form">
              <UiInput
                v-model="guidanceOptionDraft"
                label="Tambah opsi PIC / Guidance"
                maxlength="10000"
                placeholder="Nama PIC atau guidance"
                @keydown.enter.prevent="addGuidanceOption"
              />
              <div class="guidance-option-submit">
                <UiButton
                  variant="secondary"
                  :disabled="busy || !guidanceOptionDraft.trim()"
                  @click="addGuidanceOption"
                >
                  Tambah opsi
                </UiButton>
              </div>
            </div>
            <div
              v-if="guidanceOptions.length"
              class="qa-actions"
              aria-label="Opsi PIC / Guidance yang disimpan"
            >
              <span
                v-for="option in guidanceOptions"
                :key="option"
                class="guidance-option"
              >
                <span>{{ option }}</span>
                <UiButton
                  variant="ghost"
                  size="sm"
                  :disabled="busy"
                  :label="`Hapus opsi ${option}`"
                  @click="removeGuidanceOption(option)"
                >
                  Hapus
                </UiButton>
              </span>
            </div>
            <p
              v-if="existingGuidanceOptions.length"
              class="small muted"
            >
              Nilai yang sudah ada di activity: {{ existingGuidanceOptions.join(', ') }}
            </p>
          </div>
          <ActivityEditor
            v-for="(item, index) in items"
            :key="item.key"
            v-model="items[index]!"
            v-model:collapsed="items[index]!.collapsed"
            :index="index"
            :count="items.length"
            :busy="busy"
            :fields="fields.activity"
            :guidance-options="activityGuidanceOptions"
            @remove="requestRemove(index)"
            @move="move(index, $event)"
          />
          <div class="qa-actions">
            <UiButton
              variant="secondary"
              :disabled="busy || items.length >= 500"
              @click="addItem"
            >
              Tambah aktivitas
            </UiButton>
            <UiButton
              variant="ghost"
              :disabled="busy"
              @click="copyYesterday"
            >
              Salin dari kemarin
            </UiButton>
          </div>
        </section>
        <UiErrorState
          v-if="error"
          :message="error"
        />
        <RouterLink
          v-if="existingId"
          :to="`/qa-reports/${existingId}?edit=1`"
          class="qa-link"
        >
          Buka laporan yang sudah ada pada tanggal ini
        </RouterLink>
        <details
          v-if="lastStep && templateBody"
          class="template-live-preview"
          open
        >
          <summary>Periksa hasil laporan</summary>
          <pre class="template-preview">{{ livePreview }}</pre>
        </details>
        <div class="save-bar">
          <span
            class="small"
            role="status"
          >
            {{
              dirty
                ? 'Ada isian belum disimpan'
                : report
                  ? 'Laporan tersimpan'
                  : 'Belum disimpan ke database'
            }}
          </span>
          <p
            v-if="!lastStep"
            class="small muted"
          >
            Lanjut tidak menyimpan ke database. Semua isian disimpan bersama pada langkah
            {{ steps.length }}.
          </p>
          <div class="qa-actions">
            <UiButton
              v-if="step > 1"
              variant="secondary"
              :disabled="busy"
              @click="changeStep(step - 1)"
            >
              Kembali ke {{ steps[step - 2] }}
            </UiButton>
            <UiButton
              type="submit"
              :loading="busy"
            >
              {{ nextLabel }}
            </UiButton>
            <UiButton
              v-if="lastStep"
              variant="secondary"
              :disabled="busy"
              @click="save(true)"
            >
              Simpan &amp; ekspor Slack .md
            </UiButton>
          </div>
        </div>
      </form>
    </div>
    <aside
      v-if="!editing"
      class="report-output"
      aria-label="Hasil laporan harian"
    >
      <UiCard tone="subtle">
        <div class="stack">
          <div>
            <h2>Laporan tersimpan</h2>
            <p class="muted small mt-2">
              {{
                report?.template_name
                  ? `Format: ${report.template_name}`
                  : 'Testing Summary → Test Coverage → Current issues → Current Status'
              }}
            </p>
          </div>
          <UiSkeleton
            v-if="previewLoading"
            :lines="5"
          />
          <UiErrorState
            v-else-if="previewError"
            :message="`Laporan sudah tersimpan, tetapi preview gagal dimuat. ${previewError}`"
            retryable
            @retry="loadPreview"
          />
          <ReportPreview
            v-else-if="preview && report && !dirty"
            :preview="preview"
            :report="report"
          />
          <UiEmptyState
            v-else
            :title="dirty ? 'Simpan untuk melihat hasil terbaru' : 'Laporanmu akan tampil di sini'"
            description="Lengkapi form, lalu pilih Simpan laporan. Kamu bisa mengunduh hasilnya tanpa pengaturan tambahan."
            compact
          />
        </div>
      </UiCard>
    </aside>
  </div>
  <UiConfirmDialog
    v-model="removeOpen"
    title="Hapus aktivitas ini?"
    description="Aktivitas dikeluarkan dari form. Penghapusan menjadi permanen setelah laporan disimpan."
    confirm-label="Hapus dari form"
    @confirm="removeItem"
  />
  <UiConfirmDialog
    v-model="discardOpen"
    title="Tinggalkan perubahan?"
    description="Isian yang belum disimpan akan hilang. Laporan yang sudah tersimpan tidak berubah."
    confirm-label="Buang perubahan"
    @confirm="discard"
  />
</template>
<style scoped>
.daily-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  max-width: 960px;
  gap: 32px;
  align-items: start;
}
.daily-workspace > * {
  min-width: 0;
}
.report-readonly {
  grid-template-columns: minmax(0, 1fr);
  max-width: 900px;
}
.report-readonly .report-output {
  position: static;
}
.metadata {
  border: 0;
  padding: 0;
  min-width: 0;
}
.metadata legend {
  font-weight: 500;
  margin-bottom: 20px;
}
.report-title {
  grid-column: 1 / -1;
}
.report-output :deep(pre) {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  max-height: 65vh;
}
.section-heading {
  margin: 0;
}
.report-steps {
  list-style: none;
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(0, 1fr);
  gap: 16px;
  padding: 0;
  margin: 0;
}
.report-steps li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 2px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: 14px;
}
.report-steps .active {
  color: var(--color-primary);
  border-color: var(--color-primary);
  font-weight: 600;
}
.step-number {
  font-family: var(--font-mono);
}
.report-steps .complete .step-number {
  color: var(--color-success);
}
.step-hint {
  margin-top: 8px;
  overflow-wrap: anywhere;
}
.page-header {
  flex-wrap: wrap;
}
.page-header h1 {
  overflow-wrap: anywhere;
}
.save-bar {
  display: grid;
  gap: 12px;
  padding: 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-panel);
}
@media (max-width: 1150px) {
  .daily-workspace {
    grid-template-columns: minmax(0, 1fr);
  }
  .report-output {
    position: static;
  }
}
@media (max-width: 767px) {
  .report-steps {
    gap: 8px;
  }
  .report-steps li {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
    font-size: 14px;
  }
}
</style>
