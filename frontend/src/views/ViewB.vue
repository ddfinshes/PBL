<template>
  <div class="view-b-container p-0 h-full flex flex-col" @mousedown="handleGlobalMouseDown">
    <div class="header"><h2>Agent Configuration</h2></div>
    <!-- Scrollable Area for Cards -->
    <div class="view-b-scroll-area flex-1 overflow-y-auto p-2 custom-scrollbar">
      <div class="view-b-content-wrapper w-full relative">
        <!-- 占位元素，用于撑开容器高度，使绝对定位的卡片堆叠有滚动空间 -->
        <div :style="{ height: stackHeight + 'px' }" class="stack-spacer transition-all duration-500"></div>

        <!-- Stacking Agent Cards -->
        <transition-group name="stack">
          <div 
            v-for="(agent, index) in agents" 
            :key="agent.id"
            class="agent-card-wrapper"
            :style="getCardStyle(index)"
            @click="activeIndex = index"
          >
            <AgentCard 
              ref="cardRefs"
              v-model="agents[index]"
              :cognitive-options="cognitiveOptions"
              :interaction-roles="interactionRoles"
              :card-color="agents[index].cardColor"
              @delete="deleteAgent(index)"
            />
          </div>
        </transition-group>
      </div>
    </div>

    <!-- Fixed Actions Area at the Bottom -->
    <div class="actions-wrapper">
      <!-- Add Agent Action Area -->
      <div class="add-agent-section-mini" @click="addAgent">
        <div class="plus-icon">+</div>
        <div class="add-text">Add Agent</div>
      </div>

      <!-- Global Save Action -->
      <div class="global-actions">
        <el-button type="primary" size="small" @click="syncPersona" class="save-button">
          Save
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, inject, provide } from 'vue';
import axios from 'axios';
import { ElMessage } from 'element-plus';
import AgentCard from '../components/AgentCard.vue';

const { fetchPersonas, updateKnowledge, addKnowledge, deleteKnowledge } = inject('pblSocket', {});

const props = defineProps({
  theoreticalKnowledge: {
    type: Array,
    default: () => []
  },
  caseTitle: {
    type: String,
    default: ''
  }
});

// Refs for individual cards to handle global events like "cancelling edit"
const cardRefs = ref([]);
const activeIndex = ref(0);

const cognitiveOptions = {
  0: ['symptoms', 'present_illness', 'past_medical_history', 'physicochemical_parameters'],
  1: ['familiarity_driven', 'symptom_significance', 'risk_perception', 'irrelevant_factors'],
  2: ['linear_causality', 'multi_concurrent', 'undefined']
};

const interactionRoles = [
  { name: 'Leader', value: 'leader', icon: 'leader.png' },
  { name: 'Follower', value: 'follower', icon: 'follower.png' },
  { name: 'Advocate', value: 'critical', icon: 'devil.png' }
];

const cardColors = ['#CEDCFB', '#FBCEDC', '#D2FBCE', '#FBE4CE', '#E5CEFB', '#CEFBE2'];

const createDefaultAgent = (index = 0) => ({
  id: 'agent-' + Date.now() + Math.random(),
  name: '',
  age: '',
  major: '',
  avatar: 'avatar1.png',
  cardColor: cardColors[index % cardColors.length],
  // Unclassified knowledge: prioritize using extracted PDF content
  unclassifiedKnowledge: props.theoreticalKnowledge.length > 0 
    ? [...props.theoreticalKnowledge] 
    : [], 
  // Classified knowledge corresponding to three levels
  classifiedKnowledge: {
    competent: [], // Good
    novice: [],    // Medium
    layman: []     // Bad
  },
  cognitive: {
    0: [],
    1: [],
    2: []
  },
  social: {
    confidence: 'medium',
    register: 'medium',
    role: 'leader'
  },
  plasticity: 'medium'
});

const agents = ref([createDefaultAgent(0)]);

const STACK_HEADER_HEIGHT = 85; 
const EXPANDED_CARD_HEIGHT = 870; 
const VISIBLE_GAP_UP = 30;    // 上方堆叠露出的高度
const VISIBLE_GAP_DOWN = 15;  // 下方堆叠露出的高度（更紧凑）

const stackHeight = computed(() => {
  const count = agents.value.length;
  if (count === 0) return 200;
  
  if (activeIndex.value === null) {
    return (count - 1) * STACK_HEADER_HEIGHT + EXPANDED_CARD_HEIGHT;
  }
  
  // 展开模式下：上方占位 + 展开高度 + 下方占位
  return (count - 1) * VISIBLE_GAP_UP + EXPANDED_CARD_HEIGHT + 50;
});

