<template>
  <div class="border-t border-gray-600 p-4 w-full">
    <div class="relative flex items-center">
      <input
      type="text"
      v-model="inputText"
      @keydown.enter="handleSend"
      :placeholder="placeholderText"
      :disabled="!isSocketConnected"
      class="w-full px-4 py-3 border border-gray-300 rounded-l-full focus:outline-none focus:ring-2 focus:ring-[#8095CA] transition-shadow duration-200 text-gray-800 bg-white"
      />
      
      <button
        @click="handleSend"
        :disabled="!isSocketConnected || !inputText.trim()"
        class="px-6 py-3 bg-[#8095CA] text-white font-semibold rounded-r-full shadow-md hover:bg-[#6D8DBE] focus:outline-none disabled:bg-gray-400 transition-colors duration-200"
      >
        <span v-if="isPaused">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
          </svg>
        </span>
        <span v-else>
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
        </span>
      </button>

      <div class="relative flex-1 flex items-center">
        <input
        type="text"
        v-model="inputText"
        @keyup="onKeyup"
        :placeholder="placeholderText"
        :disabled="!isSocketConnected"
        class="w-full px-4 py-3 border border-gray-300 rounded-l-full focus:outline-none focus:ring-2 focus:ring-[#8095CA] transition-shadow duration-200 text-gray-800 bg-white"
        />
        
        <button
          @click="handleSend"
          :disabled="!isSocketConnected || !inputText.trim()"
          class="px-6 py-3 bg-[#8095CA] text-white font-semibold rounded-r-full shadow-md hover:bg-[#6D8DBE] focus:outline-none disabled:bg-gray-400 transition-colors duration-200"
        >
          发送
        </button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const emit = defineEmits(['send-message', 'toggle-pause'])

const props = defineProps({
  isSocketConnected: {
    type: Boolean,
    required: true,
  },
  isPaused: {
    type: Boolean,
    default: false
  },
  hasMessages: {
    type: Boolean,
    default: false
  }
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
