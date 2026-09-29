<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { errorMessage } from '../../../shared/api'
import { useToast } from '../../../shared/composables/useToast'
import UiBreadcrumbs from '../../../shared/components/ui/UiBreadcrumbs.vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiCard from '../../../shared/components/ui/UiCard.vue'
import UiErrorState from '../../../shared/components/ui/UiErrorState.vue'
import UiInput from '../../../shared/components/ui/UiInput.vue'
import UiTextarea from '../../../shared/components/ui/UiTextarea.vue'
import UiSkeleton from '../../../shared/components/ui/UiSkeleton.vue'
import UiConfirmDialog from '../../../shared/components/ui/UiConfirmDialog.vue'
import { qaApi, type ReportTemplate } from '../api'
import {
  customKeys,
  templateFields,
  fieldLabel,
  renderTemplate,
  starterBody,
  templateError,
  templateTokens,
  rememberTemplate,
} from '../templates'
import '../styles.css'

const router = useRouter()
const route = useRoute()
const { notify } = useToast()
const selected = ref<ReportTemplate>()
const isEditing = computed(() => typeof route.params.templateId === 'string')
const name = ref('')
const description = ref('')
const body = ref(starterBody)
const customName = ref('')
const editor = ref<{ textarea?: HTMLTextAreaElement }>()
const loading = ref(true),
  ready = ref(false),
  busy = ref(false)
const error = ref(''),
  formError = ref('')
