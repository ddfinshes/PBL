<template>
  <div id="app-wrapper">
    <div class="dashboard-layout">
      <!-- Left Column: ViewA + ViewB (Collapsible) -->
      <div class="left-column" :class="{ collapsed: isLeftColumnCollapsed }">
        <!-- Expanded View -->
        <div v-show="!isLeftColumnCollapsed" class="left-column-expanded">
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
                :case-data="caseResult"
                :case-title="caseResult?.case_title || ''"
                :is-left-column-collapsed="isLeftColumnCollapsed"
              />
            </div>
          </div>
        </div>

        <!-- Collapsed View: Agent List -->
        <div v-show="isLeftColumnCollapsed" class="left-column-collapsed">
          <div ref="agentListContainer" class="agent-list-container">
            <div 
              v-for="agent in agents" 
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
              <div class="agent-mini-metrics">
                <div class="mini-metric-block">
                  <div class="mini-metric-label">Self<br/>Efficiency</div>
                  <div class="mini-metric-track">
                    <div
                      class="mini-metric-fill"
                      :style="{
                        height: getAgentMetricVisual(agent).selfHeight,
                        backgroundColor: getAgentMetricVisual(agent).selfColor
                      }"
                    />
                  </div>
                </div>
                <div class="mini-metric-block">
                  <div class="mini-metric-track">
                    <div
                      class="mini-metric-fill"
                      :style="{
                        height: getAgentMetricVisual(agent).loadHeight,
                        backgroundColor: getAgentMetricVisual(agent).loadColor
                      }"
                    />
                  </div>
                  <div class="mini-metric-label">Cognitive<br/>Load</div>
                </div>
              </div>
              <div v-if="agent.tags?.length" class="agent-mini-tags">
                <span 
                  v-for="(tag, idx) in agent.tags" 
                  :key="idx" 
                  class="mini-tag-pill"
                >
                  {{ tag }}
                </span>
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

      <!-- Right Column: ViewE -->
      <div class="right-column">
        <ViewE
          style="height: 100%;"
          :case-data="caseResult"
          :objective-evaluation-map="objectiveEvaluationMap"
          :discussion-end-map="discussionEndByQuestion"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, provide } from 'vue';
import axios from 'axios';
import ViewA from './views/ViewA.vue';
import ViewB from './views/ViewB.vue';
import ViewC from './views/ViewC.vue';
import ViewD from './views/ViewD.vue';
import ViewE from './views/ViewE.vue';
import ViewF from './views/ViewF.vue';
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
  knowledgeCoverageByQuestion,
  forceResume,
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
  knowledgeCoverageByQuestion,
  personas,
  fetchPersonas,
  getAgentConfig,
  getAgentColor,
  getAgentName,
  getAgentAvatar,
  updateKnowledge,
  addKnowledge,
  deleteKnowledge
  ,forceResume
});

const caseResult = ref(null);
const imagesResult = ref(null);
const activeContext = ref(null);
const currentPdfFilename = ref(null);
const isLeftColumnCollapsed = ref(false);
const agents = ref([]);

provide('agentList', agents);

const handleDataReady = (payload) => {
  console.log('Parent component received data:', payload);
  
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
  console.log('Parent component detected question inspection:', payload);
  
  activeQuestionInfo.value = { 
    sceneIndex: payload.sceneIndex, 
    questionIndex: payload.questionIndex,
    caseName: caseResult.value?.case_title || ''
  };

  if (caseResult.value && caseResult.value.scenes[payload.sceneIndex]) {
    const scene = caseResult.value.scenes[payload.sceneIndex];
    activeContext.value = {
      story: scene.story_content,
      question: payload.data.question
    };
  }
};

const STATE_COLOR_SEVERE = '#FFABAB';
const STATE_COLOR_MEDIUM = '#FFEDD5';
const STATE_COLOR_NORMAL = '#E3FCE7';

const activeQuestionKey = computed(() => {
  const sceneIndex = Number(activeQuestionInfo.value?.sceneIndex ?? -1);
  const questionIndex = Number(activeQuestionInfo.value?.questionIndex ?? -1);
  if (sceneIndex < 0 || questionIndex < 0) return null;
  return `${sceneIndex}_${questionIndex}`;
});

const activeAgentStateSnapshot = computed(() => {
  const allSnapshots = agentStateByQuestion.value || {};
  const key = activeQuestionKey.value;
  if (key && allSnapshots[key]) return allSnapshots[key];

  const latest = Object.values(allSnapshots)
    .filter((item) => item && typeof item === 'object')
    .sort((a, b) => Number(b.updatedAt || 0) - Number(a.updatedAt || 0))[0];
  return latest || {};
});

const normalizeKey = (raw) => String(raw || '').trim().toLowerCase();

