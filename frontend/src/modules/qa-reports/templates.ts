import type { ItemInput, ReportMetadata } from './api'

export const templateTokens = [
  ['report_title', 'Judul laporan', 1],
  ['report_date', 'Tanggal', 1],
  ['author_name', 'Nama pelapor', 1],
  ['activity_code', 'Kode tiket', 1],
  ['environment', 'Environment', 1],
  ['result', 'Hasil', 1],
  ['coverage_links', 'Link coverage', 2],
  ['current_issue', 'Issue', 3],
  ['current_status', 'Status terkini', 3],
] as const
const reportKeys = new Set<string>(['report_title', 'report_date', 'author_name'])
const activityKeys = new Set<string>(
  templateTokens.map(([key]) => key).filter((key) => !reportKeys.has(key)),
)
const tokenPattern = /\{\{([\s\S]*?)\}\}/g
const keyPattern = /^[a-z][a-z0-9_]{0,49}$/
const blockPattern = /\{\{\s*#activities\s*\}\}([\s\S]*?)\{\{\s*\/activities\s*\}\}/g
const standaloneBlockPattern = /^[ \t]*(\{\{\s*(?:#|\/)activities\s*\}\})[ \t]*(?:\r?\n|$)/gm

export const starterBody = `{{report_title}}
Date: {{report_date}}

Testing Summary:
{{#activities}}- {{activity_code}} · {{environment}} · {{result}}
{{/activities}}
Test Coverage:
{{#activities}}- {{activity_code}}: {{coverage_links}}
{{/activities}}
Current issues:
{{#activities}}- {{activity_code}}: {{current_issue}}
{{/activities}}
Current Status:
{{#activities}}- {{activity_code}}: {{current_status}}
{{/activities}}`

export function normalizeTemplate(body: string): string {
  return body.replace(tokenPattern, (token) => token.replaceAll('\\_', '_'))
}

// Keep first-appearance order; the same key is filled once within each scope.
export function templateFields(body: string): {
  report: string[]
  activity: string[]
  hasActivities: boolean
} {
  body = normalizeTemplate(body)
  const keys = (text: string) => [
    ...new Set(
      [...text.matchAll(tokenPattern)]
        .map((match) => match[1]!.trim())
        .filter((key) => keyPattern.test(key)),
    ),
  ]
  const blocks = [...body.matchAll(blockPattern)]
  return {
    report: keys(body.replace(blockPattern, '')).filter((key) => !reportKeys.has(key)),
    activity: keys(blocks.map((block) => block[1]).join('\n')).filter(
      (key) => !reportKeys.has(key),
    ),
    hasActivities: blocks.length > 0,
  }
}

export function customKeys(body: string): string[] {
  return [
    ...new Set(
      [...normalizeTemplate(body).matchAll(tokenPattern)]
        .map((match) => match[1]!.trim())
        .filter((key) => keyPattern.test(key) && !reportKeys.has(key) && !activityKeys.has(key)),
    ),
  ]
}
export function fieldLabel(key: string): string {
  return key.charAt(0).toUpperCase() + key.slice(1).replaceAll('_', ' ')
}
export function templateError(body: string): string {
  body = normalizeTemplate(body)
  if (!body.trim() || body.length > 20000)
    return 'Isi template wajib diisi, maksimal 20.000 karakter.'
  const remainder = body.replace(tokenPattern, '')
  if (remainder.includes('{{') || remainder.includes('}}'))
    return 'Placeholder belum ditutup. Gunakan {{nama_placeholder}}.'
  let inBlock = false,
    blocks = 0
  for (const match of body.matchAll(tokenPattern)) {
    const token = match[1]!.trim()
    if (token === '#activities') {
      if (inBlock) return 'Blok aktivitas tidak boleh bersarang.'
      inBlock = true
      blocks++
    } else if (token === '/activities') {
      if (!inBlock) return 'Penutup blok aktivitas tidak memiliki pembuka.'
      inBlock = false
    } else if (!keyPattern.test(token))
      return 'Nama placeholder memakai huruf kecil, angka, dan underscore.'
    else if (activityKeys.has(token) && !inBlock)
      return `{{${token}}} harus berada di dalam blok aktivitas.`
  }
  if (inBlock) return 'Tutup blok aktivitas dengan {{/activities}}.'
  if (blocks > 12 || customKeys(body).length > 30)
    return 'Maksimal 12 blok aktivitas dan 30 placeholder tambahan.'
  return ''
}

export function renderTemplate(
  body: string,
  report: ReportMetadata,
  items: ItemInput[],
  values: Record<string, string> = {},
): string {
  body = normalizeTemplate(body)
  if (templateError(body)) return ''
  body = body.replace(standaloneBlockPattern, '$1')
  const reportValues = {
    ...values,
    report_title: report.title,
    author_name: report.author_name || '',
    report_date: new Intl.DateTimeFormat('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    }).format(new Date(`${report.report_date}T12:00:00`)),
  }
  const fill = (source: string, data: Record<string, string>) =>
    source.replace(tokenPattern, (_, key: string) =>
      Object.hasOwn(data, key.trim()) ? (data[key.trim()] ?? '') : '',
    )
  const pieces: string[] = []
  let cursor = 0,
    size = 0
  const append = (text: string) => {
    size += text.length
    if (size > 2000000)
      throw new Error('Hasil template terlalu panjang. Kurangi blok atau isian laporan.')
    pieces.push(text)
  }
  for (const block of body.matchAll(blockPattern)) {
    append(fill(body.slice(cursor, block.index), reportValues))
    for (const item of items) {
      append(
        fill(block[1]!, {
          ...reportValues,
          ...Object.fromEntries(
            Object.entries(item.template_values ?? {}).filter(
              ([key]) => !reportKeys.has(key) && !activityKeys.has(key),
            ),
          ),
          activity_code: item.activity_code,
          environment: item.environment,
          result: item.result,
          current_status: item.current_status || item.result,
          current_issue: item.current_issue || '',
          coverage_links: item.links.map((link) => link.url).join('\n'),
        }),
      )
    }
    cursor = block.index + block[0].length
  }
  append(fill(body.slice(cursor), reportValues))
  return pieces.join('').trim()
}

export function rememberedTemplate(): string {
  try {
    return localStorage.getItem('qa-report-template') ?? ''
  } catch {
    return ''
  }
}
export function rememberTemplate(id: string): void {
  try {
    localStorage.setItem('qa-report-template', id)
  } catch {
    /* Preference storage is optional. */
  }
}
