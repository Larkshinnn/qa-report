import { describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import UiButton from './UiButton.vue'
import UiInput from './UiInput.vue'
import UiTabs from './UiTabs.vue'
import UiDataTable from './UiDataTable.vue'
import UiConfirmDialog from './UiConfirmDialog.vue'
import UiCodeBlock from './UiCodeBlock.vue'
import UiCopyButton from './UiCopyButton.vue'
import { useUiStore } from '../../stores/ui'
import { commandNavigation, matchesCommand } from '../../navigation'

describe('Shared UI behavior', () => {
  it('blocks repeated submission while loading and keeps the label for stable width', async () => {
    const wrapper = mount(UiButton, { props: { loading: true }, slots: { default: 'Simpan' } })
    expect(wrapper.attributes('disabled')).toBeDefined()
    expect(wrapper.attributes('aria-busy')).toBe('true')
    expect(wrapper.text()).toContain('Simpan')
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toBeUndefined()
    await wrapper.setProps({ loading: false })
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })
  it('links input labels and errors and forwards native attributes to the input', async () => {
    const wrapper = mount(UiInput, {
      props: { label: 'Judul', hint: 'Masukkan judul' },
      attrs: { maxlength: 40 },
    })
    const input = wrapper.get('input')
    expect(wrapper.get('label').attributes('for')).toBe(input.attributes('id'))
    expect(input.attributes('maxlength')).toBe('40')
    await input.setValue('Laporan hari ini')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['Laporan hari ini'])
    await wrapper.setProps({ error: 'Judul harus diisi' })
    expect(input.attributes('aria-invalid')).toBe('true')
    expect(wrapper.get('[role="alert"]').attributes('id')).toBe(
      input.attributes('aria-describedby'),
    )
    expect(wrapper.find('.field-hint').exists()).toBe(false)
  })
  it('supports arrow navigation for tabs and preserves hidden panel content', async () => {
    const wrapper = mount(UiTabs, {
      attachTo: document.body,
      props: {
        modelValue: 'one',
        label: 'Contoh tabs',
        tabs: [
          { value: 'one', label: 'Satu' },
          { value: 'two', label: 'Dua' },
        ],
      },
      slots: { one: '<input value="tetap ada" />', two: 'Panel kedua' },
    })
    await wrapper.get('[role="tab"]').trigger('keydown', { key: 'ArrowRight' })
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['two'])
    await wrapper.setProps({ modelValue: 'two' })
    expect(wrapper.findAll('[role="tab"]')[1]?.attributes('aria-selected')).toBe('true')
    expect(wrapper.get('input').element.value).toBe('tetap ada')
  })
  it('sorts numeric cells numerically and clamps pagination when rows shrink', async () => {
    const rows = [
      { id: 1, name: 'Dua', value: 2 },
      { id: 2, name: 'Sepuluh', value: 10 },
      { id: 3, name: 'Satu', value: 1 },
    ]
    const wrapper = mount(UiDataTable<(typeof rows)[number]>, {
      props: {
        rows,
        columns: [
          { key: 'name', label: 'Nama' },
          { key: 'value', label: 'Nilai', sortable: true },
        ],
        rowKey: 'id',
        caption: 'Data contoh',
        pageSize: 2,
      },
    })
    await wrapper.get('th button').trigger('click')
    expect(wrapper.findAll('tbody tr').map((row) => row.text())).toEqual(['Satu1', 'Dua2'])
    await wrapper.get('[aria-label="Halaman berikutnya"]').trigger('click')
    expect(wrapper.get('tbody').text()).toBe('Sepuluh10')
    await wrapper.setProps({ rows: [rows[0]!] })
    expect(wrapper.get('tbody').text()).toBe('Dua2')
    expect(wrapper.get('[aria-label="Halaman sebelumnya"]').attributes('disabled')).toBeDefined()
  })
  it('renders error, loading, and empty states without stale table data', async () => {
    const wrapper = mount(UiDataTable<{ id: number }>, {
      props: { rows: [], columns: [], rowKey: 'id', caption: 'Contoh', loading: true },
    })
    expect(wrapper.find('[role="status"]').exists()).toBe(true)
    await wrapper.setProps({ loading: false, error: 'Koneksi gagal' })
    expect(wrapper.get('[role="alert"]').text()).toContain('Koneksi gagal')
    await wrapper.setProps({ error: undefined })
    expect(wrapper.text()).toContain('Belum ada data')
  })
  it('keeps destructive confirmation open for the parent to handle errors', async () => {
    const wrapper = mount(UiConfirmDialog, {
      props: { modelValue: true, title: 'Konfirmasi', description: 'Contoh', busy: false },
    })
    await nextTick()
    const button = document.querySelector<HTMLButtonElement>('.button-danger-solid')!
    expect(button.classList.contains('button-danger')).toBe(false)
    button.click()
    expect(wrapper.emitted('confirm')).toHaveLength(1)
    expect(document.querySelector('dialog')?.hasAttribute('open')).toBe(true)
    await wrapper.setProps({ busy: true })
    const dialog = document.querySelector('dialog')!
    dialog.dispatchEvent(new Event('cancel', { cancelable: true }))
    await nextTick()
    expect(dialog.hasAttribute('open')).toBe(true)
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })
  it('renders untrusted output as text', () => {
    const code = '<img src=x onerror=alert(1)>'
    const wrapper = mount(UiCodeBlock, { props: { code, label: 'Output', copyable: false } })
    expect(wrapper.get('code').text()).toBe(code)
    expect(wrapper.find('img').exists()).toBe(false)
  })
  it('reports clipboard denial without claiming success', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockRejectedValue(new Error('Denied')) },
    })
    const wrapper = mount(UiCopyButton, { props: { value: 'Contoh biasa' } })
    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('Clipboard tidak tersedia')
    expect(wrapper.get('button').text()).toBe('Salin')
  })
  it('finds tools by aliases and fuzzy label, including no matches', () => {
    expect(
      commandNavigation.filter((item) => matchesCommand(item, 'laporan')).map((item) => item.label),
    ).toContain('QA Reports')
    expect(commandNavigation.filter((item) => matchesCommand(item, 'zzzzzzzz'))).toHaveLength(0)
  })
  it('persists only the theme preference and restores it on initialize', () => {
    setActivePinia(createPinia())
    const ui = useUiStore()
    ui.setTheme('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem('qa-portal:theme')).toBe('dark')
    setActivePinia(createPinia())
    const next = useUiStore()
    const cleanup = next.initialize()
    expect(next.theme).toBe('dark')
    cleanup()
  })
  it('keeps theme switching usable when browser storage is blocked', () => {
    setActivePinia(createPinia())
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('Blocked')
    })
    const ui = useUiStore()
    expect(() => ui.setTheme('dark')).not.toThrow()
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(ui.preferenceError).toContain('selama sesi ini')
  })
})