const getCardStyle = (index) => {
  const isSelected = activeIndex.value === index;
  let translateY = 0;
  let zIndex = index;
  let scale = 1;
  let opacity = 1;

  if (activeIndex.value === null) {
    // 列表模式：保持等宽间距
    translateY = index * (STACK_HEADER_HEIGHT + 20);
    zIndex = index;
  } else {
    // 聚焦模式
    if (index < activeIndex.value) {
      // 上方卡片：正常向上堆叠
      translateY = index * VISIBLE_GAP_UP;
      scale = 0.92 + (index * 0.01);
      zIndex = index;
      opacity = 0.8;
    } else if (index === activeIndex.value) {
      // 激活卡片：位于视觉中心
      translateY = activeIndex.value * VISIBLE_GAP_UP + 10;
      zIndex = 100;
      scale = 1;
      opacity = 1;
    } else {
      // 下方卡片：紧密堆叠，且由于 zIndex 小于 100 会藏在激活卡片“后面”
      // 这里的偏移量计算让它们从激活卡片的底缘开始，但间距更小
      const activeCardTop = activeIndex.value * VISIBLE_GAP_UP + 10;
      translateY = activeCardTop + (EXPANDED_CARD_HEIGHT - 60) + (index - activeIndex.value - 1) * VISIBLE_GAP_DOWN;
      zIndex = index;
      scale = 0.96;
      opacity = 0.7;
    }
  }

  return {
    transform: `translateX(-50%) translateY(${translateY}px) scale(${scale})`,
    zIndex: zIndex,
    opacity: opacity,
    position: 'absolute',
    top: '0',
    left: '50%',
    width: '100%',
    maxWidth: '1200px',
    height: `${EXPANDED_CARD_HEIGHT}px`,
    transition: 'all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)',
    cursor: activeIndex.value !== index ? 'pointer' : 'default',
    transformOrigin: 'top center'
  };
};

// 监听案例标题变化：只有当教案切换时，才自动更新所有 Agent 的待分类知识点
watch(() => props.caseTitle, (newTitle, oldTitle) => {
  if (newTitle && newTitle !== oldTitle) {
    agents.value.forEach(agent => {
      agent.unclassifiedKnowledge = [...props.theoreticalKnowledge];
      
      // 清空已分类的，因为新案例的知识点完全不同
      agent.classifiedKnowledge = {
        competent: [],
        novice: [],
        layman: []
      };
    });
    // ElMessage.success('已加载新案例知识背景库');
  }
}, { immediate: true });

// 全局更新知识点名称
const renameKnowledgeGlobal = (oldName, newName) => {
  if (!newName || oldName === newName) return;
  
  // 1. 更新后端 Case JSON
  if (updateKnowledge) updateKnowledge(oldName, newName);

  // 2. 更新本地 agents 的知识点
  agents.value.forEach(agent => {
    agent.unclassifiedKnowledge = agent.unclassifiedKnowledge.map(n => n === oldName ? newName : n);
    for (const key in agent.classifiedKnowledge) {
      agent.classifiedKnowledge[key] = agent.classifiedKnowledge[key].map(n => n === oldName ? newName : n);
    }
  });
};

// 全局新增知识点
const addNewKnowledgeGlobal = (name) => {
  if (!name) return;

  // 1. 更新后端 Case JSON
  if (addKnowledge) addKnowledge(name);

  // 2. 添加到所有 Agent 的 unclassified (如果不存在)
  agents.value.forEach(agent => {
    if (!agent.unclassifiedKnowledge.includes(name)) {
      agent.unclassifiedKnowledge.push(name);
    }
  });
};

// 全局删除知识点
const deleteKnowledgeGlobal = (name) => {
  if (!name) return;

  // 1. 更新后端 Case JSON
  if (deleteKnowledge) deleteKnowledge(name);

  // 2. 从所有 Agent 的列表中移除
  agents.value.forEach(agent => {
    agent.unclassifiedKnowledge = agent.unclassifiedKnowledge.filter(n => n !== name);
    for (const key in agent.classifiedKnowledge) {
      agent.classifiedKnowledge[key] = agent.classifiedKnowledge[key].filter(n => n !== name);
    }
  });
};

// 提供给 AgentCard 使用
provide('knowledgeActions', {
  renameKnowledge: renameKnowledgeGlobal,
  addKnowledge: addNewKnowledgeGlobal,
  deleteKnowledge: deleteKnowledgeGlobal
});

const addAgent = () => {
  agents.value.push(createDefaultAgent(agents.value.length));
  // 抽出新卡片：使其成为 active
  setTimeout(() => {
    activeIndex.value = agents.value.length - 1;
  }, 100);
};

