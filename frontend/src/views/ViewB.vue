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
            <div class="agent-dual-panel">
              <div class="agent-config-panel">
                <AgentCard 
                  ref="cardRefs"
                  v-model="agents[index]"
                  :interaction-roles="interactionRoles"
                  :card-color="agents[index].cardColor"
                  @delete="deleteAgent(index)"
                />
              </div>

              <aside class="agent-preview-panel" @click.stop>
                <div class="preview-title">Agent Preview</div>

                <div class="preview-bubble before">
                  <div class="bubble-tag">Before Adjustment</div>
                  <p>{{ getAgentPreview(agent).before_text }}</p>
                </div>

                <div class="preview-avatar-center">
                  <img
                    class="preview-avatar"
                    :src="`/avatar/${agent.avatar || 'avatar1.png'}`"
                    :alt="agent.name || 'Agent avatar'"
                  />
                </div>

                <div class="preview-bubble after">
                  <div class="bubble-tag">After Adjustment</div>
                  <p>{{ previewLoadingByAgent[agent.id] ? '正在根据当前参数生成预览...' : getAgentPreview(agent).after_text }}</p>
                </div>

                <div class="preview-description-box">
                  <div class="description-tag">Behavior Description</div>
                  <p>{{ previewLoadingByAgent[agent.id] ? '正在生成该 Agent 的行为描述...' : getAgentPreview(agent).behavior_description }}</p>
                </div>
              </aside>
            </div>
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
        <el-button
          type="primary"
          size="small"
          :loading="isGeneratingPersonaPrompt"
          :disabled="isGeneratingPersonaPrompt"
          @click="syncPersona"
          class="save-button"
        >
          {{ isGeneratingPersonaPrompt ? 'Cloning Agents...' : 'Save' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, inject, provide, onMounted, onBeforeUnmount } from 'vue';
import axios from 'axios';
import { ElMessage } from 'element-plus';
import AgentCard from '../components/AgentCard.vue';

const {
  personas,
  fetchPersonas,
  updateKnowledge,
  addKnowledge,
  deleteKnowledge
} = inject('pblSocket', {});

const props = defineProps({
  theoreticalKnowledge: {
    type: Array,
    default: () => []
  },
  caseData: {
    type: Object,
    default: null
  },
  caseTitle: {
    type: String,
    default: ''
  }
});

// Refs for individual cards to handle global events like "cancelling edit"
const cardRefs = ref([]);
const activeIndex = ref(0);
const isGeneratingPersonaPrompt = ref(false);

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
  learning_styles: {
    surface: 3,
    deep: 3,
    strategic: 3
  },
  personality: {
    openness: 3,
    conscientiousness: 3,
    extraversion: 3,
    agreeableness: 3,
    neuroticism: 3
  },
  cognitiveOrientation: 'line_based',
  social: {
    confidence: 'medium',
    register: 'medium',
    participation: 'medium',
    role: 'leader'
  },
  plasticity: 'medium'
});

const agents = ref([createDefaultAgent(0)]);
const previewByAgent = ref({});
const previewLoadingByAgent = ref({});
const previewRequestVersionByAgent = ref({});
const previewAbortByAgent = ref({});
const previewDebounceByAgent = ref({});
const previewSignatureByAgent = ref({});

