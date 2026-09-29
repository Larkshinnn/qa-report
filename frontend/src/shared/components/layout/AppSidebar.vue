<script setup lang="ts">
import { useRoute } from 'vue-router'
import { PhArrowLeft, PhArrowRight, PhDesktop } from '@phosphor-icons/vue'
import { primaryNavigation, secondaryNavigation } from '../../navigation'
import { useUiStore } from '../../stores/ui'
import UiButton from '../ui/UiButton.vue'
defineProps<{ mobile?: boolean }>()
const route = useRoute()
const ui = useUiStore()
function selected(path: string): boolean {
  return path === '/' ? route.path === '/' : route.path.startsWith(path)
}
</script>
<template>
  <aside
    :class="[
      'app-sidebar',
      { 'is-collapsed': ui.sidebarCollapsed && !mobile, 'is-mobile': mobile },
    ]"
    aria-label="Sidebar"
  >
    <RouterLink
      to="/qa-reports"
      class="product-brand"
      aria-label="QA Report"
    >
      <span
        class="product-mark"
        aria-hidden="true"
      >
        QA
      </span>
      <span class="brand-copy">
        QA Report
        <small>QA WORKSPACE</small>
      </span>
    </RouterLink>
    <div class="sidebar-content">
      <p class="nav-label">INDEX / QA WORKSPACE</p>
      <nav aria-label="Navigasi utama">
        <RouterLink
          v-for="item in primaryNavigation"
          :key="item.path"
          :to="item.path"
          :class="['nav-item', { selected: selected(item.path) }]"
          :aria-current="selected(item.path) ? 'page' : undefined"
          :aria-label="item.label"
          :title="ui.sidebarCollapsed && !mobile ? item.label : undefined"
        >
          <component
            :is="item.icon"
            :size="19"
            :weight="selected(item.path) ? 'fill' : 'regular'"
            aria-hidden="true"
          />
          <span class="nav-copy">{{ item.label }}</span>
        </RouterLink>
      </nav>
      <nav
        aria-label="Preferensi dan komponen"
        class="secondary-nav"
      >
        <RouterLink
          v-for="item in secondaryNavigation"
          :key="item.path"
          :to="item.path"
          :class="['nav-item', { selected: selected(item.path) }]"
          :aria-current="selected(item.path) ? 'page' : undefined"
          :aria-label="item.label"
          :title="ui.sidebarCollapsed && !mobile ? item.label : undefined"
        >
          <component
            :is="item.icon"
            :size="19"
            aria-hidden="true"
          />
          <span class="nav-copy">{{ item.label }}</span>
        </RouterLink>
      </nav>
    </div>
    <div class="sidebar-footer">
      <PhDesktop
        :size="18"
        aria-hidden="true"
      />
      <div class="footer-copy">
          <strong>Shared workspace</strong>
          <small>Ringkasan tim · data personal terjaga</small>
      </div>
      <UiButton
        v-if="!mobile"
        icon-only
        variant="ghost"
        :label="ui.sidebarCollapsed ? 'Perluas sidebar' : 'Ringkas sidebar'"
        @click="ui.sidebarCollapsed = !ui.sidebarCollapsed"
      >
        <component
          :is="ui.sidebarCollapsed ? PhArrowRight : PhArrowLeft"
          :size="15"
        />
      </UiButton>
    </div>
  </aside>
</template>
<style scoped>
.app-sidebar {
  height: 100%;
  overflow: hidden;
  background: var(--color-sidebar);
  color: var(--color-sidebar-text);
  display: flex;
  flex-direction: column;
  border-right: 1px solid color-mix(in srgb, var(--color-sidebar-text) 18%, transparent);
}
.product-brand {
  display: flex;
  align-items: center;
  gap: 13px;
  min-height: 112px;
  padding: 27px 22px;
  flex-shrink: 0;
  border-bottom: 1px solid color-mix(in srgb, var(--color-sidebar-text) 18%, transparent);
}
.product-mark {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border: 1px solid color-mix(in srgb, var(--color-sidebar-text) 58%, transparent);
  border-radius: 50%;
  font-family: var(--font-mono);
  font-size: 13px;
  letter-spacing: -0.08em;
}
.brand-copy {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: -0.025em;
  white-space: nowrap;
}
.brand-copy small {
  display: block;
  margin-top: 4px;
  color: var(--color-sidebar-muted);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.13em;
}
.sidebar-content {
  padding: 26px 14px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior-y: contain;
}
.nav-label {
  margin: 0 10px 13px;
  color: var(--color-sidebar-muted);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
}
nav {
  display: grid;
  gap: 3px;
}
.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 44px;
  padding: 10px 12px;
  border-radius: var(--radius-control);
  color: var(--color-sidebar-muted);
  font-size: 14px;
  transition:
    color var(--duration-fast) var(--ease-out),
    background-color var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}
.nav-item:hover {
  color: var(--color-sidebar-text);
  background: color-mix(in srgb, var(--color-sidebar-text) 7%, transparent);
  transform: translateX(2px);
}
.nav-item.selected {
  background: var(--color-sidebar-active);
  color: var(--color-ink);
  font-weight: 600;
}
.nav-item.selected::before {
  content: '';
  position: absolute;
  inset: 10px auto 10px -14px;
  width: 3px;
  background: var(--color-accent);
}
.secondary-nav {
  margin-top: 28px;
  padding-top: 22px;
  border-top: 1px solid color-mix(in srgb, var(--color-sidebar-text) 16%, transparent);
}
.sidebar-footer {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 14px;
  border-top: 1px solid color-mix(in srgb, var(--color-sidebar-text) 18%, transparent);
  color: var(--color-sidebar-muted);
}
.sidebar-footer :deep(.ui-button) {
  color: var(--color-sidebar-muted);
}
.sidebar-footer :deep(.ui-button:hover) {
  color: var(--color-sidebar-text);
  background: color-mix(in srgb, var(--color-sidebar-text) 8%, transparent);
}
.footer-copy {
  flex: 1;
}
.footer-copy strong {
  display: block;
  color: var(--color-sidebar-text);
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}
.footer-copy small {
  display: block;
  margin-top: 3px;
  font-size: 11px;
  white-space: nowrap;
}
.is-collapsed .nav-copy,
.is-collapsed .brand-copy,
.is-collapsed .nav-label,
.is-collapsed .footer-copy,
.is-collapsed .sidebar-footer > svg {
  display: none;
}
.is-collapsed .product-brand {
  justify-content: center;
  padding-inline: 12px;
}
.is-collapsed .sidebar-content {
  padding: 26px 10px;
}
.is-collapsed .nav-item,
.is-collapsed .sidebar-footer {
  justify-content: center;
}
.is-collapsed .nav-item.selected::before {
  left: -10px;
}
.is-mobile {
  height: auto;
  overflow: visible;
  border: 0;
  background: transparent;
  color: var(--color-text);
}
.is-mobile .product-brand {
  display: none;
}
.is-mobile .sidebar-content {
  overflow: visible;
  padding: 0 0 20px;
}
.is-mobile .nav-label,
.is-mobile .nav-item,
.is-mobile .sidebar-footer,
.is-mobile .footer-copy strong {
  color: var(--color-text-muted);
}
.is-mobile .nav-item.selected {
  color: var(--color-primary);
  background: var(--color-surface-subtle);
}
.is-mobile .nav-item:hover {
  color: var(--color-text);
  background: var(--color-surface-subtle);
}
.is-mobile .secondary-nav,
.is-mobile .sidebar-footer {
  border-color: var(--color-border);
}
.is-mobile .sidebar-footer {
  padding-bottom: 0;
}
</style>
