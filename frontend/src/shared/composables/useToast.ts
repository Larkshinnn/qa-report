import { readonly, ref } from 'vue'

const messages = ref<{ id: number; message: string }[]>([])
let sequence = 0

// Notifications contain confirmations only. Important errors stay beside their control.
export function useToast() {
  function dismiss(id: number): void {
    messages.value = messages.value.filter((item) => item.id !== id)
  }
  function notify(message: string): void {
    const id = ++sequence
    messages.value.push({ id, message })
    setTimeout(() => dismiss(id), 5000)
  }
  return { messages: readonly(messages), notify, dismiss }
}
