import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  defaultPalette,
  normalizePalette,
  paletteTokens,
  samePalette,
  type Palette,
} from '../palettes'

export type ThemePreference = 'light' | 'dark' | 'system'

export const useUiStore = defineStore('ui', () => {
  const theme = ref<ThemePreference>('light')
  const paletteOpen = ref(false)
  const sidebarCollapsed = ref(false)
  const preferenceError = ref('')
  const colorPalette = ref<Palette | null>(null)
  const colorPaletteError = ref('')
  const resolvedTheme = ref<'light' | 'dark'>('light')

  function applyTheme(): void {
    const dark =
      theme.value === 'dark' ||
      (theme.value === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
    document.documentElement.dataset.theme = dark ? 'dark' : 'light'
    resolvedTheme.value = dark ? 'dark' : 'light'
    for (const [key, value] of Object.entries(
      paletteTokens(colorPalette.value ?? defaultPalette, dark),
    )) {
      if (colorPalette.value) document.documentElement.style.setProperty(key, value)
      else document.documentElement.style.removeProperty(key)
    }
  }
  function setColorPalette(value: Palette): boolean {
    const normalized = normalizePalette(value)
    if (!normalized) {
      colorPaletteError.value = 'Isi keempat warna dengan kode HEX yang valid.'
      return false
    }
    colorPalette.value = samePalette(normalized, defaultPalette) ? null : normalized
    applyTheme()
    try {
      if (colorPalette.value)
        localStorage.setItem('qa-portal:color-palette', JSON.stringify(colorPalette.value))
      else localStorage.removeItem('qa-portal:color-palette')
      colorPaletteError.value = ''
    } catch {
      colorPaletteError.value =
        'Browser tidak mengizinkan penyimpanan. Palet berlaku selama sesi ini.'
    }
    return true
  }
  function setTheme(value: ThemePreference): void {
    theme.value = value
    applyTheme()
    try {
      localStorage.setItem('qa-portal:theme', value)
      preferenceError.value = ''
    } catch {
      preferenceError.value = 'Browser tidak mengizinkan penyimpanan. Tema berlaku selama sesi ini.'
    }
  }
  function initialize(): () => void {
    try {
      const stored = localStorage.getItem('qa-portal:theme')
      if (stored === 'dark' || stored === 'light' || stored === 'system') theme.value = stored
    } catch {
      /* Private browsing may disable storage; light mode remains usable. */
    }
    try {
      const stored = localStorage.getItem('qa-portal:color-palette')
      const colors = stored ? normalizePalette(JSON.parse(stored)) : null
      colorPalette.value = colors && !samePalette(colors, defaultPalette) ? colors : null
    } catch {
      colorPalette.value = null
    }
    applyTheme()
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    media.addEventListener('change', applyTheme)
    return () => media.removeEventListener('change', applyTheme)
  }
  return {
    theme,
    resolvedTheme,
    colorPalette,
    colorPaletteError,
    setColorPalette,
    paletteOpen,
    sidebarCollapsed,
    preferenceError,
    setTheme,
    initialize,
  }
})
