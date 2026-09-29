<script setup lang="ts">
import UiEmptyState from '../components/ui/UiEmptyState.vue'
</script>
<template>
  <UiEmptyState
    title="Halaman tidak ditemukan"
    description="Alamat ini belum tersedia di workspace."
  >
    <template #action>
      <RouterLink
        to="/"
        class="text-link"
      >
        Kembali ke dashboard
      </RouterLink>
    </template>
  </UiEmptyState>
</template>
