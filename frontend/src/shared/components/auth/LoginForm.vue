<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { errorMessage } from '../../api'
import UiButton from '../ui/UiButton.vue'
import UiErrorState from '../ui/UiErrorState.vue'

const auth = useAuthStore()
const busy = ref(false)
const error = ref('')

function login(): void {
  error.value = ''
  busy.value = true
  try {
    auth.loginWithGoogle()
  } catch (cause) {
    busy.value = false
    error.value = errorMessage(cause)
  }
}
</script>

<template>
  <div class="stack">
    <UiErrorState
      v-if="error"
      :message="error"
    />
    <UiButton
      type="button"
      :loading="busy"
      @click="login"
    >
      Lanjutkan dengan Google
    </UiButton>
  </div>
</template>
