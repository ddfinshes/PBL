<template>
  <div class="border-t border-gray-600 p-4 w-full">
    <input
      type="text"
      v-model="inputText"
      @keydown.enter="handleSend"
      :placeholder="placeholderText"
      :disabled="!isSocketConnected"
      class="w-full px-4 py-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-shadow duration-200"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  isSocketConnected: {
    type: Boolean,
    required: true,
  },
})

const emit = defineEmits(['send-message'])

const inputText = ref('')

const placeholderText = computed(() =>
  props.isSocketConnected ? '输入干预指令，按回车发送...' : '正在连接服务器...'
)

const handleSend = () => {
  if (inputText.value.trim() && props.isSocketConnected) {
    emit('send-message', inputText.value.trim())
    inputText.value = '' // 清空输入框
  }
}
</script>
