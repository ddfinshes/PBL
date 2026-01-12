<template>
  <div class="view-e-container h-full flex flex-col bg-[#0C0E27] rounded-xl border border-[#8095CA]/20 overflow-hidden relative p-6">
    <!-- Header -->
    <div class="mb-6 z-10">
      <h3 class="text-[#8095CA] font-bold tracking-wider">讨论故事线 (Storyline)</h3>
    </div>

    <!-- Timeline Content -->
    <div ref="container" class="flex-1 overflow-y-auto timeline-scroll pr-4 relative" @click="selectedTopic = null">
      <div class="relative min-h-full">
        <!-- 竖线：强化颜色、宽度，并确保贯穿整个滚动区域 -->
        <div 
          class="absolute left-[24px] top-4 w-[4px] bg-[#8095CA] z-0 rounded-full shadow-[0_0_10px_rgba(128,149,202,0.3)]"
          :style="{ bottom: filteredMessages.length > 0 ? '40px' : '0' }"
        ></div>
        
        <!-- 末端箭头：在最后一条消息下方显示 -->
        <div 
          v-if="filteredMessages.length > 0"
          class="absolute left-[18px] w-0 h-0 border-l-[8px] border-l-transparent border-r-[8px] border-r-transparent border-t-[12px] border-t-[#8095CA] z-0"
          :style="{ top: 'calc(100% - 30px)' }"
        ></div>

        <div class="space-y-8 relative z-10 py-6">
          <div 
            v-for="(msg, index) in filteredMessages" 
            :key="msg.id"
            class="flex items-start group cursor-pointer transition-all duration-300 relative rounded-2xl"
            :class="{ 
              'scale-[1.03] z-20': msg.isCurrentTopic,
              'pulse-highlight': msg.isCurrentTopic
            }"
            @click.stop="handleMessageClick(msg)"
          >
          <!-- 选中消息的高亮边框特效 -->
          <div 
            v-if="msg.isCurrentTopic" 
            class="absolute -inset-1 border-2 border-[#60A5FA] rounded-2xl pointer-events-none z-10 animate-border-pulse"
          ></div>

          <!-- Left: Agent Info -->
          <div class="flex-shrink-0 flex flex-col items-center w-[50px] mr-6">
            <div 
              class="w-10 h-10 rounded-full border-2 border-white/80 shadow-lg bg-white overflow-hidden mb-1 transition-transform group-hover:scale-110"
              :style="{ borderColor: getAgentColor(msg.agent) }"
            >
              <img :src="getAgentAvatar(msg.agent)" class="w-full h-full object-cover">
            </div>
            <span class="text-[10px] text-gray-400 font-bold truncate w-full text-center">
              {{ getAgentName(msg.agent) }}
            </span>
          </div>

          <!-- Right: Summary Bubble -->
          <div class="flex-1 pt-1">
            <div 
              class="relative px-4 py-3 rounded-2xl rounded-tl-none border border-white/20 shadow-xl backdrop-blur-md transition-all group-hover:brightness-110"
              :style="{ 
                backgroundColor: getAgentColor(msg.agent),
                opacity: 0.85
              }"
            >
              <p class="text-[#0C0E27] text-sm leading-relaxed font-bold italic">
                “{{ msg.summary || msg.text }}”
              </p>
              
              <!-- 装饰性箭头 (指向时间轴线) -->
              <div 
                class="absolute left-[-8px] top-0 w-2 h-2"
                style="clip-path: polygon(100% 0, 0 0, 100% 100%);"
                :style="{ backgroundColor: getAgentColor(msg.agent) }"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 如果没有消息时的占位 -->
    <div v-if="filteredMessages.length === 0" class="h-full flex flex-center items-center justify-center">
      <p class="text-gray-500 text-sm italic">讨论尚未开始，等待生成故事线...</p>
    </div>
  </div>

  <!-- 底部渐变遮罩 -->
  <div class="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-[#0C0E27] to-transparent pointer-events-none"></div>
</div>
</template>

<script setup>
import { ref, onMounted, inject, computed, watch, nextTick } from 'vue';
import axios from 'axios';

const { 
  messages, 
  selectedTopic, 
  selectedNodeLeafId,
  activeMessageId, 
  activeQuestionInfo,
  rollbackTo 
} = inject('pblSocket');
const container = ref(null);
const personas = ref({});

