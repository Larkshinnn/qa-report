<script setup lang="ts">
import { type Report, type ReportPreview } from '../api'
import { computed, ref } from 'vue'
import { downloadFile } from '../../../shared/api'
import UiCodeBlock from '../../../shared/components/ui/UiCodeBlock.vue'
import UiCopyButton from '../../../shared/components/ui/UiCopyButton.vue'
import UiButton from '../../../shared/components/ui/UiButton.vue'
import UiSelect from '../../../shared/components/ui/UiSelect.vue'
const props = defineProps<{ preview: ReportPreview; report: Report }>()
const format = ref('slack')
const content = computed(() =>
  format.value === 'slack'
    ? props.preview.slack_mrkdwn
    : format.value === 'markdown'
      ? props.preview.markdown
      : props.preview.slack,
)
function downloadText(): void {
  downloadFile(
    new Blob([content.value], {
      type: format.value === 'text' ? 'text/plain;charset=utf-8' : 'text/markdown;charset=utf-8',
    }),
    `qa-report-${props.report.report_date}${format.value === 'slack' ? '-slack' : ''}.${format.value === 'text' ? 'txt' : 'md'}`,
  )
}
function downloadHtml(): void {
  downloadFile(
    new Blob([props.preview.html], { type: 'text/html;charset=utf-8' }),
    `qa-report-${props.report.report_date}.html`,
  )
}
</script>
<template>
  <div class="stack">
    <UiSelect
      v-model="format"
      label="Format laporan"
      :options="[
        { value: 'slack', label: 'Slack (mrkdwn)' },
        { value: 'markdown', label: 'Markdown (.md)' },
        { value: 'text', label: 'Teks biasa (.txt)' },
      ]"
    />
    <div class="qa-actions">
      <UiCopyButton
        :value="content"
        :label="format === 'slack' ? 'Salin untuk Slack' : 'Salin laporan'"
      />
      <UiButton
        variant="secondary"
        @click="downloadText"
      >
        {{ format === 'text' ? 'Unduh .txt' : 'Unduh .md' }}
      </UiButton>
      <UiButton
        variant="ghost"
        @click="downloadHtml"
      >
        Unduh HTML
      </UiButton>
    </div>
    <UiCodeBlock
      :code="content"
      label="Laporan harian tersimpan"
      :copyable="false"
    />
    <p
      v-if="report.template_body"
      class="small muted"
    >
      Hasil mengikuti format template yang tersimpan pada laporan ini. Slack mempertahankan *tebal*,
      _miring_, dan `kode`. HTML diunduh sebagai teks yang aman. Tidak ada pesan dikirim dari
      aplikasi ini.
    </p>
    <p
      v-else
      class="small muted"
    >
      Format Slack memakai *tebal*, _miring_, dan `kode`; Markdown biasa memakai heading # / ##. Isi
      catatan dipertahankan sesuai ketikanmu. Periksa hasil paste sebelum mengirim di Slack—format
      tidak selalu diterapkan otomatis. Tidak ada pesan dikirim dari aplikasi ini.
    </p>
    <a
      class="qa-link small"
      href="https://slack.com/help/articles/360039953113-Format-your-messages-in-Slack-with-markup"
      target="_blank"
      rel="noopener noreferrer"
    >
      Panduan format Slack
    </a>
  </div>
</template>