const getFirstQuestionFromCaseData = (caseData) => {
  if (!caseData || typeof caseData !== 'object') return '';

  const scenes = Array.isArray(caseData.scenes) ? caseData.scenes : [];
  const firstScene = scenes[0] || null;
  if (firstScene && typeof firstScene === 'object') {
    const fromQuestions = Array.isArray(firstScene.questions) ? firstScene.questions : [];
    const q1 = fromQuestions[0];
    if (typeof q1?.question === 'string' && q1.question.trim()) return q1.question.trim();
    if (typeof q1 === 'string' && q1.trim()) return q1.trim();

    const fromTriggerQuestions = Array.isArray(firstScene.trigger_questions)
      ? firstScene.trigger_questions
      : [];
    const tq1 = fromTriggerQuestions[0];
    if (typeof tq1?.question === 'string' && tq1.question.trim()) return tq1.question.trim();
    if (typeof tq1 === 'string' && tq1.trim()) return tq1.trim();
  }

  const rootTriggerQuestions = Array.isArray(caseData.trigger_questions)
    ? caseData.trigger_questions
    : [];
  const rtq1 = rootTriggerQuestions[0];
  if (typeof rtq1?.question === 'string' && rtq1.question.trim()) return rtq1.question.trim();
  if (typeof rtq1 === 'string' && rtq1.trim()) return rtq1.trim();

  return '';
};

const firstQuestionText = computed(() => {
  const q = getFirstQuestionFromCaseData(props.caseData);
  if (q) return q;
  return 'Upload a case to preview how this agent answers the first trigger question.';
});

const hasRealFirstQuestion = computed(() => {
  return Boolean(getFirstQuestionFromCaseData(props.caseData));
});

const toScore = (v, fallback = 3) => {
  const n = Number(v);
  return Number.isFinite(n) ? Math.max(1, Math.min(5, Math.round(n))) : fallback;
};

const toPreviewPersona = (agent) => {
  const fallbackName = agent?.name || 'Student';
  return {
    name: fallbackName,
    age: agent?.age || '',
    major: agent?.major || '',
    learning_styles: {
      surface: toScore(agent?.learning_styles?.surface),
      deep: toScore(agent?.learning_styles?.deep),
      strategic: toScore(agent?.learning_styles?.strategic)
    },
    personality: {
      openness: toScore(agent?.personality?.openness),
      conscientiousness: toScore(agent?.personality?.conscientiousness),
      extraversion: toScore(agent?.personality?.extraversion),
      agreeableness: toScore(agent?.personality?.agreeableness),
      neuroticism: toScore(agent?.personality?.neuroticism)
    },
    knowledge_background: {
      high: Array.isArray(agent?.classifiedKnowledge?.competent) ? agent.classifiedKnowledge.competent : [],
      medium: Array.isArray(agent?.classifiedKnowledge?.novice) ? agent.classifiedKnowledge.novice : [],
      low: Array.isArray(agent?.classifiedKnowledge?.layman) ? agent.classifiedKnowledge.layman : []
    },
    cognitive_orientation: agent?.cognitiveOrientation || 'line_based',
    learning_adaptivity: agent?.plasticity || 'medium'
  };
};

const getAgentPreview = (agent) => {
  const key = agent?.id;
  const preview = key ? previewByAgent.value[key] : null;
  if (preview) return preview;
  return {
    before_text: `针对“${firstQuestionText.value}”，将基于基础配置进行对照分析。`,
    after_text: '请调整参数后查看实时生成的风格化回答。',
    action_display: '',
    behavior_description: '系统将根据当前参数自动生成该 Agent 的行为描述。'
  };
};

