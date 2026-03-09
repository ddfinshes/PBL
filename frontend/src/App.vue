<template>
  <div id="app-wrapper">
    <div class="dashboard-layout">
      <!-- Left Column: ViewA + ViewB (Collapsible) -->
      <div class="left-column" :class="{ collapsed: isLeftColumnCollapsed }">
        <!-- Expanded View -->
        <div v-if="!isLeftColumnCollapsed" class="left-column-expanded">
          <div style="display: flex; flex-direction: column; height: 100%; gap: 10px;">
            <div style="flex: 3; min-height: 0;">
              <ViewA 
                style="height: 100%;" 
                @analysis-complete="handleDataReady"
              />
            </div>
            
            <div style="flex: 8; min-height: 0;">
              <ViewB 
                style="height: 100%;"
                :theoretical-knowledge="caseResult?.theoretical_knowledge_points || []"
                :case-title="caseResult?.case_title || ''"
              />
            </div>
          </div>
        </div>

        <!-- Collapsed View: Agent List -->
        <div v-else class="left-column-collapsed">
          <div ref="agentListContainer" class="agent-list-container">
            <div 
              v-for="agent in personas" 
              :key="agent.id"
              class="agent-mini-card"
              :style="{ borderColor: agent.cardColor || '#CEDCFB' }"
            >
              <img 
                v-if="agent.avatar" 
                :src="`/avatar/${agent.avatar}`" 
                :alt="agent.name"
                class="agent-mini-avatar"
              />
              <div class="agent-mini-name" :style="{ backgroundColor: agent.cardColor || '#CEDCFB' }">
                {{ agent.name }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Column Separator with Toggle Button -->
      <div class="column-separator">
        <button 
          class="toggle-collapse-btn" 
          @click="isLeftColumnCollapsed = !isLeftColumnCollapsed"
          :title="isLeftColumnCollapsed ? 'Expand' : 'Collapse'"
        >
          <span class="toggle-icon">{{ isLeftColumnCollapsed ? '›' : '‹' }}</span>
        </button>
      </div>

      <!-- Center Column: ViewC + ViewD -->
      <div class="center-column">
        <div style="flex: 2.5; min-height: 0; overflow: hidden;">
          <ViewC 
            style="height: 100%;"
            :case-data="caseResult" 
            :raw-pdf-data="imagesResult" 
            @inspect-question="handleInspectQuestion"
          />
        </div>

        <div style="flex: 3; min-height: 0;">
          <ViewD style="height: 100%;" />
        </div>
      </div>

      <!-- Center-Right Column: ViewF -->
      <div class="center-right-column">
        <ViewF :active-context="activeContext" />
      </div>

      <!-- Right Column: ViewE + ViewG (two rows) -->
      <div class="right-column">
        <div class="right-top-row">
          <ViewE
            style="height: 100%;"
            :case-data="caseResult"
            :objective-evaluation-map="objectiveEvaluationMap"
            :discussion-end-map="discussionEndByQuestion"
          />
        </div>

        <div class="right-bottom-row">
          <ViewG
            style="height: 100%;"
            :objective-evaluation-map="objectiveEvaluationMap"
            :discussion-end-map="discussionEndByQuestion"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, provide } from 'vue';
import axios from 'axios';
import ViewA from './views/ViewA.vue';
import ViewB from './views/ViewB.vue';
import ViewC from './views/ViewC.vue';
import ViewD from './views/ViewD.vue';
import ViewE from './views/ViewE.vue';
import ViewF from './views/ViewF.vue';
import ViewG from './views/ViewG.vue';
import { usePBLSocket } from './composables/usePBLSocket.js';

const sessionId = `pbl-session-${Date.now()}`;

// Initialize Socket
const { 
  messages, 
  currentTopic, 
  isConnected, 
  isPaused, 
  startDiscussion, 
  togglePause, 
  sendTeacherIntervention,
  activeMessageId,
  rollbackTo,
  switchNodeFocus,
  activeQuestionInfo,
  selectedNodeLeafId,
  discussionStage,
  interventionSummaries,
  personas,
  fetchPersonas,
  getAgentConfig,
  getAgentColor,
  getAgentName,
  getAgentAvatar,
  objectiveEvaluationMap,
  discussionEndByQuestion,
  agentStateByQuestion,
} = usePBLSocket(sessionId, () => {});

const selectedTopic = ref(null);

const updateKnowledge = async (oldName, newName) => {
  if (!currentPdfFilename.value) return;
  try {
    await axios.post('http://127.0.0.1:8000/api/update-knowledge', {
      pdf_filename: currentPdfFilename.value,
      old_name: oldName,
      new_name: newName
    });
    if (caseResult.value && caseResult.value.theoretical_knowledge_points) {
      caseResult.value.theoretical_knowledge_points = caseResult.value.theoretical_knowledge_points.map(p => p === oldName ? newName : p);
    }
  } catch (error) {
    console.error('Failed to update knowledge:', error);
  }
};

const addKnowledge = async (name) => {
  if (!currentPdfFilename.value) return;
  try {
    await axios.post('http://127.0.0.1:8000/api/add-knowledge', {
      pdf_filename: currentPdfFilename.value,
      knowledge_point: name
    });
    if (caseResult.value) {
      if (!caseResult.value.theoretical_knowledge_points) {
        caseResult.value.theoretical_knowledge_points = [];
      }
      if (!caseResult.value.theoretical_knowledge_points.includes(name)) {
        caseResult.value.theoretical_knowledge_points.push(name);
      }
    }
  } catch (error) {
    console.error('Failed to add knowledge:', error);
  }
};

