<template>
  <div class="border-t border-gray-300 p-4 w-full bg-[#D9D9D9]">
    <!-- Loading Overlay -->
    <div v-if="isGenerating" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/20 backdrop-blur-[2px]">
      <div class="bg-white p-6 rounded-2xl shadow-2xl flex flex-col items-center space-y-4 animate-in zoom-in duration-300">
        <div class="relative w-16 h-16">
          <div class="absolute inset-0 border-4 border-gray-100 rounded-full"></div>
          <div class="absolute inset-0 border-4 border-[#8095CA] border-t-transparent rounded-full animate-spin"></div>
        </div>
        <div class="text-center">
          <h3 class="text-lg font-bold text-gray-800">正在生成干预策略...</h3>
          <p class="text-sm text-gray-500">正在调用 LLM 并行分析讨论背景</p>
        </div>
      </div>
    </div>

    <div class="flex items-center gap-3">
      <!-- Pause/Resume Button -->
      <button
        @click="$emit('toggle-pause')"
        :disabled="!isSocketConnected || !hasMessages"
        class="p-3 rounded-full bg-gray-700/30 hover:bg-gray-600/50 transition-colors border border-gray-500/30 text-white disabled:opacity-40"
        :title="isPaused ? 'Resume discussion' : 'Pause discussion'"
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

      <!-- Recommend Button -->
      <div class="relative group">
        <button
          @click="generateSuggestions"
          :disabled="!isSocketConnected || !hasMessages || isGenerating"
          class="p-3 rounded-full bg-[#8095CA]/30 hover:bg-[#8095CA]/50 transition-colors border border-[#8095CA]/40 text-[#8095CA] disabled:opacity-40 flex items-center justify-center"
          title="Recommend intervention strategy"
        >
          <svg v-if="isGenerating" class="animate-spin h-6 w-6 text-[#8095CA]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.364-6.364l-.707-.707M6.343 17.657l-.707.707m12.728 0l-.707-.707M12 7a5 5 0 015 5 5 5 0 01-5 5 5 5 0 01-5-5 5 5 0 015-5z" />
          </svg>
        </button>

        <!-- Suggestions Dropdown -->
        <div v-if="suggestions.length > 0" class="absolute bottom-full left-0 mb-2 w-72 bg-white rounded-lg shadow-2xl border border-gray-200 overflow-hidden z-50 animate-in fade-in slide-in-from-bottom-2">
          <div class="p-2 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
            <span class="text-xs font-bold text-gray-500 uppercase">Recommended Interventions</span>
            <button @click="suggestions = []" class="text-gray-400 hover:text-gray-600">
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="max-h-64 overflow-y-auto">
            <button 
              v-for="s in suggestions" 
              :key="s.type"
              @click="applySuggestion(s.content)"
              class="w-full text-left p-3 hover:bg-[#F3F4F6] transition-colors border-b last:border-0 border-gray-50 group/item"
            >
              <div class="flex items-center gap-2 mb-1">
                <span :class="getTypeColor(s.type)" class="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase transition-colors">
                  {{ s.type }}
                </span>
                <span class="text-[10px] text-gray-400 opacity-0 group-hover/item:opacity-100 transition-opacity">Click to fill</span>
              </div>
              <p class="text-sm text-gray-700 line-clamp-2 leading-snug">{{ s.content }}</p>
            </button>
          </div>
        </div>
      </div>

      <!-- Input Box Container -->
      <div class="relative flex-1 flex items-center">
        <input
          type="text"
          v-model="inputText"
          @keydown.enter="handleKeydownEnter"
          :placeholder="placeholderText"
          :disabled="!isSocketConnected"
          class="w-full px-5 py-3 border border-gray-400 rounded-l-full focus:outline-none focus:ring-2 focus:ring-[#8095CA] transition-all text-gray-900 bg-[#D9D9D9] placeholder-gray-500"
        />
        
        <!-- 发送按钮 -->
        <button
          @click="handleSend"
          :disabled="!isSocketConnected || !inputText.trim()"
          class="px-6 py-3 bg-[#8095CA] hover:bg-[#6D8DBE] text-white font-bold rounded-r-full shadow-lg disabled:bg-gray-600 disabled:opacity-50 transition-all active:scale-95"
        >
          Send
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject } from 'vue'
import axios from 'axios'

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

const sessionId = inject('sessionId')
const pblSocket = inject('pblSocket', {})
const { activeMessageId, activeQuestionInfo } = pblSocket

// 这里的 API_BASE 应该与 ViewA.vue 保持一致，或者是环境配置
const API_BASE = 'http://127.0.0.1:8000'

const inputText = ref('')
const isGenerating = ref(false)
const suggestions = ref([])

const placeholderText = computed(() =>
  props.isSocketConnected ? 'Enter teacher intervention instruction, press Enter to send...' : 'Connecting to discussion server...'
)

const handleKeydownEnter = (event) => {
  if (event.isComposing) return
  handleSend()
}

const handleSend = () => {
  if (inputText.value.trim() && props.isSocketConnected) {
    emit('send-message', inputText.value.trim())
    inputText.value = '' // 清空输入框
    suggestions.value = [] // 清空建议
  }
}

const generateSuggestions = async () => {
  if (isGenerating.value) return
  
  // 打印调试信息，确认数据存在
  console.log('Generating suggestions with data:', {
    session_id: sessionId?.value,
    last_message_id: activeMessageId?.value,
    scene_index: activeQuestionInfo?.value?.sceneIndex,
    question_index: activeQuestionInfo?.value?.questionIndex
  })

  // 尝试解构出原始值
  const sId = sessionId?.value || sessionId;
  const aMsgId = activeMessageId?.value || activeMessageId;

  if (!sId || !aMsgId) {
    alert(`会话或消息上下文不完整。\nsessionId: ${sId}\nactiveMessageId: ${aMsgId}\n请确保讨论已开始或消息已加载。`)
    return
  }

  isGenerating.value = true
  suggestions.value = []
  
  try {
    const payload = {
      session_id: String(sId),
      last_message_id: String(aMsgId),
      scene_index: Number(activeQuestionInfo?.value?.sceneIndex || 0),
      question_index: Number(activeQuestionInfo?.value?.questionIndex || 0)
    }
    
    const response = await axios.post(`${API_BASE}/api/generate-intervention-suggestions`, payload)
    
    if (response.data.status === 'success') {
      suggestions.value = response.data.suggestions
    } else {
      console.error('Failed to generate suggestions:', response.data.message)
      alert('生成建议失败: ' + (response.data.message || '未知错误'))
    }
  } catch (err) {
    console.error('Error calling suggestions API:', err)
    alert('请求失败，请检查后端服务是否正常运行。')
  } finally {
    isGenerating.value = false
  }
}

const applySuggestion = (content) => {
  inputText.value = content
  suggestions.value = []
}

const getTypeColor = (type) => {
  switch (type) {
    case '提问': return 'bg-blue-100 text-blue-600'
    case '解释': return 'bg-purple-100 text-purple-600'
    case '回答': return 'bg-green-100 text-green-600'
    case '点评': return 'bg-amber-100 text-amber-600'
    default: return 'bg-gray-100 text-gray-600'
  }
}
</script>