const buildCandidateAgentKeys = (agent) => {
  const id = String(agent?.id || '').trim();
  const name = String(agent?.name || '').trim();
  const prefixedId = id.startsWith('agent-') ? id.slice(6) : id;
  return [id, prefixedId, name]
    .map(normalizeKey)
    .filter(Boolean);
};

const readRuntimeMetric = (stateMap, agent) => {
  if (!stateMap || typeof stateMap !== 'object') return null;
  const entries = Object.entries(stateMap);
  if (!entries.length) return null;

  const candidates = buildCandidateAgentKeys(agent);
  if (!candidates.length) return null;

  const hit = entries.find(([k]) => candidates.includes(normalizeKey(k)));
  return hit ? Number(hit[1]) : null;
};

const clampMetric = (value, fallback = 6) => {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(1, Math.min(9, Math.round(n)));
};

const selfEfficacyColor = (value) => {
  const level = clampMetric(value, 6);
  if (level <= 4) return STATE_COLOR_SEVERE;
  if (level <= 6) return STATE_COLOR_MEDIUM;
  return STATE_COLOR_NORMAL;
};

const cognitiveLoadColor = (value) => {
  const level = clampMetric(value, 6);
  if (level >= 8) return STATE_COLOR_SEVERE;
  if (level >= 5) return STATE_COLOR_MEDIUM;
  return STATE_COLOR_NORMAL;
};

const barHeightPercent = (value) => {
  const level = clampMetric(value, 6);
  return `${Math.round((level / 9) * 100)}%`;
};

const getAgentMetricVisual = (agent) => {
  const snapshot = activeAgentStateSnapshot.value || {};
  const selfRaw = readRuntimeMetric(snapshot.self_efficacy, agent);
  const loadRaw = readRuntimeMetric(snapshot.cognitive_load, agent);
  const selfLevel = clampMetric(selfRaw, 6);
  const loadLevel = clampMetric(loadRaw, 6);

  return {
    selfLevel,
    loadLevel,
    selfColor: selfEfficacyColor(selfLevel),
    loadColor: cognitiveLoadColor(loadLevel),
    selfHeight: barHeightPercent(selfLevel),
    loadHeight: barHeightPercent(loadLevel),
  };
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

/* Unified font sizing for responsive design */
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

.dashboard-layout > * {
  min-width: 0;
}

.left-column {
  flex: 0 0 clamp(680px, 40vw, 1180px);
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: flex 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.left-column.collapsed {
  flex: 0 0 160px;
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
  gap: 6px;
}

.agent-mini-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 4px;
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
  width: 48px;
  height: 48px;
  border-radius: 50%;
  object-fit: cover;
}

.agent-mini-name {
  font-size: 10px;
  font-weight: bold;
  color: #000000;
  padding: 2px 6px;
  border-radius: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100px;
  text-align: center;
  line-height: 1.1;
}

.agent-mini-metrics {
  width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 6px;
  margin-top: 2px;
}

.mini-metric-block {
  flex: 1;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 3px;
}

.mini-metric-label {
  font-size: 8px;
  font-weight: 700;
  color: #111111;
  line-height: 1;
  text-align: center;
  white-space: normal;
  word-break: keep-all;
}

.mini-metric-track {
  width: 12px;
  height: 32px;
  border-radius: 6px;
  background: #e7e7ea;
  overflow: hidden;
  position: relative;
}

.mini-metric-fill {
  width: 100%;
  position: absolute;
  bottom: 0;
  left: 0;
  border-radius: 6px;
  transition: height 0.3s ease, background-color 0.3s ease;
}

.agent-mini-tags {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  width: 100%;
  margin-top: 2px;
}

.mini-tag-pill {
  font-size: 10px;
  font-weight: 500;
  padding: 2px 6px;
  background: rgba(128, 149, 202, 0.2);
  color: #2c3e50;
  border: 1px solid rgba(128, 149, 202, 0.4);
  border-radius: 4px;
  width: 100%;
  max-width: 110px;
  text-align: center;
  word-wrap: break-word;
  word-break: break-all;
  line-height: 1.1;
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

/* 2K and below: slightly increase first-column share to avoid panel overlap at browser zoom */
@media (max-width: 2048px) {
  .left-column {
    flex-basis: clamp(680px, 42vw, 1060px);
  }
}

/* FHD and below: reserve more width for ViewA/ViewB stack */
@media (max-width: 1920px) {
  .left-column {
    flex-basis: clamp(680px, 44vw, 1020px);
  }
}

/* Laptop/common teaching screens */
@media (max-width: 1600px) {
  .dashboard-layout {
    gap: 8px;
    padding: 8px;
  }

  .left-column {
    flex-basis: clamp(660px, 46vw, 980px);
  }
}

/* 1366-level screens: prioritize left column to keep config+preview readable */
@media (max-width: 1440px) {
  .left-column {
    flex-basis: clamp(640px, 49vw, 940px);
  }

  .dashboard-layout {
    gap: 6px;
    padding: 6px;
  }
}
</style>