// 计算当前活跃路径上的消息 ID 集合
const activePathIds = computed(() => {
  const path = new Set();
  if (!messages?.value?.length) return path;

  // Filter messages by active question
  const questionMessages = messages.value.filter(m => 
    m.sceneIndex === activeQuestionInfo.value.sceneIndex && 
    m.questionIndex === activeQuestionInfo.value.questionIndex
  );

  let curr = selectedNodeLeafId.value || activeMessageId?.value;
  // 如果当前活跃消息不在范围内，取范围内最后一个
  if (!questionMessages.find(m => m.id === curr) && questionMessages.length > 0) {
    curr = questionMessages[questionMessages.length - 1].id;
  }

  let safety = 0;
  while (curr && safety < 1000) {
    path.add(curr);
    const m = questionMessages.find(msg => msg.id === curr);
    const next = m ? m.parent_id : null;
    if (!next || next === curr) break;
    curr = next;
    safety++;
  }
  return path;
});

// 加载 Agent 配置
const fetchPersonas = async () => {
  try {
    const resp = await axios.get('http://127.0.0.1:8000/get_personas');
    personas.value = resp.data;
  } catch (err) {
    console.error('ViewE: Failed to fetch personas:', err);
  }
};

// 过滤和处理消息
const filteredMessages = computed(() => {
  if (!messages.value?.length) return [];

  // Filter messages by active question
  let baseMessages = messages.value.filter(m => 
    m && m.agent !== 'case_introduction' && 
    m.agent !== 'teacher_handler' &&
    m.sceneIndex === activeQuestionInfo.value.sceneIndex && 
    m.questionIndex === activeQuestionInfo.value.questionIndex
  );
  
  if (baseMessages.length === 0) return [];

  // 获取该问题下的所有消息，用于查找
  const questionMessages = messages.value.filter(m => 
    m.sceneIndex === activeQuestionInfo.value.sceneIndex && 
    m.questionIndex === activeQuestionInfo.value.questionIndex
  );

  // 1. 确定我们要展示哪条路径
  let leafId = selectedNodeLeafId.value || activeMessageId?.value;
  if (!questionMessages.find(m => m.id === leafId)) {
    leafId = questionMessages[questionMessages.length - 1].id;
  }

  if (selectedTopic?.value) {
     // 找到选中主题涉及的最佳叶子节点（该主题下的最后一条发言）
     const topicMsgs = questionMessages.filter(m => {
        let tName = m.topic || (m.agent === 'teacher' ? '教师干预' : '待识别');
        return `${m.branch_id || 'main'}_${tName}` === selectedTopic.value;
     });
     if (topicMsgs.length > 0) leafId = topicMsgs[topicMsgs.length - 1].id;
  }

  // 计算该路径上的所有消息 ID (包含祖先链，确保上下文完整)
  const pathIds = new Set();
  let curr = leafId;
  let safety = 0;
  while (curr && safety < 1000) {
    pathIds.add(curr);
    const m = questionMessages.find(msg => msg.id === curr);
    const next = m ? m.parent_id : null;
    if (!next || next === curr) break;
    curr = next;
    safety++;
  }

  // 确保所有在路径上的消息被按时间顺序排列
  return baseMessages
    .filter(m => pathIds.has(m.id))
    .map(m => {
       const agentName = m.agent;
       let tName = m.topic || (agentName === 'teacher' ? '教师干预' : '待识别');
       const nodeKey = `${m.branch_id || 'main'}_${tName}`;
       return {
         ...m,
         isCurrentTopic: !!(selectedTopic.value && nodeKey === selectedTopic.value)
       };
    })
    .sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
});

const handleMessageClick = (msg) => {
  // 点击消息触发回退过程
  if (confirm(`确定要回退到 ${getAgentName(msg.agent)} 的这条消息并重新开始讨论吗？`)) {
    rollbackTo(msg.id);
  }
};

const getAgentAvatar = (agentKey) => {
  if (personas.value[agentKey]?.avatar) {
    const avatar = personas.value[agentKey].avatar;
    return avatar.startsWith('http') || avatar.startsWith('/') ? avatar : `/avatar/${avatar}`;
  }
  return '/avatar/default.png';
};

const getAgentName = (agentKey) => {
  return personas.value[agentKey]?.name || agentKey;
};

const getAgentColor = (agentKey) => {
  return personas.value[agentKey]?.cardColor || '#8095CA';
};

// 自动滚动到底部
watch(() => filteredMessages.value.length, () => {
  nextTick(() => {
    if (container.value) {
      container.value.scrollTo({
        top: container.value.scrollHeight,
        behavior: 'smooth'
      });
    }
  });
});

onMounted(() => {
  fetchPersonas();
});
</script>

<style scoped>
.timeline-scroll::-webkit-scrollbar {
  width: 4px;
}
.timeline-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.timeline-scroll::-webkit-scrollbar-thumb {
  background: rgba(128, 149, 202, 0.2);
  border-radius: 10px;
}
.timeline-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(128, 149, 202, 0.4);
}

.animate-border-pulse {
  animation: border-pulse 2s infinite;
}

@keyframes border-pulse {
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
</style>