const requestAgentPreview = async (agent) => {
  if (!agent?.id || !hasRealFirstQuestion.value) return;

  const currentPreview = previewByAgent.value[agent.id] || {};
  const previousAfterText = String(currentPreview.after_text || '').trim();
  const previousBeforeText = String(currentPreview.before_text || '').trim();

  const prevController = previewAbortByAgent.value[agent.id];
  if (prevController) {
    prevController.abort();
  }
  const controller = new AbortController();
  previewAbortByAgent.value = {
    ...previewAbortByAgent.value,
    [agent.id]: controller
  };

  const currentVersion = (previewRequestVersionByAgent.value[agent.id] || 0) + 1;
  previewRequestVersionByAgent.value[agent.id] = currentVersion;
  previewLoadingByAgent.value = {
    ...previewLoadingByAgent.value,
    [agent.id]: true
  };

  try {
    const response = await axios.post('http://127.0.0.1:8000/api/agent-preview', {
      agent_id: agent.name || agent.id,
      persona: toPreviewPersona(agent),
      trigger_question: firstQuestionText.value
    }, {
      signal: controller.signal
    });

    if (previewRequestVersionByAgent.value[agent.id] !== currentVersion) return;

    if (response?.data?.status === 'success') {
      const afterText = String(response.data.after_text || '').trim();
      const beforeText = previousAfterText || previousBeforeText || String(response.data.before_text || '').trim();
      previewByAgent.value = {
        ...previewByAgent.value,
        [agent.id]: {
          before_text: beforeText,
          after_text: afterText,
          action_display: response.data.action_display || '',
          behavior_description: String(response.data.behavior_description || '').trim() || '该 Agent 的行为描述生成失败，请重试。'
        }
      };
    }
  } catch (error) {
    if (previewRequestVersionByAgent.value[agent.id] !== currentVersion) return;
    if (error?.name !== 'CanceledError' && error?.code !== 'ERR_CANCELED') {
      console.error('Failed to fetch agent preview:', error);
    }
  } finally {
    if (previewRequestVersionByAgent.value[agent.id] === currentVersion) {
      previewLoadingByAgent.value = {
        ...previewLoadingByAgent.value,
        [agent.id]: false
      };
    }

    const latestController = previewAbortByAgent.value[agent.id];
    if (latestController === controller) {
      const nextMap = { ...previewAbortByAgent.value };
      delete nextMap[agent.id];
      previewAbortByAgent.value = nextMap;
    }
  }
};

const buildAgentPreviewSignature = (agent) => {
  if (!agent?.id) return '';
  if (!hasRealFirstQuestion.value) return `no-question:${agent.id}`;
  const persona = toPreviewPersona(agent);
  return JSON.stringify({
    question: firstQuestionText.value,
    persona
  });
};

const scheduleAgentPreviewRefresh = (agentId) => {
  const agent = agents.value.find(item => item.id === agentId);
  if (!agent) return;

  const runningController = previewAbortByAgent.value[agentId];
  if (runningController) {
    runningController.abort();
  }

  const oldTimer = previewDebounceByAgent.value[agentId];
  if (oldTimer) clearTimeout(oldTimer);

  const timerId = setTimeout(() => {
    const nextDebounce = { ...previewDebounceByAgent.value };
    delete nextDebounce[agentId];
    previewDebounceByAgent.value = nextDebounce;
    requestAgentPreview(agent);
  }, 420);

  previewDebounceByAgent.value = {
    ...previewDebounceByAgent.value,
    [agentId]: timerId
  };
};

const mapBackendPersonaToAgent = (persona, index = 0, backendKey = '') => {
  const highKnowledge = Array.isArray(persona?.knowledge_background?.high)
    ? [...persona.knowledge_background.high]
    : [];
  const mediumKnowledge = Array.isArray(persona?.knowledge_background?.medium)
    ? [...persona.knowledge_background.medium]
    : [];
  const lowKnowledge = Array.isArray(persona?.knowledge_background?.low)
    ? [...persona.knowledge_background.low]
    : [];

  const classifiedSet = new Set([...highKnowledge, ...mediumKnowledge, ...lowKnowledge]);
  const unclassifiedKnowledge = Array.isArray(props.theoreticalKnowledge)
    ? props.theoreticalKnowledge.filter(point => !classifiedSet.has(point))
    : [];

  return {
    ...createDefaultAgent(index),
    id: `agent-${backendKey || index}`,
    name: persona?.name ?? '',
    age: persona?.age ?? '',
    major: persona?.major ?? '',
    avatar: persona?.avatar || 'avatar1.png',
    cardColor: persona?.cardColor || persona?.color || cardColors[index % cardColors.length],
    unclassifiedKnowledge,
    classifiedKnowledge: {
      competent: highKnowledge,
      novice: mediumKnowledge,
      layman: lowKnowledge
    },
    structuralKnowledge: persona?.knowledge_background?.structural_level || 'medium',
    learning_styles: {
      surface: Number(persona?.learning_styles?.surface) || 3,
      deep: Number(persona?.learning_styles?.deep) || 3,
      strategic: Number(persona?.learning_styles?.strategic) || 3
    },
    personality: {
      openness: Number(persona?.personality?.openness) || 3,
      conscientiousness: Number(persona?.personality?.conscientiousness) || 3,
      extraversion: Number(persona?.personality?.extraversion) || 3,
      agreeableness: Number(persona?.personality?.agreeableness) || 3,
      neuroticism: Number(persona?.personality?.neuroticism) || 3
    },
    cognitiveOrientation: persona?.cognitive_orientation || 'line_based',
    social: {
      confidence: persona?.social?.confidence || 'medium',
      register: persona?.social?.register || 'medium',
      participation: persona?.social?.participation || 'medium',
      role: persona?.interaction_role || persona?.social?.role || 'leader'
    },
    plasticity: persona?.learning_adaptivity || 'medium'
  };
};

