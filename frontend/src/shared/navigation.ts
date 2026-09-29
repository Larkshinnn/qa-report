import {
  PhClipboardText,
} from '@phosphor-icons/vue'
import type { Component } from 'vue'

export type NavigationItem = { label: string; path: string; icon: Component; keywords: string }
export const primaryNavigation: NavigationItem[] = [
  {
    label: 'QA Reports',
    path: '/qa-reports',
    icon: PhClipboardText,
    keywords: 'laporan testing harian',
  },
]
export const secondaryNavigation: NavigationItem[] = []
export const commandNavigation = [...primaryNavigation]

export function matchesCommand(item: NavigationItem, query: string): boolean {
  const haystack = `${item.label} ${item.keywords}`.toLocaleLowerCase()
  return query
    .trim()
    .toLocaleLowerCase()
    .split(/\s+/)
    .every((word) => {
      let at = 0
      for (const char of word) {
        const found = haystack.indexOf(char, at)
        if (found < 0) return false
        at = found + 1
      }
      return true
    })
}
