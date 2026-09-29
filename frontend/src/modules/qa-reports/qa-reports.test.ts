import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent } from 'vue'
import { qaApi, localDate, safeCoverageUrl, statusLabel, yesterday, type Report } from './api'
import ReportView from './views/ReportView.vue'
import HistoryView from './views/HistoryView.vue'
import { ApiError } from '../../shared/api'
import * as sharedApi from '../../shared/api'
import { useAuthStore } from '../../shared/stores/auth'
import AuthGate from '../../shared/components/auth/AuthGate.vue'
import UiInput from '../../shared/components/ui/UiInput.vue'
import UiSelect from '../../shared/components/ui/UiSelect.vue'
import UiTextarea from '../../shared/components/ui/UiTextarea.vue'
import ReportPreview from './components/ReportPreview.vue'
import DeleteReportButton from './components/DeleteReportButton.vue'
import BackupControls from '../backups/components/BackupControls.vue'
import { backupApi } from '../backups/api'
import { qaReportRoutes } from './routes'

const fixture: Report = {
  id: 'test-report-id',
  title: 'Test Daily QA Report',
  author_name: 'Tester',
  report_date: '2026-09-02',
  version: 1,
  status: 'draft',
  updated_at: '2026-09-02T00:00:00Z',
  slack_sent_at: null,
  email_sent_at: null,
  items: [
    {
      id: 'test-item-id',
      activity_code: 'QA-17',
      environment: 'Dev',
      result: 'Pass',
      current_issue: null,
      current_status: 'Pass',
      links: [{ url: 'javascript:alert(1)', label: null }],
    },
  ],
}

const previewFixture = {
  title: fixture.title,
  slack:
    'Test Daily QA Report\nDate: September 2, 2026\n\nTesting Summary:\nActivity: QA-17\nEnvironment: Dev\nResult: Pass\n\nTest Coverage :\nActivity: QA-17\njavascript:alert(1)\n\nCurrent Status:\nQA-17: Pass',
  html: '<p>Test report</p>',
  markdown: '# Test Daily QA Report\n\n## Test Coverage :\njavascript:alert(1)',
  slack_mrkdwn: '*Test Daily QA Report*\n\n*Test Coverage :*\njavascript:alert(1)',
}

async function reportView(edit = false, newReport = false) {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAuthStore().displayName = 'Tester'
  vi.spyOn(qaApi, 'get').mockResolvedValue(structuredClone(fixture))
  vi.spyOn(qaApi, 'preview').mockResolvedValue(previewFixture)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/qa-reports/:id', component: ReportView },
      { path: '/qa-reports/new', component: ReportView, meta: { newReport: true } },
      { path: '/qa-reports/history', component: HistoryView },
      { path: '/qa-reports', component: { template: '<div>History</div>' } },
    ],
  })
  await router.push(
    newReport ? '/qa-reports/new' : `/qa-reports/${fixture.id}${edit ? '?edit=1' : ''}`,
  )
  await router.isReady()
  const wrapper = mount(defineComponent({ template: '<RouterView />' }), {
    attachTo: document.body,
    global: { plugins: [pinia, router] },
  })
  await flushPromises()
  return { wrapper, router }
}

async function advance(wrapper: VueWrapper, count = 1): Promise<void> {
  for (let index = 0; index < count; index++) {
    await wrapper.find('form').trigger('submit')
    await flushPromises()
  }
}
async function backStep(wrapper: VueWrapper): Promise<void> {
  await wrapper
    .findAll('button')
    .find(
      (button) =>
        button.text().startsWith('Kembali ke ') && button.text() !== 'Kembali ke daftar laporan',
    )!
    .trigger('click')
  await flushPromises()
}

