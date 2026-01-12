<template>
  <div class="placeholder-view h-full flex flex-col">
    <!-- Header -->
    <header class="border-b border-gray-600 shadow-sm z-10">
      <div class="px-4 py-3 flex justify-between items-center">
        <h1 class="text-lg font-bold text-gray-200">PBL 模拟讨论</h1>
        <div class="flex items-center space-x-2">
          <span class="text-sm font-medium text-gray-300">阶段: {{ discussionStage }}</span>
<<<<<<< HEAD
          
=======
>>>>>>> eb8570c (美化了所有写过的视图，调整了自适应分辨率)
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
import { ref, onMounted, inject, computed } from 'vue'
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

const chatContainer = ref(null)
const personas = ref({})
const sessionId = inject('sessionId', `pbl-session-${Date.now()}`)

const fetchPersonas = async () => {
  try {
    // 使用 axios 更加统一，且增加日志
    const resp = await axios.get('http://127.0.0.1:8000/get_personas')
    personas.value = resp.data
    console.log('Personas loaded for simulation:', Object.keys(personas.value))
  } catch (err) {
    console.error('Failed to fetch personas:', err)
  }
}

/**
 * 根据消息中的 agent 标识寻找对应的配置。
 * 兼容处理：尝试匹配 key 或匹配 name 属性。
 */
const getAgentConfig = (agentKey) => {
  if (!agentKey || !personas.value) return {}
  
  // 1. 直接通过 Key 匹配 (如 Student_0)
  if (personas.value[agentKey]) return personas.value[agentKey]
  
  // 2. 如果 Key 没匹配上，尝试按 name 属性搜索 (如 "徐源松")
  const found = Object.values(personas.value).find(p => p.name === agentKey)
  if (found) return found
  
  return {}
}

onMounted(() => {
  fetchPersonas()
})

const scrollToBottom = () => {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

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
  let sIdx = 0
  let qIdx = 0

const handleStartDiscussion = async () => {
  // 讨论开始前重新获取一次最新的 Agent 配置，确保颜色和头像同步
  await fetchPersonas()
  startDiscussion(initialCaseText)
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
