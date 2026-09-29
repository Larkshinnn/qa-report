import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia } from 'pinia'
import { defineComponent } from 'vue'
import { qaApi, type Report, type ReportTemplate } from './api'
import { customKeys, renderTemplate, starterBody, templateError, templateFields } from './templates'
import TemplatesView from './views/TemplatesView.vue'
import TemplateEditorView from './views/TemplateEditorView.vue'
import ReportView from './views/ReportView.vue'

const template: ReportTemplate = {
  id: 'template-1',
  name: 'Tim produk',
  description: null,
  usage_count: 0,
  created_at: '2026-09-03T00:00:00Z',
  updated_at: '2026-09-03T00:00:00Z',
  body: '{{report_title}}\nProyek: {{nama_proyek}}\n{{#activities}}- {{activity_code}}: {{result}}\n{{/activities}}',
}
const report: Report = {
  id: 'report-1',
  title: 'QA',
  report_date: '2026-09-03',
  author_name: 'Tester',
  template_id: template.id,
  template_body: template.body,
  template_name: template.name,
  template_values: { nama_proyek: 'Portal' },
  version: 1,
  status: 'draft',
  updated_at: '2026-09-03T00:00:00Z',
  slack_sent_at: null,
  email_sent_at: null,
  items: [
    {
      activity_code: 'QA-1',
      environment: 'Dev',
      result: 'Pass',
      current_issue: null,
      current_status: null,
      links: [],
    },
  ],
}
async function page(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/qa-reports/templates', component: TemplatesView },
      { path: '/qa-reports/templates/new', component: TemplateEditorView },
      { path: '/qa-reports/templates/:templateId/edit', component: TemplateEditorView },
      { path: '/qa-reports/new', component: ReportView },
      { path: '/qa-reports/:id', component: ReportView },
      { path: '/qa-reports', component: { template: '<p>Daftar</p>' } },
    ],
  })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(defineComponent({ template: '<RouterView />' }), {
    attachTo: document.body,
    global: { plugins: [router, createPinia()] },
  })
  await flushPromises()
  return { wrapper, router }
}
describe('custom report templates', () => {
  beforeEach(() => {
    vi.spyOn(qaApi, 'listTemplates').mockResolvedValue([structuredClone(template)])
    vi.spyOn(qaApi, 'get').mockResolvedValue(structuredClone(report))
    vi.spyOn(qaApi, 'preview').mockResolvedValue({
      title: 'QA',
      slack: 'QA',
      markdown: 'QA',
      html: 'QA',
      slack_mrkdwn: 'QA',
    })
  })
  it('renders multiple blocks without evaluating placeholder-like user input', () => {
    expect(templateError(starterBody)).toBe('')
    const body =
      '{{nama_proyek}} {{#activities}}{{current_issue}}{{/activities}}\n{{#activities}}{{activity_code}}{{/activities}}'
    const text = renderTemplate(
      body,
      report,
      [{ ...report.items[0]!, current_issue: '{{report_title}} $&' }],
      { nama_proyek: 'Portal' },
    )
    expect(text).toBe('Portal {{report_title}} $&\nQA-1')
    expect(customKeys('{{nama_proyek}} {{ nama_proyek }} {{result}}')).toEqual(['nama_proyek'])
    for (const value of [
      '{{activity_code}}',
      '{{broken',
      '{{bad-name}}',
      '{{#activities}}{{#activities}}{{/activities}}',
      '{{/activities}}',
    ])
      expect(templateError(value)).not.toBe('')
  })
  it('does not render standalone activity block lines as blank lines', () => {
    const body = `Next Step:
{{#activities}}
- {{activity_code}}
  {{next_step}}
{{/activities}}`
    const text = renderTemplate(body, report, [
      { ...report.items[0]!, template_values: { next_step: 'Contoh next step' } },
    ])
    expect(text).toBe('Next Step:\n- QA-1\n  Contoh next step')
  })
  it('preserves an unsaved first template after a server error', async () => {
    vi.mocked(qaApi.listTemplates).mockResolvedValue([])
    vi.spyOn(qaApi, 'createTemplate').mockRejectedValue(new Error('Simpan gagal'))
    const { wrapper } = await page('/qa-reports/templates/new')
    await wrapper.get('input').setValue('Format baru')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Simpan gagal')
    expect(wrapper.get<HTMLInputElement>('input').element.value).toBe('Format baru')
    expect(wrapper.get('textarea').element.value).toContain('{{report_title}}')
  })
  it('lists templates in a table and opens a separate create page, returning after save', async () => {
    const create = vi
      .spyOn(qaApi, 'createTemplate')
      .mockResolvedValue({ ...template, name: 'Format baru' })
    const { wrapper, router } = await page('/qa-reports/templates')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    expect(wrapper.get('table').text()).toContain('Tim produk')
    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.find('textarea').exists()).toBe(false)
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Tambah template')!
      .trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/qa-reports/templates/new')
    expect(wrapper.get('h1').text()).toBe('Template baru')
    expect(wrapper.get<HTMLInputElement>('input').element.value).toBe('')
    expect(wrapper.get('textarea').element.value).toBe(starterBody)
    expect(wrapper.find('table').exists()).toBe(false)
    await wrapper.get('input').setValue('Format baru')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(create).toHaveBeenCalledExactlyOnceWith({
      name: 'Format baru',
      description: null,
      body: starterBody.trim(),
    })
    expect(router.currentRoute.value.path).toBe('/qa-reports/templates')
    expect(wrapper.find('table').exists()).toBe(true)
  })
  it('opens the selected template on an edit route and submits its concurrency version', async () => {
    const update = vi
      .spyOn(qaApi, 'updateTemplate')
      .mockResolvedValue({ ...template, name: 'Format revisi' })
    const { wrapper, router } = await page('/qa-reports/templates')
    await wrapper.get('a[aria-label="Edit template Tim produk"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/qa-reports/templates/template-1/edit')
    expect(wrapper.get('h1').text()).toBe('Edit template')
    expect(wrapper.get('textarea').element.value).toBe(template.body)
    await wrapper.get('input').setValue('Format revisi')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(update).toHaveBeenCalledExactlyOnceWith(template.id, {
      name: 'Format revisi',
      description: null,
      body: template.body,
      expected_updated_at: template.updated_at,
    })
    expect(router.currentRoute.value.path).toBe('/qa-reports/templates')
  })
  it('reports a missing edit target without silently opening a new template', async () => {
    const { wrapper } = await page('/qa-reports/templates/missing/edit')
    expect(wrapper.text()).toContain('Template tidak ditemukan')
    expect(wrapper.find('form').exists()).toBe(false)
  })
  it('ignores late editor loads after navigating to a new template', async () => {
    let resolveLoad!: (value: ReportTemplate[]) => void
    vi.mocked(qaApi.listTemplates).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveLoad = resolve
      }),
    )
    const { wrapper, router } = await page('/qa-reports/templates/template-1/edit')
    await router.push('/qa-reports/templates/new')
    await flushPromises()
    await wrapper.get('input').setValue('Draft baru')
    resolveLoad([template])
    await flushPromises()
    expect(wrapper.get<HTMLInputElement>('input').element.value).toBe('Draft baru')
    expect(wrapper.text()).not.toContain('Template tidak ditemukan')
  })
  it('saves a template before navigating to report creation with that format', async () => {
    const create = vi.spyOn(qaApi, 'createTemplate').mockResolvedValue(template)
    const { wrapper, router } = await page('/qa-reports/templates/new')
    await wrapper.get('input').setValue(template.name)
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Simpan & buat laporan')!
      .trigger('click')
    await flushPromises()
    expect(create).toHaveBeenCalledTimes(1)
    expect(router.currentRoute.value.fullPath).toBe('/qa-reports/new?template=template-1')
    expect(wrapper.get('[aria-current="step"]').text()).toContain('Identitas laporan')
  })
  it('uses a listed template directly in the report identity step', async () => {
    const { wrapper, router } = await page('/qa-reports/templates')
    await wrapper.get('button[aria-label="Gunakan template Tim produk"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/qa-reports/new?template=template-1')
    expect(wrapper.get('[aria-current="step"]').text()).toContain('Identitas laporan')
    expect(wrapper.find('.activity-editor').exists()).toBe(false)
  })
  it('retains the deletion confirmation on failure and removes only the selected table row', async () => {
    const remove = vi
      .spyOn(qaApi, 'removeTemplate')
      .mockRejectedValueOnce(new Error('Hapus gagal'))
      .mockResolvedValue(undefined)
    const { wrapper } = await page('/qa-reports/templates')
    await wrapper.get('button[aria-label="Hapus template Tim produk"]').trigger('click')
    expect(remove).not.toHaveBeenCalled()
    const confirm = () =>
      Array.from(document.querySelectorAll<HTMLButtonElement>('dialog[open] button')).find(
        (button) => button.textContent?.trim() === 'Hapus template',
      )!
    confirm().click()
    await flushPromises()
    expect(document.querySelector('dialog[open]')?.textContent).toContain('Hapus gagal')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    confirm().click()
    await flushPromises()
    expect(remove).toHaveBeenLastCalledWith(template.id)
    expect(wrapper.text()).toContain('Belum ada template')
  })
  it('asks before discarding template edits during navigation', async () => {
    const { wrapper, router } = await page('/qa-reports/templates/template-1/edit')
    await wrapper.get('input').setValue('Belum disimpan')
    const navigation = router.push('/qa-reports')
    await flushPromises()
    expect(document.querySelector('dialog[open]')?.textContent).toContain(
      'Tinggalkan perubahan template?',
    )
    Array.from(document.querySelectorAll<HTMLButtonElement>('dialog[open] button'))
      .find((button) => button.textContent?.trim() === 'Batal')!
      .click()
    await navigation
    expect(router.currentRoute.value.path).toBe('/qa-reports/templates/template-1/edit')
  })
  it('fills report-wide placeholders at identity and preserves them across back navigation', async () => {
    const create = vi.spyOn(qaApi, 'create').mockResolvedValue(structuredClone(report))
    const { wrapper } = await page('/qa-reports/new?template=template-1')
    expect(wrapper.text()).toContain('Isian template')
    await wrapper.get('textarea').setValue('Portal')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    const activity = wrapper
      .findAll('input')
      .find((input) => input.attributes('placeholder') === 'AMTSK-166')!
    await activity.setValue('QA-1')
    expect(wrapper.get('pre').text()).toContain('Proyek: Portal')
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Kembali ke Identitas laporan')!
      .trigger('click')
    await flushPromises()
    expect(wrapper.get('textarea').element.value).toBe('Portal')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(create).toHaveBeenCalledWith(
      expect.objectContaining({
        template_id: template.id,
        template_values: { nama_proyek: 'Portal' },
      }),
    )
  })
  it('keeps a saved snapshot when its template is deleted', async () => {
    vi.mocked(qaApi.listTemplates).mockResolvedValue([])
    const save = vi.spyOn(qaApi, 'save').mockResolvedValue(structuredClone(report))
    const { wrapper } = await page('/qa-reports/report-1?edit=1')
    expect(wrapper.text()).toContain('Tim produk · format tersimpan')
    for (let i = 0; i < 2; i++) {
      await wrapper.get('form').trigger('submit')
      await flushPromises()
    }
    const saved = save.mock.calls[0]![1]
    expect(saved).not.toHaveProperty('template_id')
    expect(saved.template_values).toEqual({ nama_proyek: 'Portal' })
  })
  it('uses only template fields, with per-activity next steps that survive reordering and back', async () => {
    const body =
      '{{report_title}}\nDate: {{report_date}}\nTesting Result:\n{{#activities}}- {{activity_code}} {{environment}} {{current_status}}\nSummary:\n{{current_issue}}\nNext step:\n{{next_step}}\n{{/activities}}'
    vi.mocked(qaApi.listTemplates).mockResolvedValue([{ ...template, body }])
    const create = vi
      .spyOn(qaApi, 'create')
      .mockResolvedValue({ ...structuredClone(report), template_body: body })
    const { wrapper } = await page('/qa-reports/new?template=template-1')
    expect(wrapper.findAll('.report-steps li')).toHaveLength(2)
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    const fill = async (index: number) => {
      const activity = wrapper.findAll('.activity-editor')[index]!
      const inputs = activity.findAll('input')
      await inputs[0]!.setValue(`QA-${index + 1}`)
      await inputs[1]!.setValue('Menunggu retest')
      const texts = activity.findAll('textarea')
      await texts[0]!.setValue(`Summary ${index + 1}`)
      await texts[1]!.setValue(`Next ${index + 1}`)
      expect(activity.text()).not.toContain('Test Coverage')
      expect(activity.findAll('select')).toHaveLength(2)
      expect(texts[1]!.attributes('id')).toBeTruthy()
    }
    await fill(0)
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Tambah aktivitas')!
      .trigger('click')
    await fill(1)
    await wrapper.get('button[aria-label="Naikkan aktivitas 2"]').trigger('click')
    expect(wrapper.get('pre').text().indexOf('QA-2')).toBeLessThan(
      wrapper.get('pre').text().indexOf('QA-1'),
    )
    expect(wrapper.get('pre').text()).toContain('Summary 2\nNext step:\nNext 2')
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Kembali ke Identitas laporan')!
      .trigger('click')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.findAll('.activity-editor')[0]!.findAll('textarea')[1]!.element.value).toBe(
      'Next 2',
    )
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    const saved = create.mock.calls[0]![0]
    expect(
      saved.items?.map((item) => [item.activity_code, item.result, item.template_values]),
    ).toEqual([
      ['QA-2', '', { next_step: 'Next 2' }],
      ['QA-1', '', { next_step: 'Next 1' }],
    ])
  })
  it('supports report-only templates and separates report/activity placeholder scopes', async () => {
    const body = '{{report\\_title}}\n{{catatan}}'
    expect(templateError(body)).toBe('')
    expect(
      templateFields(
        '{{catatan}}{{#activities}}{{catatan}} {{next_step}} {{next_step}}{{/activities}}',
      ),
    ).toEqual({ report: ['catatan'], activity: ['catatan', 'next_step'], hasActivities: true })
    vi.mocked(qaApi.listTemplates).mockResolvedValue([{ ...template, body }])
    const create = vi
      .spyOn(qaApi, 'create')
      .mockResolvedValue({ ...structuredClone(report), items: [], template_body: body })
    const { wrapper } = await page('/qa-reports/new?template=template-1')
    expect(wrapper.findAll('.report-steps li')).toHaveLength(1)
    expect(wrapper.find('.activity-editor').exists()).toBe(false)
    await wrapper.get('textarea').setValue('Selesai')
    expect(wrapper.get('pre').text()).toContain('Selesai')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(create).toHaveBeenCalledWith(
      expect.objectContaining({ items: [], template_values: { catatan: 'Selesai' } }),
    )
    expect(qaApi.preview).toHaveBeenCalled()
  })
  it('loads old report-wide values into the activity fields without losing the snapshot', async () => {
    const body = '{{#activities}}{{activity_code}} {{next_step}}{{/activities}}'
    vi.mocked(qaApi.get).mockResolvedValue({
      ...structuredClone(report),
      template_body: body,
      template_values: { next_step: 'Legacy next step' },
    })
    const save = vi.spyOn(qaApi, 'save').mockResolvedValue(structuredClone(report))
    const { wrapper } = await page('/qa-reports/report-1?edit=1')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('textarea').element.value).toBe('Legacy next step')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(save.mock.calls[0]![1].items[0]!.template_values).toEqual({
      next_step: 'Legacy next step',
    })
  })
})
