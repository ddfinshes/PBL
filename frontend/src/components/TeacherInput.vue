<template>
  <div class="border-t border-gray-600 p-4 w-full bg-[#1a1f3a]">
    <div class="flex items-center gap-3">
      <!-- 暂停/继续按钮 -->
      <button
        @click="$emit('toggle-pause')"
        :disabled="!isSocketConnected || !hasMessages"
        class="p-3 rounded-full bg-gray-700/30 hover:bg-gray-600/50 transition-colors border border-gray-500/30 text-white disabled:opacity-40"
        :title="isPaused ? '恢复讨论' : '暂停讨论'"
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

      <!-- 输入框容器 -->
      <div class="relative flex-1 flex items-center">
        <input
          type="text"
          v-model="inputText"
          @keydown.enter="handleKeydownEnter"
          :placeholder="placeholderText"
          :disabled="!isSocketConnected"
          class="w-full px-5 py-3 border border-gray-500/30 rounded-l-full focus:outline-none focus:ring-2 focus:ring-[#8095CA] transition-all text-white bg-gray-800/50 placeholder-gray-400"
        />
        
        <!-- 发送按钮 -->
        <button
          @click="handleSend"
          :disabled="!isSocketConnected || !inputText.trim()"
          class="px-6 py-3 bg-[#8095CA] hover:bg-[#6D8DBE] text-white font-bold rounded-r-full shadow-lg disabled:bg-gray-600 disabled:opacity-50 transition-all active:scale-95"
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
  props.isSocketConnected ? '输入教师干预指令，按回车发送...' : '正在连接讨论服务器...'
)

const handleKeydownEnter = (event) => {
  if (event.isComposing) return
  handleSend()
}

const handleSend = () => {
  if (inputText.value.trim() && props.isSocketConnected) {
    emit('send-message', inputText.value.trim())
    inputText.value = '' // 清空输入框
  }
}
</script>

