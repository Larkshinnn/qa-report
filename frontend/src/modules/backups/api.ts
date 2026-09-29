import { api, apiFile } from '../../shared/api'
import type { Palette, SavedPalette } from '../../shared/palettes'
import type { ThemePreference } from '../../shared/stores/ui'

export interface ThemeBackup {
  theme: ThemePreference
  color_palette: Palette | null
  saved_palettes: SavedPalette[]
}

export interface ImportPreview {
  exported_at: string
  reports: number
  templates: number
  vault_entries: number
  has_theme: boolean
  has_existing_data: boolean
  vault_mergeable: boolean
  existing_reports: number
  existing_templates: number
  existing_vault_entries: number
  new_reports: number
  new_templates: number
  new_vault_entries: number
}

export interface ImportResult {
  mode: 'missing' | 'overwrite'
  reports_restored: number
  reports_skipped: number
  vault_restored: number
  vault_skipped: number
  theme: ThemeBackup
}

const base = '/backups'

export const backupApi = {
  download: (theme: ThemeBackup): Promise<Blob> =>
    apiFile(base, { method: 'POST', body: JSON.stringify(theme) }),
  preview: (archive: Blob): Promise<ImportPreview> =>
    api(`${base}/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/zip' },
      body: archive,
    }),
  restore: (archive: Blob, mode: 'missing' | 'overwrite'): Promise<ImportResult> =>
    api(`${base}/import?${new URLSearchParams({ mode })}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/zip' },
      body: archive,
    }),
}

export function backupFilename(date = new Date()): string {
  const part = (value: number) => String(value).padStart(2, '0')
  return `backup_${date.getFullYear()}${part(date.getMonth() + 1)}${part(date.getDate())}_${part(date.getHours())}${part(date.getMinutes())}${part(date.getSeconds())}.zip`
}
