<script setup lang="ts">
defineProps<{ items: { label: string; to?: string }[] }>()
</script>
<template>
  <nav
    aria-label="Breadcrumb"
    class="breadcrumbs"
  >
    <ol>
      <li
        v-for="(item, index) in items"
        :key="index"
      >
        <span
          v-if="index"
          aria-hidden="true"
          class="separator"
        >
          /
        </span>
        <RouterLink
          v-if="item.to && index < items.length - 1"
          :to="item.to"
        >
          {{ item.label }}
        </RouterLink>
        <span
          v-else
          :aria-current="index === items.length - 1 ? 'page' : undefined"
        >
          {{ item.label }}
        </span>
      </li>
    </ol>
  </nav>
</template>
<style scoped>
.breadcrumbs {
  margin-bottom: 20px;
  font-size: 14px;
  color: var(--color-text-muted);
}
ol,
li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
ol {
  list-style: none;
  padding: 0;
  margin: 0;
}
li {
  min-width: 0;
}
li > span:last-child {
  overflow-wrap: anywhere;
}
a {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  color: var(--color-primary);
  text-decoration: underline;
  text-underline-offset: 4px;
}
.separator {
  padding: 0 4px;
}
</style>