const discardOpen = ref(false)
const baseline = ref('')
let resolveDiscard: ((result: boolean) => void) | undefined
let loadId = 0
const form = computed(() => ({
  name: name.value.trim(),
  description: description.value.trim() || null,
  body: body.value.trim(),
}))
const dirty = computed(() => ready.value && JSON.stringify(form.value) !== baseline.value)
const syntaxError = computed(() => templateError(body.value))
const extraKeys = computed(() => customKeys(body.value))
const fields = computed(() => templateFields(body.value))
const preview = computed(() =>
  renderTemplate(
    body.value,
    {
      title: 'Daily QA Report',
      author_name: 'Tester',
      report_date: '2026-09-03',
    },
    [
      {
        activity_code: 'QA-142',
        environment: 'Staging',
        result: 'Pass',
        current_issue: 'Tidak ada issue',
        current_status: 'Passed',
        links: [{ url: 'https://example.test/coverage', label: null }],
        template_values: Object.fromEntries(
          fields.value.activity
            .filter((key) => extraKeys.value.includes(key))
            .map((key) => [key, `Contoh ${fieldLabel(key).toLowerCase()}`]),
        ),
      },
    ],
    Object.fromEntries(
      extraKeys.value.map((key) => [key, `Contoh ${fieldLabel(key).toLowerCase()}`]),
    ),
  ),
)
function fill(template?: ReportTemplate): void {
  selected.value = template
  name.value = template?.name ?? ''
  description.value = template?.description ?? ''
  body.value = template?.body ?? starterBody
  formError.value = error.value = ''
  baseline.value = JSON.stringify(form.value)
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
async function insert(token: string): Promise<void> {
  const element = editor.value?.textarea
  if (!element) return
  const start = element.selectionStart
  body.value = body.value.slice(0, start) + token + body.value.slice(element.selectionEnd)
  await nextTick()
  element.focus()
  element.setSelectionRange(start + token.length, start + token.length)
}
function addCustom(): void {
  const key = customName.value.trim()
  if (!/^[a-z][a-z0-9_]{0,49}$/.test(key)) {
    formError.value = 'Contoh nama yang valid: nama_proyek atau rencana_besok.'
    return
  }
  formError.value = ''
  void insert('{{' + key + '}}')
  customName.value = ''
}
async function load(): Promise<void> {
  const current = ++loadId
  const templateId = route.params.templateId
  loading.value = true
  ready.value = false
  error.value = ''
  try {
    let template: ReportTemplate | undefined
    if (typeof templateId === 'string') {
      const templates = await qaApi.listTemplates()
      if (current !== loadId) return
      template = templates.find((item) => item.id === templateId)
      if (!template)
        throw new Error('Template tidak ditemukan. Kembali ke daftar untuk memilih template lain.')
    }
    fill(template)
    ready.value = true
  } catch (cause) {
    if (current === loadId) error.value = errorMessage(cause)
  } finally {
    if (current === loadId) loading.value = false
  }
}
async function save(andUse = false): Promise<void> {
  if (busy.value) return
  formError.value =
    syntaxError.value || (!name.value.trim() ? 'Isi nama template terlebih dahulu.' : '')
  if (formError.value) return
  busy.value = true
  error.value = ''
  try {
    const saved = selected.value
      ? await qaApi.updateTemplate(selected.value.id, {
          ...form.value,
          expected_updated_at: selected.value.updated_at,
        })
      : await qaApi.createTemplate(form.value)
    fill(saved)
    notify('Template tersimpan.')
    busy.value = false
    if (andUse) {
      rememberTemplate(saved.id)
      await router.push({ path: '/qa-reports/new', query: { template: saved.id } })
    } else {
      await router.push('/qa-reports/templates')
    }
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}
function unload(event: BeforeUnloadEvent): void {
  if (dirty.value) {
    event.preventDefault()
    event.returnValue = ''
  }
}
onBeforeRouteLeave(confirmDiscard)
onBeforeRouteUpdate(confirmDiscard)
watch(
  () => route.params.templateId,
  () => void load(),
)
onMounted(() => {
  void load()
  window.addEventListener('beforeunload', unload)
})
onUnmounted(() => {
  ++loadId
  window.removeEventListener('beforeunload', unload)
  resolveDiscard?.(false)
})
</script>

<template>
  <UiBreadcrumbs
    :items="[
      { label: 'Laporan', to: '/qa-reports' },
      { label: 'Template', to: '/qa-reports/templates' },
      { label: isEditing ? 'Edit template' : 'Template baru' },
    ]"
  />
  <div class="page-header">
    <div>
      <h1>{{ isEditing ? 'Edit template' : 'Template baru' }}</h1>
      <p>Atur format dan placeholder. Periksa contoh hasil sebelum menyimpan.</p>
    </div>
    <UiButton
      variant="secondary"
      :disabled="busy"
      @click="router.push('/qa-reports/templates')"
    >
      Kembali ke daftar template
    </UiButton>
  </div>
  <UiSkeleton
    v-if="loading"
    :lines="5"
  />
  <UiErrorState
    v-else-if="!ready"
    :message="error"
    retryable
    @retry="load"
  />
  <section
    v-else
    class="template-editor"
    aria-label="Editor template"
  >
    <UiCard padding="md">
      <form
        class="stack"
        @submit.prevent="save()"
      >
        <div>
          <h2>Format &amp; placeholder</h2>
          <p class="small muted mt-2">
            Tulis format laporanmu. Placeholder akan diganti dengan isian dari form laporan.
          </p>
        </div>
        <fieldset
          class="template-fields stack"
          :disabled="busy"
        >
          <UiInput
            v-model="name"
            label="Nama template"
            placeholder="Daily QA — tim produk"
            maxlength="100"
            required
          />
          <UiInput
            v-model="description"
            label="Keterangan (opsional)"
            placeholder="Dipakai untuk update harian di Slack"
            maxlength="255"
          />
          <details class="placeholder-help">
            <summary>Sisipkan placeholder &amp; lihat panduan</summary>
            <div class="stack">
              <p class="small muted">
                Alur pengisian mengikuti template: identitas laporan, lalu isian per aktivitas jika
                ada blok aktivitas. Hanya kolom yang dipakai yang ditampilkan.
              </p>
              <div class="token-grid">
                <UiButton
                  v-for="[key, label] in templateTokens"
                  :key="key"
                  variant="quiet"
                  size="sm"
                  @click="insert('{{' + key + '}}')"
                >
                  {{ label }}
                </UiButton>
                <UiButton
                  variant="secondary"
                  size="sm"
                  @click="insert('{{#activities}}\n- {{activity_code}}\n{{/activities}}')"
                >
                  Blok aktivitas
                </UiButton>
              </div>
              <p
                class="small muted"
                v-pre
              >
                Letakkan data per tiket di dalam {{#activities}} ... {{/activities}}. Blok ini
                diulang untuk setiap aktivitas. Boleh dipakai lagi untuk bagian coverage atau
                status. Placeholder tambahan di dalam blok diisi per aktivitas; di luar blok diisi
                sekali untuk seluruh laporan.
              </p>
              <div class="qa-actions">
                <UiInput
                  v-model="customName"
                  label="Placeholder tambahan"
                  placeholder="nama_proyek"
                  maxlength="50"
                  @keydown.enter.prevent="addCustom"
                />
                <UiButton
                  variant="secondary"
                  @click="addCustom"
                >
                  Sisipkan
                </UiButton>
              </div>
            </div>
          </details>
          <UiTextarea
            ref="editor"
            v-model="body"
            label="Isi template"
            :rows="17"
            maxlength="20000"
            required
            :error="syntaxError || undefined"
            hint="Teks dan baris kosong mengikuti format yang kamu tulis. Gunakan *tebal* untuk Slack."
          />
          <p
            v-if="!syntaxError"
            class="qa-notice"
          >
            Alur: Identitas laporan{{ fields.hasActivities ? ' → Isian per aktivitas' : '' }} →
            simpan.
            <span v-if="fields.report.length">
              Isian laporan: {{ fields.report.map(fieldLabel).join(', ') }}.
            </span>
            <span v-if="fields.activity.length">
              Per aktivitas:
              {{
                fields.activity
                  .map(
                    (key) =>
                      templateTokens.find(([token]) => token === key)?.[1] ?? fieldLabel(key),
                  )
                  .join(', ')
              }}.
            </span>
            Kolom yang tidak digunakan tidak ditampilkan.
          </p>
        </fieldset>
        <p
          v-if="formError"
          class="field-error"
          role="alert"
        >
          {{ formError }}
        </p>
        <UiErrorState
          v-if="error"
          :message="error"
        />
        <div class="qa-actions">
          <UiButton
            type="submit"
            :loading="busy"
            :disabled="!!syntaxError"
          >
            Simpan template
          </UiButton>
          <UiButton
            variant="secondary"
            :disabled="busy || !!syntaxError"
            @click="save(true)"
          >
            Simpan &amp; buat laporan
          </UiButton>
        </div>
        <div class="template-form-actions qa-actions">
          <span
            class="small muted"
            role="status"
          >
            {{
              dirty
                ? 'Ada perubahan belum disimpan'
                : selected
                  ? 'Template tersimpan'
                  : 'Belum disimpan'
            }}
          </span>
        </div>
      </form>
    </UiCard>
    <UiCard
      tone="subtle"
      padding="md"
    >
      <div class="section-heading">
        <div>
          <h2>Contoh hasil</h2>
          <p>Diperbarui saat format diubah · data contoh</p>
        </div>
      </div>
      <p
        v-if="syntaxError"
        class="small muted"
      >
        Lengkapi placeholder untuk melihat contoh hasil.
      </p>
      <pre
        v-else
        class="template-preview"
        >{{ preview }}</pre>
      <p class="small muted mt-2">
        Saat membuat laporan, nama, tanggal, dan data contoh diganti dengan isianmu.
      </p>
    </UiCard>
  </section>
  <UiConfirmDialog
    v-model="discardOpen"
    title="Tinggalkan perubahan template?"
    description="Perubahan yang belum disimpan akan hilang. Pilih Batal untuk kembali menyimpan."
    confirm-label="Buang perubahan"
    @confirm="discard"
  />
</template>