const restoreAgentsFromBackend = async () => {
  try {
    let personaMap = {};

    if (fetchPersonas) {
      await fetchPersonas();
      personaMap = personas?.value && typeof personas.value === 'object'
        ? personas.value
        : {};
    }

    if (!Object.keys(personaMap).length) {
      const response = await axios.get('http://127.0.0.1:8000/get_personas');
      personaMap = response?.data && typeof response.data === 'object' ? response.data : {};
    }

    const entries = Object.entries(personaMap);

    if (!entries.length) return;

    agents.value = entries.map(([backendKey, persona], index) =>
      mapBackendPersonaToAgent(persona, index, backendKey)
    );
    activeIndex.value = 0;
  } catch (error) {
    console.error('Failed to restore personas in ViewB:', error);
  }
};

onMounted(() => {
  restoreAgentsFromBackend();
});

onBeforeUnmount(() => {
  Object.values(previewDebounceByAgent.value).forEach(timerId => clearTimeout(timerId));
  Object.values(previewAbortByAgent.value).forEach(controller => controller?.abort?.());
  previewDebounceByAgent.value = {};
  previewAbortByAgent.value = {};
});

watch(firstQuestionText, () => {
  if (!hasRealFirstQuestion.value) return;
  agents.value.forEach(agent => {
    previewSignatureByAgent.value[agent.id] = '';
    scheduleAgentPreviewRefresh(agent.id);
  });
}, { immediate: true });