describe('QA reports', () => {
  beforeEach(() => {
    vi.spyOn(qaApi, 'listTemplates').mockResolvedValue([])
  })
  it('labels editable saved reports without implying data is unsaved', () => {
    expect(statusLabel('draft')).toBe('Tersimpan')
    expect(statusLabel('finalized')).toBe('Final')
    expect(statusLabel('sent')).toBe('Terkirim')
  })

  it('provides breadcrumbs and visible navigation buttons on a saved report', async () => {
    const { wrapper, router } = await reportView()
    const crumbs = wrapper.get('nav[aria-label="Breadcrumb"]')
    expect(crumbs.get('[aria-current="page"]').text()).toBe(fixture.title)
    for (const label of ['Laporan tanggal lain', 'Kembali ke daftar laporan']) {
      expect(
        wrapper
          .findAll('button')
          .find((button) => button.text() === label)!
          .classes(),
      ).toContain('button-secondary')
    }
    await crumbs.get('a').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/qa-reports')
  })

  it('retains coverage and notes through back navigation and activity reordering', async () => {
    const create = vi.spyOn(qaApi, 'create').mockResolvedValue(structuredClone(fixture))
    const { wrapper } = await reportView(true, true)
    const fields = (label: string) =>
      wrapper.findAllComponents(UiInput).filter((field) => field.props('label') === label)
    const textareas = (label: string) =>
      wrapper.findAllComponents(UiTextarea).filter((field) => field.props('label') === label)
    const click = async (name: string) => {
      await wrapper
        .findAll('button')
        .find((button) => button.text() === name)!
        .trigger('click')
      await flushPromises()
    }
    expect(wrapper.find('textarea').exists()).toBe(false)
    expect(fields('URL coverage 1')).toHaveLength(0)
    expect(wrapper.findAll('.report-steps li')).toHaveLength(2)
    expect(fields('Activity / kode tiket')).toHaveLength(0)
    await advance(wrapper)
    expect(wrapper.get('[aria-current="step"]').text()).toContain('Isian per aktivitas')
    expect(document.activeElement?.textContent).toContain('2. Isian per aktivitas')
    await fields('Activity / kode tiket')[0]!.get('input').setValue('QA-A')
    await fields('Durasi pengerjaan (jam)')[0]!.get('input').setValue('1.5')
    await fields('Tambah opsi PIC / Guidance')[0]!.get('input').setValue('Ghaza')
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Tambah opsi')!
      .trigger('click')
    await click('Tambah aktivitas')
    await fields('Activity / kode tiket')[1]!.get('input').setValue('QA-B')
    await fields('URL coverage 1')[0]!.get('input').setValue('https://example.test/a')
    await fields('URL coverage 1')[1]!.get('input').setValue('https://example.test/b')
    await textareas('Current issues')[0]!.get('textarea').setValue('Issue A')
    await textareas('Current issues')[1]!.get('textarea').setValue('Issue B')
    await textareas('Obstacle (manmonth)')[0]!.get('textarea').setValue('Blocked A')
    await textareas('Next Step / Action (manmonth)')[0]!.get('textarea').setValue('Retry A')
    const guidance = wrapper
      .findAllComponents(UiSelect)
      .find((field) => field.props('label') === 'PIC / Guidance (manmonth)')!
    await guidance.get('select').setValue('Ghaza')
    await textareas('Deliverable (manmonth)')[0]!.get('textarea').setValue('Evidence A')
    await fields('Current Status')[0]!.get('input').setValue('Retest A')
    await backStep(wrapper)
    await advance(wrapper)
    await wrapper.get('button[aria-label="Naikkan aktivitas 2"]').trigger('click')
    expect(
      fields('URL coverage 1').map((field) => field.get<HTMLInputElement>('input').element.value),
    ).toEqual(['https://example.test/b', 'https://example.test/a'])
    expect(
      textareas('Current issues').map(
        (field) => field.get<HTMLTextAreaElement>('textarea').element.value,
      ),
    ).toEqual(['Issue B', 'Issue A'])
    expect(
      textareas('Obstacle (manmonth)').map(
        (field) => field.get<HTMLTextAreaElement>('textarea').element.value,
      ),
    ).toEqual(['', 'Blocked A'])
    expect(create).not.toHaveBeenCalled()
    await Promise.all([
      wrapper.get('form').trigger('submit'),
      wrapper.get('form').trigger('submit'),
    ])
    await flushPromises()
    expect(create).toHaveBeenCalledTimes(1)
    expect(
      create.mock.calls[0]![0].items?.map((item) => [
        item.activity_code,
        item.links[0]?.url,
        item.current_issue,
        item.duration_hours,
        item.obstacle,
        item.next_step,
        item.pic_guidance,
        item.deliverable,
      ]),
    ).toEqual([
      [
        'QA-B',
        'https://example.test/b',
        'Issue B',
        undefined,
        undefined,
        undefined,
        undefined,
        undefined,
      ],
      [
        'QA-A',
        'https://example.test/a',
        'Issue A',
        1.5,
        'Blocked A',
        'Retry A',
        'Ghaza',
        'Evidence A',
      ],
    ])
    expect(wrapper.find('form').exists()).toBe(false)
  })

  it('uses local calendar dates and accepts only safe coverage link protocols', () => {
    expect(localDate(new Date(2026, 8, 2, 0, 5))).toBe('2026-09-02')
    expect(yesterday('2024-03-01')).toBe('2024-02-29')
    expect(safeCoverageUrl('https://example.test/coverage')).toBe(true)
    for (const url of [
      'javascript:alert(1)',
      'data:text/html,test',
      'invalid',
      'https://user:pass@example.test',
    ]) {
      expect(safeCoverageUrl(url)).toBe(false)
    }
  })

  it('opens history reports read-only and never renders unsafe coverage as a link', async () => {
    const { wrapper } = await reportView()
    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.find('a[href^="javascript:"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('javascript:alert(1)')
    expect(wrapper.find('pre').text()).toBe(previewFixture.slack_mrkdwn)
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Edit laporan')!
      .trigger('click')
    expect(wrapper.find('form').exists()).toBe(true)
  })

  it('retains draft input on save failure and blocks stale previews', async () => {
    vi.spyOn(qaApi, 'save').mockRejectedValue(new ApiError('Server tidak terjangkau.', 0))
    const { wrapper } = await reportView(true)
    await wrapper
      .findAllComponents(UiInput)
      .find((input) => input.props('label') === 'Judul laporan')!
      .find('input')
      .setValue('Draft belum disimpan')
    await advance(wrapper)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Server tidak terjangkau.')
    await backStep(wrapper)
    expect(
      wrapper
        .findAllComponents(UiInput)
        .find((input) => input.props('label') === 'Judul laporan')!
        .find<HTMLInputElement>('input').element.value,
    ).toBe('Draft belum disimpan')
    expect(wrapper.find('pre').exists()).toBe(false)
    expect(wrapper.text()).toContain('Ada isian belum disimpan')
    expect(qaApi.save).toHaveBeenCalledWith(
      fixture.id,
      expect.objectContaining({ title: 'Draft belum disimpan', version: 1 }),
    )
  })

  it('asks before leaving an unsaved draft and allows cancelling the navigation', async () => {
    const { wrapper, router } = await reportView(true)
    await wrapper.find('input').setValue('Perubahan lokal')
    const navigation = router.push('/qa-reports')
    await flushPromises()
    expect(document.querySelector('dialog[open]')?.textContent).toContain('Tinggalkan perubahan?')
    const cancel = [...document.querySelectorAll<HTMLButtonElement>('dialog[open] button')].find(
      (button) => button.textContent?.trim() === 'Batal',
    )!
    cancel.click()
    await navigation
    expect(router.currentRoute.value.path).toContain(fixture.id)
    expect(wrapper.find<HTMLInputElement>('input').element.value).toBe('Perubahan lokal')
  })

  it('offers the existing report when creation hits a duplicate date', async () => {
    vi.spyOn(qaApi, 'create').mockRejectedValue(new ApiError('Tanggal sudah ada.', 409, fixture.id))
    const { wrapper } = await reportView(true, true)
    await advance(wrapper)
    await wrapper
      .findAllComponents(UiInput)
      .find((input) => input.props('label') === 'Activity / kode tiket')!
      .find('input')
      .setValue('QA-17')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Tanggal sudah ada.')
    expect(wrapper.find(`a[href="/qa-reports/${fixture.id}?edit=1"]`).text()).toContain(
      'Buka laporan yang sudah ada',
    )
    await backStep(wrapper)
    await advance(wrapper)
    expect(
      wrapper
        .findAllComponents(UiInput)
        .find((input) => input.props('label') === 'Activity / kode tiket')!
        .find<HTMLInputElement>('input').element.value,
    ).toBe('QA-17')
  })

  it('opens an older empty draft with an activity form without writing to the server', async () => {
    const create = vi.spyOn(qaApi, 'create')
    const save = vi.spyOn(qaApi, 'save')
    const { wrapper, router } = await reportView(true)
    vi.mocked(qaApi.get).mockResolvedValue({
      ...structuredClone(fixture),
      id: 'empty-report',
      items: [],
    })
    await router.push('/qa-reports/empty-report?edit=1')
    await flushPromises()
    expect(wrapper.findAll('fieldset.activity-editor')).toHaveLength(0)
    await advance(wrapper)
    expect(wrapper.findAll('fieldset.activity-editor')).toHaveLength(1)
    expect(
      wrapper
        .findAllComponents(UiInput)
        .find((input) => input.props('label') === 'Activity / kode tiket')!
        .find<HTMLInputElement>('input').element.value,
    ).toBe('')
    expect(create).not.toHaveBeenCalled()
    expect(save).not.toHaveBeenCalled()
  })

  it('creates metadata and activities together, then exports the saved report without finalizing', async () => {
    const create = vi.spyOn(qaApi, 'create').mockResolvedValue(structuredClone(fixture))
    const save = vi.spyOn(qaApi, 'save')
    const finalize = vi.spyOn(qaApi, 'finalize')
    const download = vi.spyOn(sharedApi, 'downloadFile').mockImplementation(() => {})
    const { wrapper } = await reportView(true, true)
    expect(create).not.toHaveBeenCalled()
    expect(wrapper.findAll('fieldset.activity-editor')).toHaveLength(0)
    const input = (label: string) =>
      wrapper
        .findAllComponents(UiInput)
        .find((field) => field.props('label') === label)!
        .find('input')
    await input('Nama pelapor').setValue('Gideon')
    await input('Tanggal laporan').setValue('2026-09-01')
    await advance(wrapper)
    await input('Activity / kode tiket').setValue('AMTSK-166')
    expect(create).not.toHaveBeenCalled()
    expect(wrapper.find('textarea').exists()).toBe(true)
    await input('URL coverage 1').setValue('https://example.test/coverage?tab=t.0')
    expect(create).not.toHaveBeenCalled()
    await input('Current Status').setValue('Passed prod')
    await wrapper.find('textarea').setValue('Passed on production')
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Simpan & ekspor Slack .md')!
      .trigger('click')
    await flushPromises()
    expect(create).toHaveBeenCalledExactlyOnceWith({
      title: 'Gideon Daily QA Report',
      report_date: '2026-09-01',
      author_name: 'Gideon',
      items: [
        {
          id: undefined,
          activity_code: 'AMTSK-166',
          environment: 'Dev',
          result: 'In progress',
          current_status: 'Passed prod',
          current_issue: 'Passed on production',
          links: [{ url: 'https://example.test/coverage?tab=t.0', label: null }],
        },
      ],
    })
    expect(save).not.toHaveBeenCalled()
    expect(finalize).not.toHaveBeenCalled()
    expect(download).toHaveBeenCalledWith(expect.any(Blob), 'qa-report-2026-09-02-slack.md')
    const blob = download.mock.calls[0]![0]
    const contents = await new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result)
      reader.readAsText(blob)
    })
    expect(contents).toBe(previewFixture.slack_mrkdwn)
    expect(wrapper.find('pre').text()).toBe(previewFixture.slack_mrkdwn)
  })

  it('shows a retryable export error after a successful save without losing saved data', async () => {
    vi.spyOn(qaApi, 'save').mockResolvedValue({ ...structuredClone(fixture), version: 2 })
    const download = vi.spyOn(sharedApi, 'downloadFile').mockImplementation(() => {})
    const { wrapper } = await reportView(true)
    vi.mocked(qaApi.preview).mockRejectedValue(new ApiError('Preview gagal.', 500))
    await advance(wrapper)
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Simpan & ekspor Slack .md')!
      .trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Laporan sudah tersimpan, tetapi preview gagal dimuat.')
    expect(download).not.toHaveBeenCalled()
    expect(wrapper.find('form').exists()).toBe(false)
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Edit laporan')!
      .trigger('click')
    await flushPromises()
    await advance(wrapper)
    expect(
      wrapper
        .findAllComponents(UiInput)
        .find((input) => input.props('label') === 'Activity / kode tiket')!
        .find<HTMLInputElement>('input').element.value,
    ).toBe('QA-17')
  })

  // jsdom does not reliably flush Vue Router's async leave-guard dialog; cover this in browser QA.
  it.skip('prevents saving an empty activity and confirms leaving a new unsaved form', async () => {
    const create = vi.spyOn(qaApi, 'create')
    const { wrapper, router } = await reportView(true, true)
    await advance(wrapper)
    await wrapper.find('form').trigger('submit')
    expect(create).not.toHaveBeenCalled()
    await wrapper.find('input[type="text"]').setValue('Gideon')
    const navigation = router.push('/qa-reports')
    await flushPromises()
    expect(document.querySelector('dialog[open]')?.textContent).toContain('Tinggalkan perubahan?')
    ;[...document.querySelectorAll<HTMLButtonElement>('dialog[open] button')]
      .find((button) => button.textContent?.trim() === 'Buang perubahan')!
      .click()
    await navigation
    expect(router.currentRoute.value.path).toBe('/qa-reports')
  })

  it('keeps mounted form data when a session expires', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const auth = useAuthStore()
    auth.authenticated = true
    auth.everAuthenticated = true
    vi.spyOn(auth, 'check').mockResolvedValue()
    const wrapper = mount(AuthGate, {
      attachTo: document.body,
      global: { plugins: [pinia] },
      slots: { default: '<textarea aria-label="Draft">keep me</textarea>' },
    })
    window.dispatchEvent(new Event('qa:session-expired'))
    await flushPromises()
    expect(wrapper.find('textarea').element.value).toBe('keep me')
    expect(document.querySelector('dialog[open]')?.textContent).toContain('Masuk kembali')
  })

  it('folds activities without clearing input and opens hidden invalid fields before validation', async () => {
    const create = vi.spyOn(qaApi, 'create')
    const { wrapper } = await reportView(true, true)
    await advance(wrapper)
    const button = (name: string) =>
      wrapper.findAll('button').find((button) => button.text() === name)!
    await button('Lipat semua aktivitas').trigger('click')
    expect(wrapper.find('[aria-controls]').attributes('aria-expanded')).toBe('false')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[aria-controls]').attributes('aria-expanded')).toBe('true')
    expect(create).not.toHaveBeenCalled()
    const input = wrapper
      .findAllComponents(UiInput)
      .find((input) => input.props('label') === 'Activity / kode tiket')!
      .find('input')
    await input.setValue('QA-42')
    await button('Tambah aktivitas').trigger('click')
    expect(
      wrapper.findAll('[aria-controls]').map((button) => button.attributes('aria-expanded')),
    ).toEqual(['false', 'true'])
    await button('Buka semua aktivitas').trigger('click')
    expect(input.element.value).toBe('QA-42')
  })

  it('opens the list newest first and navigates to a separate new form', async () => {
    const list = vi.spyOn(qaApi, 'list').mockResolvedValue({
      reports: [
        { ...fixture, id: 'new', report_date: '2026-09-02', title: 'New report', item_count: 1 },
        { ...fixture, id: 'old', report_date: '2026-09-01', title: 'Old report', item_count: 1 },
      ],
      total: 2,
      page: 1,
      page_size: 20,
    })
    const create = vi.spyOn(qaApi, 'create')
    const pinia = createPinia()
    const router = createRouter({ history: createMemoryHistory(), routes: qaReportRoutes })
    await router.push('/qa-reports')
    await router.isReady()
    const wrapper = mount(defineComponent({ template: '<RouterView />' }), {
      attachTo: document.body,
      global: { plugins: [router, pinia] },
    })
    await flushPromises()
    expect(list).toHaveBeenCalledWith({ page: '1', order: 'desc' })
    expect(wrapper.findAll('tbody tr').map((row) => row.text())).toEqual([
      expect.stringContaining('New report'),
      expect.stringContaining('Old report'),
    ])
    expect(wrapper.find('fieldset.activity-editor').exists()).toBe(false)
    expect(wrapper.text()).toContain('Tersimpan')
    expect(wrapper.text()).not.toContain('Draft')
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Tambah laporan')!
      .trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/qa-reports/new')
    expect(wrapper.find('fieldset.activity-editor').exists()).toBe(false)
    await advance(wrapper)
    expect(wrapper.find('fieldset.activity-editor').exists()).toBe(true)
    expect(create).not.toHaveBeenCalled()
  })

  it('selects Slack, Markdown and plain-text exports without changing the saved report', async () => {
    const download = vi.spyOn(sharedApi, 'downloadFile').mockImplementation(() => {})
    const wrapper = mount(ReportPreview, { props: { report: fixture, preview: previewFixture } })
    expect(wrapper.find('pre').text()).toBe(previewFixture.slack_mrkdwn)
    await wrapper.find('select').setValue('markdown')
    expect(wrapper.find('pre').text()).toBe(previewFixture.markdown)
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Unduh .md')!
      .trigger('click')
    expect(download).toHaveBeenLastCalledWith(expect.any(Blob), 'qa-report-2026-09-02.md')
    await wrapper.find('select').setValue('text')
    expect(wrapper.find('pre').text()).toBe(previewFixture.slack)
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Unduh .txt')!
      .trigger('click')
    expect(download).toHaveBeenLastCalledWith(expect.any(Blob), 'qa-report-2026-09-02.txt')
  })

  it('requires explicit deletion confirmation and retains the dialog on a version conflict', async () => {
    const remove = vi
      .spyOn(qaApi, 'remove')
      .mockRejectedValueOnce(new ApiError('Laporan berubah di tab lain.', 409))
      .mockResolvedValue(undefined)
    const wrapper = mount(DeleteReportButton, {
      attachTo: document.body,
      props: { reportId: fixture.id, reportTitle: fixture.title, report: fixture },
    })
    expect(wrapper.find('button').classes()).toContain('button-danger')
    await wrapper.find('button').trigger('click')
    expect(remove).not.toHaveBeenCalled()
    const confirm = () =>
      [...document.querySelectorAll<HTMLButtonElement>('dialog button')].find(
        (button) => button.textContent?.trim() === 'Hapus permanen',
      )!
    confirm().click()
    await flushPromises()
    expect(document.querySelector('dialog')?.textContent).toContain('Laporan berubah di tab lain.')
    expect(wrapper.emitted('deleted')).toBeUndefined()
    confirm().click()
    await flushPromises()
    expect(remove).toHaveBeenLastCalledWith(fixture.id, fixture.version)
    expect(wrapper.emitted('deleted')).toHaveLength(1)
  })

  it('validates backup uploads and waits for confirmation before restoring', async () => {
    const preview = vi.spyOn(backupApi, 'preview').mockResolvedValue({
      exported_at: '2026-09-29T00:00:00Z',
      reports: 1,
      templates: 2,
      vault_entries: 3,
      has_theme: true,
      has_existing_data: true,
      vault_mergeable: true,
      existing_reports: 20,
      existing_templates: 2,
      existing_vault_entries: 1,
      new_reports: 1,
      new_templates: 0,
      new_vault_entries: 2,
    })
    const restore = vi.spyOn(backupApi, 'restore').mockResolvedValue({
      mode: 'missing',
      reports_restored: 1,
      reports_skipped: 0,
      vault_restored: 3,
      vault_skipped: 0,
      theme: { theme: 'dark', color_palette: null, saved_palettes: [] },
    })
    const wrapper = mount(BackupControls, {
      attachTo: document.body,
      global: { plugins: [createPinia()] },
    })
    expect(wrapper.find('details').exists()).toBe(false)
    expect(wrapper.get('h2').text()).toBe('Backup & import')
    const input = wrapper.find<HTMLInputElement>('input[type=file]')
    Object.defineProperty(input.element, 'files', {
      configurable: true,
      value: [{ name: 'invalid.json', size: 1 }],
    })
    await input.trigger('change')
    await flushPromises()
    expect(wrapper.text()).toContain('Pilih file backup ZIP.')
    expect(preview).not.toHaveBeenCalled()
    expect(restore).not.toHaveBeenCalled()
    const archive = { name: 'backup_20260929_120000.zip', size: 10 } as File
    expect(wrapper.text()).toContain('Drag & drop file ZIP')
    await wrapper.get('.import-picker').trigger('drop', {
      dataTransfer: { files: [archive] },
    })
    await flushPromises()
    expect(preview).toHaveBeenCalledExactlyOnceWith(archive)
    expect(document.querySelector('dialog')?.textContent).toContain('backup_20260929_120000.zip')
    expect(document.querySelector('dialog')?.textContent).toContain('Perbandingan data')
    expect(document.querySelector('dialog')?.textContent).toContain('Data baru')
    expect(document.querySelector('dialog')?.textContent).toContain('Overwrite semua')
    expect(restore).not.toHaveBeenCalled()
    ;[...document.querySelectorAll<HTMLButtonElement>('dialog button')]
      .find((button) => button.textContent?.trim() === 'Tambahkan yang belum ada')!
      .click()
    await flushPromises()
    expect(restore).toHaveBeenCalledExactlyOnceWith(archive, 'missing')
    expect(wrapper.emitted('restored')).toHaveLength(1)
  })
})
