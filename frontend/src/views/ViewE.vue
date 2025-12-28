<template>
  <div class="placeholder-view h-full flex flex-col">
    <!-- Header -->
    <header class="border-b border-gray-600 shadow-sm z-10">
      <div class="px-4 py-3 flex justify-between items-center">
        <h1 class="text-lg font-bold text-gray-600">PBL 讨论面板</h1>
        <div class="flex items-center space-x-2">
          <span class="text-sm font-medium text-gray-600">阶段: {{ discussionStage }}</span>
          <div class="flex items-center space-x-1">
            <span class="relative flex h-3 w-3">
              <span
                :class="[isConnected ? 'animate-ping bg-green-400' : 'bg-red-400', 'absolute inline-flex h-full w-full rounded-full opacity-75']"
              ></span>
              <span
                :class="[isConnected ? 'bg-green-500' : 'bg-red-500', 'relative inline-flex rounded-full h-3 w-3']"
              ></span>
            </span>
            <span class="text-xs font-medium text-gray-600">{{ isConnected ? '已连接' : '未连接' }}</span>
          </div>
        </div>
      </div>
    </header>

    <!-- Chat Area -->
    <main ref="chatContainer" class="flex-1 overflow-y-auto p-4">
      <!-- Initial State / Start Button -->
      <div v-if="messages.length === 0" class="text-center py-12">
        <h2 class="text-xl font-semibold text-gray-700">讨论尚未开始</h2>
        <p class="mt-2 text-gray-500">点击下方按钮，以上述病例开始一场新的 PBL 讨论。</p>
        <button
          @click="handleStartDiscussion"
          :disabled="!isConnected"
          class="mt-6 px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg shadow-md hover:bg-indigo-700 focus:outline-none disabled:bg-gray-400"
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
        />
      </div>
    </main>

    <!-- Teacher Input -->
    <TeacherInput
      :is-socket-connected="isConnected"
      @send-message="handleTeacherIntervention"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { usePBLSocket } from '../composables/usePBLSocket.js'
import ChatCard from '../components/ChatCard.vue'
import TeacherInput from '../components/TeacherInput.vue'

const chatContainer = ref(null)
const sessionId = `pbl-session-${Date.now()}`

const scrollToBottom = () => {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

const {
  messages,
  isConnected,
  discussionStage,
  startDiscussion,
  sendTeacherIntervention,
} = usePBLSocket(sessionId, scrollToBottom)

const initialCaseText =
  '患者：男，45岁，因“突发胸痛2小时”入院。既往有高血压病史5年，吸烟史20年。查体：血压150/90mmHg，心率110次/分，双肺呼吸音清。心电图提示V1-V5导联ST段抬高。请各位同学开始讨论。'

const handleStartDiscussion = () => {
  startDiscussion(initialCaseText)
}

const handleTeacherIntervention = (messageText) => {
  sendTeacherIntervention(messageText)
}
</script>

<style scoped>
.placeholder-view{
  background: #1a1f3a; 
  color: white;
}
</style>
