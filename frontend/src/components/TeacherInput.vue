<template>
  <div class="border-t border-gray-600 p-4 w-full">
    <div class="relative flex items-center">
      <input
      type="text"
      v-model="inputText"
      @keyup="onKeyup"
      :placeholder="placeholderText"
      :disabled="!isSocketConnected"
      class="w-full px-4 py-3 border border-gray-300 rounded-l-full focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-shadow duration-200"
      />
      
      <button
        @click="handleSend"
        :disabled="!isSocketConnected || !inputText.trim()"
        class="px-6 py-3 bg-indigo-600 text-white font-semibold rounded-r-full shadow-md hover:bg-indigo-700 focus:outline-none disabled:bg-gray-400 transition-colors duration-200"
      >
        发送
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const emit = defineEmits(['send-message'])

const props = defineProps({
  isSocketConnected: {
    type: Boolean,
    required: true,
  },
})

const inputText = ref('')

const placeholderText = computed(() =>
  props.isSocketConnected ? '输入干预指令，按回车发送...' : '正在连接服务器...'
)

const onKeyup = (event) => {
  console.log('Keyup event:', event.key, 'isComposing:', event.isComposing);
  if (event.key === 'Enter' && !event.isComposing) {
    handleSend()
  }
}

const handleSend = () => {
  console.log('输入内容：', inputText.value.trim())
  console.log('输入内容：', props.isSocketConnected)
  if (inputText.value.trim() && props.isSocketConnected) {
    emit('send-message', inputText.value.trim())
    inputText.value = '' // 清空输入框
  }
}
</script>
