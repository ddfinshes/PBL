<template>
  <div class="placeholder-view h-full flex flex-col">
    <!-- Header -->
    <header class="border-b border-gray-600 shadow-sm z-10">
      <div class="px-4 py-3 flex justify-between items-center">
        <h1 class="text-lg font-bold text-gray-200">PBL 模拟讨论</h1>
        <div class="flex items-center space-x-2">
          <span class="text-sm font-medium text-gray-300">阶段: {{ discussionStage }}</span>
          
          <div class="flex items-center space-x-1">
            <span class="relative flex h-3 w-3">
              <span
                :class="[isConnected ? 'animate-ping bg-[#7fbf4c]' : 'bg-[#fc8d59]', 'absolute inline-flex h-full w-full rounded-full opacity-75']"
              ></span>
              <span
                :class="[isConnected ? 'bg-[#7fbf4c]' : 'bg-[#fc8d59]', 'relative inline-flex rounded-full h-3 w-3']"
              ></span>
            </span>
            <span class="text-xs font-medium text-gray-300">{{ isConnected ? '已连接' : '未连接' }}</span>
          </div>
        </div>
      </div>
    </header>

    <!-- Chat Area -->
    <main ref="chatContainer" class="flex-1 overflow-y-auto p-4">
      <!-- Initial State / Start Button -->
      <div v-if="messages.length === 0" class="text-center py-12">
        <h2 class="text-xl font-semibold text-gray-200">讨论尚未开始</h2>
        <p class="mt-2 text-gray-400">点击下方按钮，以上述病例开始一场新的 PBL 讨论。</p>
        <button
          @click="handleStartDiscussion"
          :disabled="!isConnected"
          class="mt-6 px-6 py-3 bg-[#8095CA] text-white font-semibold rounded-lg shadow-md hover:bg-[#6D8DBE] focus:outline-none disabled:bg-gray-400"
        >
          开始讨论
        </button>
      </div>

      <!-- Message Stream -->
      <div v-else>
        <ChatCard
          v-for="message in messages"
          :key="message.id"
          :message="message"
          :agent-config="getAgentConfig(message.agent)"
        />
      </div>
    </main>

    <!-- Teacher Input -->
    <TeacherInput
      :is-socket-connected="isConnected"
      :is-paused="isPaused"
      :has-messages="messages.length > 0"
      @send-message="handleTeacherIntervention"
      @toggle-pause="togglePause"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'
import axios from 'axios'
import { usePBLSocket } from '../composables/usePBLSocket.js'
import ChatCard from '../components/ChatCard.vue'
import TeacherInput from '../components/TeacherInput.vue'

const props = defineProps({
  activeContext: {
    type: Object,
    default: null
  }
})

// =====================
// Refs and Session
// =====================
const chatContainer = ref(null)
const personas = ref({})
const sessionId = inject('sessionId', `pbl-session-${Date.now()}`)

// =====================
// Fetch Personas (Incoming Feature)
// =====================
const fetchPersonas = async () => {
  try {
    const resp = await axios.get('http://127.0.0.1:8000/get_personas')
    personas.value = resp.data
    console.log('Personas loaded for simulation:', Object.keys(personas.value))
  } catch (err) {
    console.error('Failed to fetch personas:', err)
  }
}

// =====================
// Agent Config Mapping
// =====================
const getAgentConfig = (agentKey) => {
  if (!agentKey || !personas.value) return {}

  // 1. 直接通过 key 匹配
  if (personas.value[agentKey]) return personas.value[agentKey]

  // 2. 尝试按 name 属性搜索
  const found = Object.values(personas.value).find(p => p.name === agentKey)
  if (found) return found

  return {}
}

// =====================
// Socket & Discussion
// =====================
const scrollToBottom = () => {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

const {
  messages,
  isConnected,
  isPaused,
  discussionStage,
  startDiscussion,
  togglePause,
  sendTeacherIntervention,
} = usePBLSocket(sessionId, scrollToBottom)

// =====================
// Initial Case Text
// =====================
const initialCaseText =
  '患者：男，45岁，因“突发胸痛2小时”入院。既往有高血压病史5年，吸烟史20年。查体：血压150/90mmHg，心率110次/分，双肺呼吸音清。心电图提示V1-V5导联ST段抬高。请各位同学开始讨论。'

// =====================
// Event Handlers
// =====================
const handleStartDiscussion = async () => {
  // 讨论开始前获取最新 agent 配置
  await fetchPersonas()
  
  // 优先使用当前选中的案例情节，如果没有则用默认文字
  let textToSend = initialCaseText
  if (props.activeContext) {
    textToSend = `${props.activeContext.story}\n\n引导问题：${props.activeContext.question}\n请各位同学开始讨论。`
  }
  
  startDiscussion(textToSend)
}

const handleTeacherIntervention = (messageText) => {
  console.log('handleTeacherIntervention called with:', messageText)
  sendTeacherIntervention(messageText)
}

// =====================
// Lifecycle
// =====================
onMounted(() => {
  fetchPersonas()
})
</script>

<style scoped>
.placeholder-view {
  background: #1a1f3a; 
  color: white;
  border-radius: 12px;
}
</style>
