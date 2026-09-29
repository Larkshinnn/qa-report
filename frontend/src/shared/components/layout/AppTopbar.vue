<script setup lang="ts">
import { useRoute } from 'vue-router'
import { PhList, PhMagnifyingGlass, PhCaretRight } from '@phosphor-icons/vue'
import { useUiStore } from '../../stores/ui'
import { useAuthStore } from '../../stores/auth'
import UiButton from '../ui/UiButton.vue'
const emit = defineEmits<{ menu: [] }>()
const ui = useUiStore()
const auth = useAuthStore()
const route = useRoute()
</script>
<template>
  <header class="app-topbar">
    <div class="topbar-context">
      <UiButton
        class="mobile-toggle"
        variant="ghost"
        icon-only
        label="Buka navigasi"
        @click="emit('menu')"
      >
        <PhList :size="22" />
      </UiButton>
      <div
        class="breadcrumb"
        aria-label="Lokasi halaman"
      >
        <span>WORKBENCH</span>
        <PhCaretRight
          :size="11"
          aria-hidden="true"
        />
        <strong>{{ route.meta.title ?? 'Halaman' }}</strong>
      </div>
    </div>
    <div class="topbar-actions">
      <span class="connection-context">{{ auth.email }}</span>
      <UiButton
        variant="secondary"
        label="Cari halaman atau alat"
        @click="ui.paletteOpen = true"
      >
        <PhMagnifyingGlass :size="17" />
        <span class="search-label">Cari di QA Report</span>
        <kbd>Ctrl K</kbd>
      </UiButton>
      <UiButton
        variant="ghost"
        size="sm"
        @click="auth.logout"
      >
        Keluar
      </UiButton>
    </div>
  </header>
</template>
<style scoped>
.app-topbar {
  position: sticky;
  top: 0;
  z-index: calc(var(--layer-header) - 1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-height: 68px;
  padding: 0 32px;
  background: color-mix(in srgb, var(--color-surface) 96%, transparent);
  border-bottom: 1px solid var(--color-border-strong);
}
.topbar-context,
.breadcrumb,
.topbar-actions,
.connection-context {
  display: flex;
  align-items: center;
}
.breadcrumb {
  gap: 10px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  color: var(--color-text-muted);
  text-transform: uppercase;
}
.breadcrumb strong {
  color: var(--color-text);
  font-weight: 500;
}
.topbar-actions {
  gap: 14px;
}
.connection-context {
  gap: 7px;
  padding-right: 14px;
  border-right: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: 13px;
}
.connection-context:hover {
  color: var(--color-primary);
}
.mobile-toggle {
  display: none;
}
.app-topbar :deep(.button-secondary) {
  min-height: 38px;
  padding: 7px 10px;
  background: transparent;
  font-size: 13px;
}
.app-topbar kbd {
  margin-left: 5px;
}
@media (max-width: 1000px) {
  .app-topbar {
    padding: 0 22px;
  }
  .connection-context {
    display: none;
  }
}
@media (max-width: 767px) {
  .app-topbar {
    min-height: 60px;
    padding: 0 10px;
  }
  .mobile-toggle {
    display: inline-flex;
  }
  .topbar-context {
    flex: 1;
  }
  .breadcrumb > span,
  .breadcrumb > svg,
  .search-label,
  kbd {
    display: none;
  }
  .app-topbar :deep(.button-secondary) {
    width: 42px;
    padding: 0;
  }
}
</style>
