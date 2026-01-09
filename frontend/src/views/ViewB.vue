<template>
  <div class="view-b-container p-4 bg-transparent h-screen overflow-y-auto" @mousedown="handleGlobalMouseDown">
    <div class="view-b-content-wrapper w-full">
      <div class="agent-list flex flex-col gap-12 items-center p-4 w-full">
        
        <!-- Individual Agent Cards -->
        <AgentCard 
          v-for="(agent, index) in agents" 
          :key="agent.id"
          ref="cardRefs"
          v-model="agents[index]"
          :cognitive-options="cognitiveOptions"
          :interaction-roles="interactionRoles"
          @delete="deleteAgent(index)"
        />

        <!-- Add Agent Action Area -->
        <div class="add-agent-section flex flex-row items-center justify-center cursor-pointer hover:bg-[#CEDCFB]/60 transition-all flex-shrink-0 gap-4"
          @click="addAgent"
        >
          <div class="plus-icon text-[48px] text-[#84A7D8] font-light">+</div>
          <div class="add-text text-[18px] text-[#2d3748] font-bold">Add New Agent Template</div>
        </div>

        <!-- Global Save Action -->
        <div class="global-actions mt-4 text-center pb-20">
          <el-button type="primary" size="large" @click="syncPersona" class="save-button px-20 py-6 rounded-full text-lg shadow-xl">
            保存所有 Agent 配置
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import axios from 'axios';
import { ElMessage } from 'element-plus';
import AgentCard from '../components/AgentCard.vue';

const props = defineProps({
  theoreticalKnowledge: {
    type: Array,
    default: () => []
  }
});

// Refs for individual cards to handle global events like "cancelling edit"
const cardRefs = ref([]);

const cognitiveOptions = {
  0: ['Patient Events', 'Symptoms', 'Social Cues'],
  1: ['Mechanism', 'External Factors', 'Risk Perception', 'Familiarity Driven'],
  2: ['Linear Causality', 'Multi-Concurrent', 'Cues-Driven', 'Undefined']
};

const interactionRoles = [
  { name: '负责人', value: 'leader', icon: 'image.png' },
  { name: '观察者', value: 'follower', icon: 'image.png' },
  { name: '质疑者', value: 'critical', icon: 'image.png' }
];

const createDefaultAgent = () => ({
  id: 'agent-' + Date.now(),
  name: '',
  age: '',
  major: '',
  // 待分类知识点：优先使用 PDF 提取的内容
  unclassifiedKnowledge: props.theoreticalKnowledge.length > 0 
    ? [...props.theoreticalKnowledge] 
    : [], 
  // 已分类知识点，对应三个档次
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

const agents = ref([createDefaultAgent()]);

// 监听背景知识变化：当新 PDF 解析完成后，自动更新所有 Agent 的待分类知识点
watch(() => props.theoreticalKnowledge, (newPoints) => {
  if (newPoints && newPoints.length > 0) {
    agents.value.forEach(agent => {
      // 只有当 agent 的待分类知识点是默认值或为空时才自动覆盖
      // 或者您可以选择直接覆盖，取决于业务逻辑。这里我们采取“有新数据就更新”的策略
      agent.unclassifiedKnowledge = [...newPoints];
      
      // 同时清空已分类的，因为新案例的知识点完全不同
      agent.classifiedKnowledge = {
        competent: [],
        novice: [],
        layman: []
      };
    });
    ElMessage.success('已根据教案更新 Agent 知识背景库');
  }
}, { immediate: true });

const addAgent = () => {
  agents.value.push(createDefaultAgent());
};

const deleteAgent = (index) => {
  if (agents.value.length > 1) {
    agents.value.splice(index, 1);
  } else {
    ElMessage.warning('请至少保留一个 Agent');
  }
};

const handleGlobalMouseDown = (e) => {
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
        "knowledge background": {
           high: agent.classifiedKnowledge.competent,
           medium: agent.classifiedKnowledge.novice,
           low: agent.classifiedKnowledge.layman
        },
        "cognitive orientation": {
           "attentional anchor": agent.cognitive[0],
           "reasoning entry": agent.cognitive[1],
           "causal structure": agent.cognitive[2]
        },
        "social interaction style": {
           "verbal confidence": agent.social.confidence,
           "language register": agent.social.register,
           "interaction role": agent.social.role
        },
        "learning adaptivity": agent.plasticity
      };
    });

    const response = await axios.post('http://127.0.0.1:8000/update_personas', payload);
    if (response.status === 200) {
      ElMessage.success('配置保存成功！');
    }
  } catch (error) {
    console.error('Error saving personas:', error);
    ElMessage.error('配置保存失败');
  }
};
</script>

<style scoped>
.view-b-container::-webkit-scrollbar {
  width: 6px;
}
.view-b-container::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.1);
  border-radius: 10px;
}

.add-agent-section {
  width: 100%;
  max-width: 1200px;
  height: 120px;
  background-color: rgba(206, 220, 251, 0.4);
  border: 2px dashed #84A7D8;
  border-radius: 20px;
}
</style>
