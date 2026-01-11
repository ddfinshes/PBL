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
        <div 
          v-for="message in filteredMessages" 
          :key="message.id" 
          class="relative mb-4 transition-all duration-300"
          :class="{ 'scale-[1.01] z-10': message.isCurrentTopic }"
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
const personas = ref({})
const sessionId = inject('sessionId')
const { 
  messages, 
  isConnected, 
  isPaused, 
  startDiscussion, 
  togglePause, 
  sendTeacherIntervention,
  selectedTopic,
  activeMessageId
} = inject('pblSocket')

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

  // 1. 确定我们要观察哪条“路径”的终点
  let leafId = activeMessageId.value;
  if (selectedTopic.value) {
     const topicMsgs = messages.value.filter(m => {
        let tName = m.topic || (m.agent === 'teacher' ? '教师干预' : '待识别');
        return `${m.branch_id || 'main'}_${tName}` === selectedTopic.value;
     });
     if (topicMsgs.length > 0) leafId = topicMsgs[topicMsgs.length - 1].id;
  }

  const viewingChain = getChainForId(leafId);

  // 2. 映射消息并标记高亮
  return messages.value
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

const discussionStage = ref('阶段一：初步讨论')

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
