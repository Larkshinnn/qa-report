<script setup lang="ts">
import { onUnmounted } from 'vue'
import AppShell from './shared/components/layout/AppShell.vue'
import AuthGate from './shared/components/auth/AuthGate.vue'
import { useUiStore } from './shared/stores/ui'
const cleanup = useUiStore().initialize()
onUnmounted(cleanup)
</script>
<template>
  <AuthGate><AppShell /></AuthGate>
</template>
