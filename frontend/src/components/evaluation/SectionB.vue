<template>
  <div class="content">
    <!-- Scrollable Area for Agent Cards -->
    <div class="agents-scroll-area flex-1 overflow-y-auto" ref="scrollContainer">
      <div class="agents-container" :style="{ height: stackHeight + 'px' }">
        <!-- Stacked Agent Cards -->
        <transition-group name="stack" tag="div" class="cards-stack">
          <div 
            v-for="(agent, index) in agents" 
            :key="agent.id || index"
            class="agent-card-wrapper"
            :style="getCardStyle(index)"
            @click="handleCardClick(index)"
          >
            <div class="agent-card-container">
              <AgentCard 
                :model-value="agent"
                @update:model-value="agents[index] = $event"
                :interaction-roles="interactionRoles"
                :card-color="agent.cardColor"
                @delete="deleteAgent(index)"
              />
            </div>
          </div>
        </transition-group>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, defineProps, defineEmits, defineExpose, watch } from 'vue';
import AgentCard from './AgentCard.vue';

const props = defineProps({
  username: {
    type: String,
    required: true
  },
  currentCaseId: {
    type: Number,
    default: 1
  },
  selectedEvaluator: {
    type: Object,
    default: null
  },
  currentAgentName: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['back-to-analysis', 'agent-selected']);

const cardColors = ['#CEDCFB', '#FBCEDC', '#D2FBCE', '#FBE4CE', '#E5CEFB', '#CEFBE2'];

const agents = ref([]);
const activeIndex = ref(0);
const loading = ref(false);
const scrollContainer = ref(null);

// 监听 currentAgentName 同步 activeIndex
watch(() => props.currentAgentName, (newName) => {
  if (newName) {
    const idx = agents.value.findIndex(a => a.name === newName || a.id === `agent-${newName}`);
    if (idx !== -1 && idx !== activeIndex.value) {
      console.log('SectionB: 根据全局选择更新 activeIndex:', idx);
      activeIndex.value = idx;
    }
  }
});

// 处理卡片点击，同步回全局
const handleCardClick = (index) => {
  activeIndex.value = index;
  const agent = agents.value[index];
  if (agent) {
    // 假设 agent.id 格式为 agent-name，或者直接用 name
    const agentName = agent.name;
    console.log('SectionB: 卡片点击，同步 Agent 选择:', agentName);
    emit('agent-selected', agentName);
  }
};

const interactionRoles = [
  { name: 'Leader', value: 'leader', icon: 'leader.png' },
  { name: 'Follower', value: 'follower', icon: 'follower.png' },
  { name: 'Advocate', value: 'critical', icon: 'devil.png' }
];

const CARD_OFFSET = 60; // 卡片垂直偏移量（增大到60以避免点击错误）
const CARD_SCALE = 0.95; // 背景卡片缩放比例
const CARD_HEIGHT = 850; // 单张卡片高度

const stackHeight = computed(() => {
  if (agents.value.length === 0) return 0;
  // 第一张卡片高度 + 其他卡片的偏移
  return CARD_HEIGHT + (agents.value.length - 1) * CARD_OFFSET + 40;
});

const getCardStyle = (index) => {
  const isActive = index === activeIndex.value;
  const offset = index * CARD_OFFSET;
  const zIndex = index;
  
  if (isActive) {
    return {
      transform: `translateY(${offset}px) scale(1)`,
      zIndex: zIndex + 100,
      opacity: 1
    };
  } else if (index > activeIndex.value) {
    // 活跃卡片后面的卡片
    return {
      transform: `translateY(${offset}px) scale(${CARD_SCALE})`,
      zIndex: zIndex,
      opacity: 1
    };
  } else {
    // 活跃卡片前面的卡片（隐藏）
    return {
      transform: `translateY(${offset}px) scale(${CARD_SCALE})`,
      zIndex: zIndex,
      opacity: 0.5
    };
  }
};

const deleteAgent = (index) => {
  agents.value.splice(index, 1);
  if (activeIndex.value >= agents.value.length && agents.value.length > 0) {
    activeIndex.value = agents.value.length - 1;
  }
};

const fetchCaseInfo = async () => {
  if (loading.value) return;
  
  try {
    loading.value = true;
    console.log(`SectionB: 开始加载 case${props.currentCaseId} 的 agents...`);
    
    // 从 API 获取 case 中的 agent 配置
    const response = await fetch(`/api/evaluation/case-agents?case_id=${props.currentCaseId}`);
    
    if (!response.ok) {
      console.error(`SectionB: 加载失败，HTTP ${response.status}: ${response.statusText}`);
      return;
    }

    const data = await response.json();
    
    if (data.status !== 'success' || !data.agents) {
      console.error('SectionB: 从 API 获取 agents 失败:', data);
      return;
    }

    console.log(`SectionB: 从 API 获取到 ${Object.keys(data.agents).length} 个 agents`);

    // 从 API 响应加载 agent 配置
    agents.value = [];
    let colorIndex = 0;

    // 遍历 case 中的每个 agent（学生）
    Object.entries(data.agents).forEach(([agentKey, agentData]) => {
      if (typeof agentData === 'object' && agentData.name) {
        const agent = {
          id: `agent-${agentKey}`,
          name: agentData.name || '',
          age: agentData.age || '',
          major: agentData.major || '',
          avatar: agentData.avatar || 'avatar1.png',
          cardColor: agentData.cardColor || cardColors[colorIndex % cardColors.length],
          learning_styles: agentData.learning_styles || {
            surface: 3,
            deep: 3,
            strategic: 3
          },
          personality: agentData.personality || {
            openness: 3,
            conscientiousness: 3,
            extraversion: 3,
            agreeableness: 3,
            neuroticism: 3
          },
          knowledge_background: agentData.knowledge_background || {
            high: [],
            medium: [],
            low: []
          },
          cognitiveOrientation: agentData.cognitive_orientation || '未定义',
          learning_adaptivity: agentData.learning_adaptivity || '',
          tags: agentData.tags || [],
          learning_style_prompt: agentData.learning_style_prompt || '',
          personality_prompt: agentData.personality_prompt || '',
          unclassifiedKnowledge: [],
          classifiedKnowledge: {
            competent: [],
            novice: [],
            layman: []
          },
          social: {
            confidence: 'medium',
            register: 'medium',
            participation: 'medium',
            role: 'leader'
          },
          plasticity: agentData.learning_adaptivity || 'medium',
          configChat: {
            messages: [],
            unresolvedFields: []
          }
        };

        // 初始化知识分类
        if (agentData.knowledge_background) {
          // 直接赋值，不用检查是否为空
          agent.classifiedKnowledge.competent = agentData.knowledge_background.high || [];
          agent.classifiedKnowledge.novice = agentData.knowledge_background.medium || [];
          agent.classifiedKnowledge.layman = agentData.knowledge_background.low || [];
          
          console.log(`SectionB: ${agent.name} - 知识分类: competent=${agent.classifiedKnowledge.competent.length}, novice=${agent.classifiedKnowledge.novice.length}, layman=${agent.classifiedKnowledge.layman.length}`);
        }

        agents.value.push(agent);
        colorIndex++;
      }
    });

    activeIndex.value = 0;
    console.log(`SectionB: 成功加载 ${agents.value.length} 个 agents`);
    console.log(`SectionB: 堆叠卡片间距已设置为 ${CARD_OFFSET}px`);
    
    // 输出所有agents的知识分类信息用于调试
    agents.value.forEach((agent, idx) => {
      console.log(`Agent ${idx + 1} (${agent.name}):`, {
        competent: agent.classifiedKnowledge.competent,
        novice: agent.classifiedKnowledge.novice,
        layman: agent.classifiedKnowledge.layman
      });
    });
    
    // 重置滚动位置
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = 0;
    }
  } catch (error) {
    console.error('SectionB: 加载 case agents 失败:', error);
  } finally {
    loading.value = false;
  }
};

// 监听 currentCaseId 变化，自动重新加载（immediate: true 确保初始化时也会执行）
watch(() => props.currentCaseId, () => {
  console.log(`SectionB: currentCaseId 变化为 ${props.currentCaseId}，重新加载...`);
  fetchCaseInfo();
}, { immediate: true });

defineExpose({
  fetchCaseInfo
});
</script>

<style scoped>
.content {
  padding: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.agents-scroll-area {
  flex: 1;
  overflow-y: auto;
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  padding: 20px;
}

.agents-container {
  position: relative;
  width: 100%;
}

.cards-stack {
  position: relative;
  width: 100%;
  height: 100%;
}

.agent-card-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  width: 100%;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.agent-card-container {
  width: 100%;
  background-color: white;
  border-radius: 20px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.stack-enter-active,
.stack-leave-active {
  transition: all 0.3s ease;
}

.stack-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

.stack-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
}
</style>