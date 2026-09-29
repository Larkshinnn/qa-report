<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { useUiStore } from '../../stores/ui'
import UiButton from '../ui/UiButton.vue'
import { errorMessage } from '../../api'
import UiCard from '../ui/UiCard.vue'
import UiModal from '../ui/UiModal.vue'
import UiSkeleton from '../ui/UiSkeleton.vue'
import UiErrorState from '../ui/UiErrorState.vue'
import LoginForm from './LoginForm.vue'

const auth = useAuthStore()
const ui = useUiStore()
const loading = ref(true)
const error = ref('')
const expired = computed(() => auth.everAuthenticated && !auth.authenticated)

function toggleTheme(): void {
  ui.setTheme(ui.theme === 'dark' ? 'light' : 'dark')
}

async function check(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    await auth.check()
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}

function expire(): void {
  auth.authenticated = false
}

onMounted(() => {
  void check()
  window.addEventListener('qa:session-expired', expire)
})
onUnmounted(() => window.removeEventListener('qa:session-expired', expire))
</script>

<template>
  <template v-if="auth.authenticated || auth.everAuthenticated">
    <slot />
    <UiModal
      :model-value="expired"
      title="Masuk kembali"
      description="Sesi berakhir. Isian yang belum disimpan tetap ada di halaman ini."
      :dismissible="false"
      size="sm"
    >
      <LoginForm />
    </UiModal>
  </template>
  <main
    v-else-if="!loading"
    class="auth-page"
  >
    <div class="auth-intro">
      <div class="auth-heading">
        <span class="auth-mark">QA REPORT / PRIVATE</span>
        <UiButton
          variant="ghost"
          size="sm"
          @click="toggleTheme"
        >
          {{ ui.theme === 'dark' ? 'Tema terang' : 'Tema gelap' }}
        </UiButton>
      </div>
      <h1>Catat pekerjaan QA dengan rapi.</h1>
      <p>Laporanmu dipisahkan berdasarkan akun dan siap diekspor kapan saja.</p>
    </div>
    <UiCard
      class="auth-card"
      padding="lg"
    >
      <UiErrorState
        v-if="error"
        :message="error"
        retryable
        @retry="check"
      />
      <template v-else>
        <h2>Masuk ke QA Report</h2>
        <p class="muted small auth-description">
          Gunakan akun Google yang diizinkan untuk melanjutkan.
        </p>
        <LoginForm />
      </template>
    </UiCard>
    <p class="muted small">Data laporan hanya dapat diakses oleh akunmu.</p>
  </main>
  <main
    v-else
    class="auth-page"
  >
    <UiCard
      class="auth-card"
      padding="lg"
    >
      <UiSkeleton
        :lines="4"
        label="Memeriksa sesi"
      />
    </UiCard>
  </main>
</template>

<style scoped>
.auth-page {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 24px;
  padding: 40px 20px;
  background: var(--color-page);
}
.auth-intro,
.auth-card {
  width: 100%;
  max-width: 460px;
}
.auth-intro h1 {
  font-size: 34px;
  line-height: 1.1;
  margin: 28px 0 12px;
}
.auth-intro p {
  color: var(--color-text-muted);
  line-height: 1.7;
}
.auth-mark {
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.14em;
  border-bottom: 1px solid var(--color-accent);
  padding-bottom: 5px;
}
.auth-description {
  margin: 12px 0 24px;
  line-height: 1.6;
}
.auth-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}
</style>