const deleteKnowledge = async (name) => {
  if (!currentPdfFilename.value) return;
  try {
    await axios.post('http://127.0.0.1:8000/api/delete-knowledge', {
      pdf_filename: currentPdfFilename.value,
      knowledge_point: name
    });
    if (caseResult.value && caseResult.value.theoretical_knowledge_points) {
      caseResult.value.theoretical_knowledge_points = caseResult.value.theoretical_knowledge_points.filter(p => p !== name);
    }
  } catch (error) {
    console.error('Failed to delete knowledge:', error);
  }
};

provide('sessionId', sessionId);
provide('pblSocket', {
  messages,
  currentTopic,
  isConnected,
  isPaused,
  startDiscussion,
  togglePause,
  sendTeacherIntervention,
  activeMessageId,
  rollbackTo,
  switchNodeFocus,
  selectedTopic,
  activeQuestionInfo,
  selectedNodeLeafId,
  discussionStage,
  interventionSummaries,
  objectiveEvaluationMap,
  discussionEndByQuestion,
  agentStateByQuestion,
  personas,
  fetchPersonas,
  getAgentConfig,
  getAgentColor,
  getAgentName,
  getAgentAvatar,
  updateKnowledge,
  addKnowledge,
  deleteKnowledge
});

const caseResult = ref(null);
const imagesResult = ref(null);
const activeContext = ref(null);
const currentPdfFilename = ref(null);
const isLeftColumnCollapsed = ref(false);

const handleDataReady = (payload) => {
  console.log('父组件收到数据:', payload);
  
  if (payload) {
    caseResult.value = payload.structure;
    imagesResult.value = payload.raw_images;
    currentPdfFilename.value = payload.pdf_filename;
  } else {
    caseResult.value = null;
    imagesResult.value = null;
    activeContext.value = null;
    currentPdfFilename.value = null;
  }
};

const handleInspectQuestion = (payload) => {
  console.log('父组件监听到问题查看:', payload);
  
  activeQuestionInfo.value = { 
    sceneIndex: payload.sceneIndex, 
    questionIndex: payload.questionIndex 
  };

  if (caseResult.value && caseResult.value.scenes[payload.sceneIndex]) {
    const scene = caseResult.value.scenes[payload.sceneIndex];
    activeContext.value = {
      story: scene.story_content,
      question: payload.data.question
    };
  }
};


</script>

<style>
/* Global styles */
html, body {
  margin: 0;
  padding: 0;
  height: 100vh;
  width: 100vw;
  background: #ffffff;
  overflow: hidden;
}

#app {
  height: 100vh;
  width: 100vw;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
}

#app-wrapper {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

/* 统一字体大小单位，利于自适应 */
body {
  font-size: 14px;
}

/* Dashboard Layout Styles */
.dashboard-layout {
  display: flex;
  width: 100%;
  height: 100%;
  gap: 10px;
  padding: 10px;
  background: #ffffff;
}

.left-column {
  flex: 0 0 32%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: flex 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.left-column.collapsed {
  flex: 0 0 100px;
}

.left-column-header {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.collapse-toggle-btn {
  background: #F0F0F0;
  border: 1px solid #E0E0E0;
  border-radius: 4px;
  width: 32px;
  height: 32px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s ease;
}

.collapse-toggle-btn:hover {
  background: #E0E0E0;
}

.chevron-icon {
  font-size: 20px;
  font-weight: bold;
  color: #666666;
  line-height: 1;
}

/* Column Separator & Toggle Button */
.column-separator {
  flex: 0 0 auto;
  width: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  background: linear-gradient(to right, rgba(224, 224, 224, 0) 0%, rgba(224, 224, 224, 0.3) 40%, rgba(224, 224, 224, 0.3) 60%, rgba(224, 224, 224, 0) 100%);
  border-left: 1px solid #E8E8E8;
  border-right: 1px solid #E8E8E8;
  transition: background 0.3s ease;
}

.column-separator:hover {
  background: linear-gradient(to right, rgba(224, 224, 224, 0) 0%, rgba(224, 224, 224, 0.5) 40%, rgba(224, 224, 224, 0.5) 60%, rgba(224, 224, 224, 0) 100%);
}

.toggle-collapse-btn {
  width: 22px;
  height: 44px;
  border: 1px solid #D0D0D0;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(4px);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  padding: 0;
  flex-shrink: 0;
}

.toggle-collapse-btn:hover {
  background: rgba(255, 255, 255, 0.95);
  border-color: #8095CA;
  box-shadow: 0 2px 8px rgba(128, 149, 202, 0.15);
  transform: scale(1.1);
}

.toggle-collapse-btn:active {
  transform: scale(0.95);
}

.toggle-icon {
  font-size: 12px;
  font-weight: 600;
  color: #888888;
  line-height: 1;
  transition: color 0.25s ease;
}

.toggle-collapse-btn:hover .toggle-icon {
  color: #8095CA;
}

.left-column-expanded {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.left-column-collapsed {
  flex: 1;
  overflow-y: auto;
  padding: 0 5px;
}

.agent-list-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.agent-mini-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 6px;
  border: 2px solid;
  border-radius: 4px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.agent-mini-card:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.agent-mini-avatar {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  object-fit: cover;
}

.agent-mini-name {
  font-size: 10px;
  font-weight: bold;
  color: #000000;
  padding: 3px 4px;
  border-radius: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 70px;
  text-align: center;
  line-height: 1.2;
}

.center-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.center-right-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.right-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.right-top-row {
  flex: 0.9;
  min-height: 0;
}

.right-bottom-row {
  flex: 1.6;
  min-height: 0;
}
</style>