const deleteAgent = (index) => {
  if (agents.value.length > 1) {
    agents.value.splice(index, 1);
    if (activeIndex.value >= agents.value.length) {
      activeIndex.value = Math.max(0, agents.value.length - 1);
    }
  } else {
    ElMessage.warning('请至少保留一个 Agent');
  }
};

const handleGlobalMouseDown = (e) => {
  // 点击背景折叠卡片
  const isBackground = e.target.classList.contains('view-b-content-wrapper') || 
                       e.target.classList.contains('view-b-container') ||
                       e.target.classList.contains('view-b-scroll-area');
  
  if (isBackground) {
    activeIndex.value = null;
  }

  if (!e.target.closest('input') && !e.target.closest('.cursor-text')) {
    cardRefs.value.forEach(card => {
      if (card && card.resetEditing) card.resetEditing();
    });
  }
};

const syncPersona = async () => {
  try {
    const formatPersonaForBackend = (agent) => {
      // 映射级别为数值或原始字符串，取决于后端需求
      // 这里根据 server.py 的期望进行转换
      const levelMap = { low: 3, medium: 6, high: 9 };
      
      return {
        reasoning_path: Array.isArray(agent.cognitive[2]) ? agent.cognitive[2].join(', ') : (agent.cognitive[2] || 'Linear Causality'),
        knowledge_integration: agent.plasticity === 'high' ? '系统化' : '碎片化',
        core_biases: [],
        sensitivity: levelMap[agent.social.confidence] || 5,
        proficiency: levelMap[agent.social.register] || 5,
        // 额外字段
        interaction_role: agent.social.role,
        learning_adaptivity: agent.plasticity
      };
    };

    const payload = {};
    agents.value.forEach((agent, idx) => {
      const key = agent.name || `Student_${idx}`;
      payload[key] = {
        name: agent.name,
        age: agent.age,
        major: agent.major,
        avatar: agent.avatar || 'avatar1.png',
        color: agent.cardColor,     // 兼容字段 1
        cardColor: agent.cardColor, // 兼容字段 2
        knowledge_background: {
           high: agent.classifiedKnowledge.competent,
           medium: agent.classifiedKnowledge.novice,
           low: agent.classifiedKnowledge.layman
        },
        cognitive_orientation: {
           attentional_anchor: agent.cognitive[0],
           reasoning_entry: agent.cognitive[1],
           causal_structure: agent.cognitive[2]
        },
        social_interaction_style: {
           verbal_confidence: agent.social.confidence,
           language_register: agent.social.register,
           interaction_role: agent.social.role
        },
        learning_adaptivity: agent.plasticity
      };
    });

    const response = await axios.post('http://127.0.0.1:8000/update_personas', payload);
    if (response.status === 200) {
      ElMessage.success('Successfully saved personas!');
      if (fetchPersonas) fetchPersonas();
    }
  } catch (error) {
    console.error('Error saving personas:', error);
    ElMessage.error('Failed to save configuration');
  }
};
</script>

<style scoped>
.view-b-content-wrapper {
  overflow: visible; /* 允许卡片溢出阴影显示 */
}

.header {
  padding: 8px 12px;
  flex-shrink: 0;
  background: #000000;
  margin: 0;
}
.header h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  text-align: left;
}

/* =========================================
   1. 基础布局 & 卡片容器 (Layout & Base)
   ========================================= */
.view-b-container {
  background: #ECECEC;
  color: #e5e7eb;
  border-radius: 12px;
  position: relative;
  overflow: hidden;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(128, 149, 202, 0.2);
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(128, 149, 202, 0.4);
}

.agent-card-wrapper {
  transform-origin: center top;
  will-change: transform, opacity;
}

/* Stack Transitions */
.stack-enter-active,
.stack-leave-active {
  transition: all 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.stack-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(200px) scale(0.8) !important;
}

.stack-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-100px) scale(0.9) !important;
}

.stack-move {
  transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.global-actions .save-button {
  background-color: #8095CA;
  border-color: #8095CA;
}
.global-actions .save-button:hover {
  background-color: #6D8DBE;
  border-color: #6D8DBE;
}

/* =========================================
   Actions Wrapper Styles
   ========================================= */
.actions-wrapper {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 6px 16px;
  background: #F0F0F0;
  border-top: 1px solid #E0E0E0;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.06);
  z-index: 300;
}

.add-agent-section-mini {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 4px 10px;
  background-color: transparent;
  border: 2px dashed #8095CA;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.add-agent-section-mini:hover {
  background-color: #E8E8E8;
}

.plus-icon {
  font-size: 14px;
  color: #8095CA;
  font-weight: 300;
  line-height: 1;
}

.add-text {
  font-size: 11px;
  color: #666666;
  font-weight: bold;
}
</style>