watch(agents, () => {
  const seenIds = new Set();

  agents.value.forEach(agent => {
    const aid = agent?.id;
    if (!aid) return;
    seenIds.add(aid);

    const nextSignature = buildAgentPreviewSignature(agent);
    const prevSignature = previewSignatureByAgent.value[aid] || '';

    if (nextSignature !== prevSignature) {
      previewSignatureByAgent.value[aid] = nextSignature;
      if (hasRealFirstQuestion.value) {
        scheduleAgentPreviewRefresh(aid);
      }
    }
  });

  Object.keys(previewSignatureByAgent.value).forEach(aid => {
    if (seenIds.has(aid)) return;

    const timerId = previewDebounceByAgent.value[aid];
    if (timerId) clearTimeout(timerId);

    const runningController = previewAbortByAgent.value[aid];
    if (runningController) runningController.abort();

    const nextSign = { ...previewSignatureByAgent.value };
    const nextTimer = { ...previewDebounceByAgent.value };
    const nextAbort = { ...previewAbortByAgent.value };
    const nextPreview = { ...previewByAgent.value };
    const nextLoading = { ...previewLoadingByAgent.value };

    delete nextSign[aid];
    delete nextTimer[aid];
    delete nextAbort[aid];
    delete nextPreview[aid];
    delete nextLoading[aid];

    previewSignatureByAgent.value = nextSign;
    previewDebounceByAgent.value = nextTimer;
    previewAbortByAgent.value = nextAbort;
    previewByAgent.value = nextPreview;
    previewLoadingByAgent.value = nextLoading;
  });
}, { deep: true });

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
    maxWidth: '100%',
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
  isGeneratingPersonaPrompt.value = true;
  try {
    const formatPersonaForBackend = (agent) => {
      // 映射级别为数值或原始字符串，取决于后端需求
      // 这里根据 server.py 的期望进行转换
      const levelMap = { low: 3, medium: 6, high: 9 };
      
      return {
        reasoning_path: agent.cognitiveOrientation || 'line_based',
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
        color: agent.cardColor,     
        cardColor: agent.cardColor, 
        learning_styles: {
          surface: Number(agent.learning_styles?.surface) || 3,
          deep: Number(agent.learning_styles?.deep) || 3,
          strategic: Number(agent.learning_styles?.strategic) || 3
        },
        personality: {
          openness: Number(agent.personality?.openness) || 3,
          conscientiousness: Number(agent.personality?.conscientiousness) || 3,
          extraversion: Number(agent.personality?.extraversion) || 3,
          agreeableness: Number(agent.personality?.agreeableness) || 3,
          neuroticism: Number(agent.personality?.neuroticism) || 3
        },
        knowledge_background: {
           high: agent.classifiedKnowledge.competent,
           medium: agent.classifiedKnowledge.novice,
            low: agent.classifiedKnowledge.layman
        },
        cognitive_orientation: agent.cognitiveOrientation || 'line_based',
        learning_adaptivity: agent.plasticity
      };
    });

    ElMessage.info('Calling LLM to generate learning-style/personality prompt...');

    const response = await axios.post('http://127.0.0.1:8000/update_personas', payload);
    if (response.status === 200) {
      ElMessage.success('Successfully saved personas!');
      if (fetchPersonas) fetchPersonas();
    }
  } catch (error) {
    console.error('Error saving personas:', error);
    ElMessage.error('Failed to save configuration');
  } finally {
    isGeneratingPersonaPrompt.value = false;
  }
};
</script>

<style scoped>
.view-b-content-wrapper {
  overflow: visible; /* 允许卡片溢出阴影显示 */
}

.view-b-scroll-area {
  overflow-x: hidden;
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

.agent-dual-panel {
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.95fr);
  gap: 10px;
  align-items: stretch;
}

.agent-config-panel {
  min-width: 0;
}

.agent-preview-panel {
  background: #f8f9ff;
  border: 1px solid #d7ddf2;
  border-radius: 20px;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 12px;
  overflow: hidden;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.preview-title {
  font-size: 13px;
  font-weight: 700;
  color: #2f3a63;
  text-align: center;
  letter-spacing: 0.02em;
  margin-top: 0;
  flex-shrink: 0;
}

.preview-avatar-center {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 2px 0;
}

.preview-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid #ffffff;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.14);
  background: #ffffff;
}

.preview-bubble {
  border-radius: 14px;
  padding: 9px 10px;
  border: 1px solid;
  max-height: 230px;
  overflow-y: auto;
}

.preview-description-box {
  border-radius: 12px;
  padding: 8px 10px;
  border: 1px solid #d7ddf2;
  background: #ffffff;
  max-height: 120px;
  overflow-y: auto;
}

.description-tag {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 4px;
  color: #5b668a;
}

.preview-description-box p {
  margin: 0;
  font-size: 11px;
  line-height: 1.4;
  color: #2a2f45;
}

.preview-bubble p {
  margin: 0;
  font-size: 11px;
  line-height: 1.45;
  color: #2a2f45;
}

.preview-bubble.before {
  background: #edf2ff;
  border-color: #cfdaf8;
}

.preview-bubble.after {
  background: #e9f6f2;
  border-color: #c9e9dd;
}

.bubble-tag {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 5px;
  color: #5b668a;
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
