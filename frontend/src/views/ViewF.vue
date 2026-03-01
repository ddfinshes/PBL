<template>
  <div class="placeholder-view h-full flex flex-col">
    <!-- Header -->
    <header class="view-f-header">
      <div class="flex justify-between items-center">
        <h1 class="view-title">Discussion Simulation</h1>
        <div class="flex items-center space-x-2">
          <span class="text-sm font-medium text-gray-600">Stage: {{ discussionStage }}</span>
          
          <div class="flex items-center space-x-1">
            <span class="relative flex h-3 w-3">
              <span
                :class="[isConnected ? 'animate-ping bg-[#7fbf4c]' : 'bg-[#fc8d59]', 'absolute inline-flex h-full w-full rounded-full opacity-75']"
              ></span>
              <span
                :class="[isConnected ? 'bg-[#7fbf4c]' : 'bg-[#fc8d59]', 'relative inline-flex rounded-full h-3 w-3']"
              ></span>
            </span>
            <span class="text-xs font-medium text-gray-600">{{ isConnected ? 'Connected' : 'Disconnected' }}</span>
          </div>
        </div>
      </div>
    </header>

    <!-- Chat Area -->
    <main ref="chatContainer" class="flex-1 overflow-y-auto p-4" style="background: #ECECEC;">
      <!-- Initial State / Start Button -->
      <div v-if="filteredMessages.length === 0" class="text-center py-12">
        <h2 class="text-xl font-semibold text-gray-800">Discussion Not Started Yet</h2>
        <p class="mt-2 text-gray-600">Click the button below to start a new PBL discussion based on the case file above.</p>
        <button
          @click="handleStartDiscussion"
          :disabled="!isConnected"
          class="mt-6 px-6 py-3 bg-[#8095CA] text-white font-semibold rounded-lg shadow-md hover:bg-[#6D8DBE] focus:outline-none disabled:bg-gray-400"
        >
          Start Discussion
        </button>
      </div>

      <!-- Message Stream -->
      <div v-else>
        <div 
          v-for="message in filteredMessages" 
          :key="message.id" 
          class="relative mb-4 transition-all duration-300 cursor-pointer"
          :class="{ 'scale-[1.01] z-10': message.isCurrentTopic }"
          @click.stop="handleMessageClick(message)"
        >
          <!-- 呼吸边框特效 -->
          <div 
            v-if="message.isCurrentTopic" 
            class="absolute -inset-1 border-2 border-[#60A5FA] rounded-xl pointer-events-none animate-chat-pulse z-[5]"
          ></div>
          
          <ChatCard
            :message="message"
            :agent-config="getAgentConfig(message.agent)"
            class="relative z-10"
          />
        </div>
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
import { ref, onMounted, inject, watch, nextTick, computed } from 'vue'
import axios from 'axios'
import ChatCard from '../components/ChatCard.vue'
import TeacherInput from '../components/TeacherInput.vue'

const props = defineProps({
  activeContext: {
    type: Object,
    default: null
  }
})

const chatContainer = ref(null)
const sessionId = inject('sessionId')
const pblSocket = inject('pblSocket', {})

const { 
  messages, 
  isConnected, 
  isPaused, 
  startDiscussion, 
  togglePause, 
  sendTeacherIntervention,
  rollbackTo,
  selectedTopic,
  selectedNodeLeafId,
  activeMessageId,
  activeQuestionInfo,
  personas,
  fetchPersonas,
  getAgentConfig,
  discussionStage
} = pblSocket
console.log('-------',discussionStage
)
// 获取特定消息 ID 向上溯源的所有父节点 ID（即该分支的完整路径）
const getChainForId = (leafId) => {
  const chain = new Set();
  if (!messages.value?.length) return chain;

  let curr = leafId;
  let safety = 0;
  while (curr && safety < 1000) {
    chain.add(curr);
    const m = messages.value.find(msg => msg.id === curr);
    const next = m ? m.parent_id : null;
    if (next === curr) break;
    curr = next;
    safety++;
  }
  // 补充初始消息 (通常是病例介绍)
  messages.value.forEach(m => { 
    if (!m.parent_id) chain.add(m.id); 
  });
  return chain;
};

// 支持根据选中主题进行过滤，同时严格限制在活跃分支或选中的分支路径上
const filteredMessages = computed(() => {
  if (!messages.value?.length) return [];

  // Filter messages by active question
  const questionMessages = messages.value.filter(m => 
    m.sceneIndex === activeQuestionInfo.value.sceneIndex && 
    m.questionIndex === activeQuestionInfo.value.questionIndex
  );

  if (questionMessages.length === 0) return [];

  // 1. 确定我们要观察哪条“路径”的终点
  // 优先使用选中的节点作为终点，否则使用当前最新活跃消息
  let localActiveId = selectedNodeLeafId.value || activeMessageId.value;
  
  // 兜底校验：如果选中的 ID 不在当前问题的范围内，则取该问题范围内的最后一条
  if (!questionMessages.find(m => m.id === localActiveId)) {
    localActiveId = questionMessages[questionMessages.length - 1].id;
  }

  const viewingChain = getChainForId(localActiveId);

  // 2. 映射消息并标记高亮
  return questionMessages
    .filter(m => m && viewingChain.has(m.id))
    .map(m => {
       const agentName = m.agent;
       // 教师和案例介绍不参与主题高亮判定
       if (agentName === 'teacher' || agentName === 'case_introduction' || agentName === 'teacher_handler') {
         return { ...m, isCurrentTopic: false };
       }
       
       let tName = m.topic || '待识别';
       const nodeKey = `${m.branch_id || 'main'}_${tName}`;
       return {
         ...m,
         isCurrentTopic: !!(selectedTopic.value && nodeKey === selectedTopic.value)
       };
    });
});

// 当切换选中的主题时，重置滚动位置到顶部
watch(selectedTopic, () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = 0;
    }
  });
});

// 自动滚动逻辑（新消息到达时）
watch(() => filteredMessages.value.length, () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
    }
  });
});

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
  if (fetchPersonas) await fetchPersonas()
  
  // 优先使用当前选中的案例情节，如果没有则用默认文字
  let textToSend = initialCaseText
  let sIdx = 0
  let qIdx = 0

  if (props.activeContext) {
    textToSend = `${props.activeContext.story}\n Trigger Question: ${props.activeContext.question}\nPlease start your discussion.`
    sIdx = activeQuestionInfo.value.sceneIndex
    qIdx = activeQuestionInfo.value.questionIndex
  }
  
  startDiscussion(textToSend, sIdx, qIdx)
}

const handleTeacherIntervention = (messageText) => {
  console.log('handleTeacherIntervention called with:', messageText)
  sendTeacherIntervention(messageText)
}

const handleMessageClick = (message) => {
  rollbackTo(message.id)
}

// =====================
// Lifecycle
// =====================
onMounted(() => {
  if (fetchPersonas) fetchPersonas()
})
</script>

<style scoped>
.placeholder-view {
  background: #ECECEC; 
  color: #333333;
  border-radius: 12px;
  overflow: hidden;
}
.view-f-header {
  background: #000000;
  padding: 8px 12px;
  flex-shrink: 0;
}
.view-title {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
  text-align: left;
}

@keyframes chat-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(96, 165, 250, 0.7);
    border-color: rgba(96, 165, 250, 1);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(96, 165, 250, 0);
    border-color: rgba(96, 165, 250, 0.5);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(96, 165, 250, 0);
    border-color: rgba(96, 165, 250, 1);
  }
}

.animate-chat-pulse {
  animation: chat-pulse 2s infinite;
}
</style>