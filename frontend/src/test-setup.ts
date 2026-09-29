import { afterEach, vi } from 'vitest'
import { enableAutoUnmount } from '@vue/test-utils'

enableAutoUnmount(afterEach)

// jsdom does not implement native modal behavior; focus/inert are checked in a real browser.
HTMLDialogElement.prototype.showModal = function (): void {
  this.setAttribute('open', '')
}
HTMLDialogElement.prototype.close = function (): void {
  this.removeAttribute('open')
  this.dispatchEvent(new Event('close'))
}
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })),
})
afterEach(() => {
  document.body.innerHTML = ''
  localStorage.clear()
  vi.restoreAllMocks()
})
