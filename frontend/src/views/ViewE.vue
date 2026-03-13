<template>
  <div class="view-e-container h-full flex flex-col bg-[#ECECEC] rounded-xl border border-gray-300 overflow-hidden">
    <div class="view-e-header">
      <h2 class="view-title">Global State Evaluation</h2>
    </div>

    <div class="flex-1 overflow-y-auto px-4 py-4 objective-scroll">
      <div v-if="!hasActiveQuestion" class="empty-state">
        <p>Select a trigger question to view objective completion.</p>
      </div>

      <div v-else>
        <div class="context-card">
          <div class="context-title">Current Trigger Question</div>
          <div class="context-text">{{ currentTriggerQuestion || 'Not available' }}</div>
        </div>

        <div class="progress-card">
          <div class="progress-row">
            <span class="progress-label">Completion</span>
            <span class="progress-value">{{ achievedCount }}/{{ objectiveRows.length }}</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: `${progressPercent}%` }"></div>
          </div>
        </div>

        <div v-if="objectiveRows.length === 0" class="empty-state">
          <p>No learning objectives evaluated yet for this trigger question.</p>
        </div>

        <div v-else class="objective-list">
          <div
            v-for="(row, idx) in objectiveRows"
            :key="`${idx}-${row.objective}`"
            class="objective-item"
            :class="row.statusClass"
          >
            <div class="objective-top">
              <div class="objective-index">LO{{ idx + 1 }}</div>
              <div class="objective-top-right">
                <div class="objective-status">{{ row.statusLabel }}</div>
                <button
                  class="override-btn"
                  :class="{
                    'override-achieved': row.override === 'achieved',
                    'override-in-progress': row.override === 'in_progress',
                    'override-auto': row.override === null
                  }"
                  :title="row.override === 'achieved' ? 'Manual: Achieved (click to change to In Progress)' : row.override === 'in_progress' ? 'Manual: In Progress (click to mark Achieved)' : 'Auto (click to manually set status)'"
                  @click="cycleOverride(idx)"
                >{{ 
                  row.override === 'achieved' ? '✓ Achieved' : 
                  row.override === 'in_progress' ? '→ In Progress' : 
                  'Auto' 
                }}</button>
              </div>
            </div>
            <div v-if="editingObjectiveIndex !== idx" class="objective-edit-row">
              <div class="objective-text">{{ row.objective }}</div>
              <button class="kp-action" :disabled="kpLoading" @click="startEditObjective(idx, row.objective)">Edit</button>
            </div>
            <div v-else class="objective-edit-row">
              <input
                v-model="editingObjectiveText"
                class="kp-input"
                type="text"
                placeholder="Learning objective"
              />
              <div class="knowledge-actions">
                <button class="kp-action" :disabled="kpLoading" @click="onSaveObjective">Save</button>
                <button class="kp-action" :disabled="kpLoading" @click="cancelEditObjective">Cancel</button>
              </div>
            </div>
            <div v-if="row.evidence" class="objective-evidence">{{ row.evidence }}</div>
          </div>

          <div class="objective-add-row">
            <input
              v-model="newObjectiveText"
              class="kp-input"
              type="text"
              placeholder="Add a learning objective"
              @keyup.enter="onAddObjective"
            />
            <button class="kp-btn" :disabled="kpLoading" @click="onAddObjective">Add</button>
          </div>
        </div>

        <div class="knowledge-card">
          <button class="collapse-header" @click="isKnowledgeCollapsed = !isKnowledgeCollapsed">
            <span class="context-title">Knowledge Points</span>
            <span class="collapse-right">
              <span class="knowledge-count">{{ knowledgePoints.length }}</span>
              <span class="collapse-icon">{{ isKnowledgeCollapsed ? 'Expand' : 'Collapse' }}</span>
            </span>
          </button>

          <div v-if="!isKnowledgeCollapsed">
            <div class="knowledge-add-row">
              <input
                v-model="newPointText"
                class="kp-input"
                type="text"
                placeholder="Add a knowledge point"
                @keyup.enter="onAddKnowledgePoint"
              />
              <button class="kp-btn" :disabled="kpLoading" @click="onAddKnowledgePoint">Add</button>
            </div>

            <div v-if="knowledgePoints.length === 0" class="kp-empty">No knowledge points yet.</div>
            <div v-else class="knowledge-list">
              <div v-for="item in knowledgePoints" :key="item.id" class="knowledge-item">
                <div class="knowledge-main-row" v-if="editingPointId !== item.id">
                  <div class="knowledge-left">
                    <div class="knowledge-text">{{ item.point }}</div>
                    <div
                      class="kp-score"
                      :class="scoreClassName(getKnowledgePointScore(item).score)"
                      :title="getKnowledgePointScore(item).evidence || 'No evidence yet'"
                    >
                      Depth {{ Math.round(Number(getKnowledgePointScore(item).score || 0) * 100) }}%
                    </div>
                  </div>
                  <div class="knowledge-actions">
                    <button class="kp-action" @click="startEditPoint(item)">Edit</button>
                    <button class="kp-action danger" @click="onDeleteKnowledgePoint(item)">Delete</button>
                  </div>
                </div>

                <div v-else class="knowledge-edit-row">
                  <input
                    v-model="editingPointText"
                    class="kp-input"
                    type="text"
                    placeholder="Knowledge point"
                  />
                  <div class="knowledge-actions">
                    <button class="kp-action" :disabled="kpLoading" @click="onSaveKnowledgePoint(item)">Save</button>
                    <button class="kp-action" :disabled="kpLoading" @click="cancelEditPoint">Cancel</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject, computed, ref, watch } from 'vue';
import axios from 'axios';

const props = defineProps({
  caseData: { type: Object, default: null },
  objectiveEvaluationMap: { type: Object, default: () => ({}) },
  discussionEndMap: { type: Object, default: () => ({}) }
});

const {
  sessionId,
  activeQuestionInfo,
  knowledgeCoverageByQuestion,
  selectedNodeLeafId,
  activeMessageId,
  forceResume,
} = inject('pblSocket', {});

const knowledgePoints = ref([]);
const kpLoading = ref(false);
const newPointText = ref('');
const editingPointId = ref('');
const editingPointText = ref('');
const newObjectiveText = ref('');
const editingObjectiveIndex = ref(-1);
const editingObjectiveText = ref('');
const isKnowledgeCollapsed = ref(true);

const getCaseName = () => String(props.caseData?.case_title || '').trim();

const syncKnowledgePointsToCaseData = (points) => {
  if (!props.caseData || !hasActiveQuestion.value) return;
  const sIdx = activeQuestionInfo.value.sceneIndex;
  const qIdx = activeQuestionInfo.value.questionIndex;
  const scene = props.caseData?.scenes?.[sIdx];
  if (!scene) return;

  if (!Array.isArray(scene.trigger_question_learning_objectives)) {
    scene.trigger_question_learning_objectives = [];
  }
  while (scene.trigger_question_learning_objectives.length <= qIdx) {
    scene.trigger_question_learning_objectives.push({ trigger_question: '', learning_objectives: [], knowledge_points: [] });
  }
  if (!scene.trigger_question_learning_objectives[qIdx] || typeof scene.trigger_question_learning_objectives[qIdx] !== 'object') {
    scene.trigger_question_learning_objectives[qIdx] = { trigger_question: '', learning_objectives: [], knowledge_points: [] };
  }
  scene.trigger_question_learning_objectives[qIdx].knowledge_points = points;

  if (!Array.isArray(scene.trigger_questions)) {
    scene.trigger_questions = [];
  }
  if (scene.trigger_questions[qIdx] && typeof scene.trigger_questions[qIdx] === 'object') {
    scene.trigger_questions[qIdx].knowledge_points = points;
  }
};

const fetchKnowledgePoints = async () => {
  if (!hasActiveQuestion.value) {
    knowledgePoints.value = [];
    return;
  }
  const caseName = getCaseName();
  if (!caseName) {
    knowledgePoints.value = [];
    return;
  }

  kpLoading.value = true;
  try {
    const resp = await axios.get('http://127.0.0.1:8000/api/question-knowledge-points', {
      params: {
        case_name: caseName,
        scene_index: activeQuestionInfo.value.sceneIndex,
        question_index: activeQuestionInfo.value.questionIndex
      }
    });
    const rows = Array.isArray(resp?.data?.knowledge_points) ? resp.data.knowledge_points : [];
    knowledgePoints.value = rows;
    syncKnowledgePointsToCaseData(rows);
  } catch (err) {
    console.error('Failed to fetch knowledge points:', err);
    knowledgePoints.value = [];
  } finally {
    kpLoading.value = false;
  }
};

const onAddKnowledgePoint = async () => {
  const text = String(newPointText.value || '').trim();
  if (!text || kpLoading.value || !hasActiveQuestion.value) return;
  kpLoading.value = true;
  try {
    const resp = await axios.post('http://127.0.0.1:8000/api/question-knowledge-points/add', {
      caseName: getCaseName(),
      sceneIndex: activeQuestionInfo.value.sceneIndex,
      questionIndex: activeQuestionInfo.value.questionIndex,
      point: text,
      explanation: ''
    });
    const rows = Array.isArray(resp?.data?.knowledge_points) ? resp.data.knowledge_points : [];
    knowledgePoints.value = rows;
    syncKnowledgePointsToCaseData(rows);
    newPointText.value = '';
  } catch (err) {
    console.error('Failed to add knowledge point:', err);
    alert(`Failed to add knowledge point: ${err?.response?.data?.detail || err.message}`);
  } finally {
    kpLoading.value = false;
  }
};

const startEditPoint = (item) => {
  editingPointId.value = String(item?.id || '');
  editingPointText.value = String(item?.point || '');
};

const cancelEditPoint = () => {
  editingPointId.value = '';
  editingPointText.value = '';
};

const onSaveKnowledgePoint = async (item) => {
  const text = String(editingPointText.value || '').trim();
  if (!text || kpLoading.value || !item?.id) return;
  kpLoading.value = true;
  try {
    const resp = await axios.post('http://127.0.0.1:8000/api/question-knowledge-points/update', {
      caseName: getCaseName(),
      sceneIndex: activeQuestionInfo.value.sceneIndex,
      questionIndex: activeQuestionInfo.value.questionIndex,
      pointId: item.id,
      point: text,
      explanation: String(item?.explanation || '')
    });
    const rows = Array.isArray(resp?.data?.knowledge_points) ? resp.data.knowledge_points : [];
    knowledgePoints.value = rows;
    syncKnowledgePointsToCaseData(rows);
    cancelEditPoint();
  } catch (err) {
    console.error('Failed to update knowledge point:', err);
    alert(`Failed to update knowledge point: ${err?.response?.data?.detail || err.message}`);
  } finally {
    kpLoading.value = false;
  }
};

const onDeleteKnowledgePoint = async (item) => {
  if (!item?.id || kpLoading.value) return;
  kpLoading.value = true;
  try {
    const resp = await axios.post('http://127.0.0.1:8000/api/question-knowledge-points/delete', {
      caseName: getCaseName(),
      sceneIndex: activeQuestionInfo.value.sceneIndex,
      questionIndex: activeQuestionInfo.value.questionIndex,
      pointId: item.id
    });
    const rows = Array.isArray(resp?.data?.knowledge_points) ? resp.data.knowledge_points : [];
    knowledgePoints.value = rows;
    syncKnowledgePointsToCaseData(rows);
    if (editingPointId.value === item.id) {
      cancelEditPoint();
    }
  } catch (err) {
    console.error('Failed to delete knowledge point:', err);
    alert(`Failed to delete knowledge point: ${err?.response?.data?.detail || err.message}`);
  } finally {
    kpLoading.value = false;
  }
};

const getObjectiveListRef = () => {
  const scene = currentScene.value;
  if (!scene) return null;
  const qIdx = activeQuestionInfo.value.questionIndex;
  if (!Array.isArray(scene.trigger_question_learning_objectives)) {
    scene.trigger_question_learning_objectives = [];
  }
  while (scene.trigger_question_learning_objectives.length <= qIdx) {
    scene.trigger_question_learning_objectives.push({ trigger_question: '', learning_objectives: [], knowledge_points: [] });
  }
  const row = scene.trigger_question_learning_objectives[qIdx];
  if (!row || typeof row !== 'object') {
    scene.trigger_question_learning_objectives[qIdx] = { trigger_question: '', learning_objectives: [], knowledge_points: [] };
  }
  if (!Array.isArray(scene.trigger_question_learning_objectives[qIdx].learning_objectives)) {
    scene.trigger_question_learning_objectives[qIdx].learning_objectives = [];
  }
  return scene.trigger_question_learning_objectives[qIdx].learning_objectives;
};

const onAddObjective = async () => {
  const text = String(newObjectiveText.value || '').trim();
  if (!text || kpLoading.value || !hasActiveQuestion.value) return;
  kpLoading.value = true;
  try {
    await axios.post('http://127.0.0.1:8000/api/add-objective', {
      caseName: getCaseName(),
      sceneIndex: activeQuestionInfo.value.sceneIndex,
      questionIndex: activeQuestionInfo.value.questionIndex,
      objectiveText: text
    });
    const listRef = getObjectiveListRef();
    if (listRef && !listRef.includes(text)) {
      listRef.push(text);
    }
    newObjectiveText.value = '';
  } catch (err) {
    console.error('Failed to add objective:', err);
    alert(`Failed to add objective: ${err?.response?.data?.detail || err.message}`);
  } finally {
    kpLoading.value = false;
  }
};

const startEditObjective = (idx, text) => {
  editingObjectiveIndex.value = idx;
  editingObjectiveText.value = String(text || '');
};

const cancelEditObjective = () => {
  editingObjectiveIndex.value = -1;
  editingObjectiveText.value = '';
};

// --- Manual override for objective achievement ---
// key: "sceneIdx_questionIdx_objIdx" → true | false | null (null = auto)
const objectiveOverrides = ref({});
const objectiveOverrideTouchedAt = ref({});

const cycleOverride = async (idx) => {
  console.log('[ViewE] cycleOverride clicked for index:', idx);
  if (!hasActiveQuestion.value) {
    console.warn('[ViewE] No active question, skipping override');
    return;
  }
  const key = getOverrideKey(idx);
  if (!key) return;
  
  // Get current state from row data to capture both Auto and Manual states
  const row = objectiveRows.value[idx];
  if (!row) {
    console.error('[ViewE] Row not found for index:', idx);
    return;
  }

  const currentManual = objectiveOverrides.value[key] ?? null;
  
  let next;
  // 简化逻辑：只在 'achieved' 和 'in_progress' 之间切换
  // 如果当前是 Auto，根据当前视觉状态切换
  if (currentManual === null) {
    next = (row.achieved) ? 'in_progress' : 'achieved';
  } else {
    next = (currentManual === 'achieved') ? 'in_progress' : 'achieved';
  }

  console.log(`[ViewE] Transitioning override for ${key}: ${currentManual} -> ${next}`);

  // Immediate UI update
  objectiveOverrides.value = { ...objectiveOverrides.value, [key]: next };
  objectiveOverrideTouchedAt.value = { ...objectiveOverrideTouchedAt.value, [key]: Date.now() };

  try {
    const sIdx = Number(activeQuestionInfo?.sceneIndex ?? 0);
    const qIdx = Number(activeQuestionInfo?.questionIndex ?? 0);

    const payload = {
      caseName: getCaseName(),
      sceneIndex: sIdx,
      questionIndex: qIdx,
      objectiveIndex: idx,
      override: next
      // 删除了后端不接受的 session_id，并确保索引为数字
    };
    console.log('[ViewE] Sending override payload to backend:', payload);
    const resp = await axios.post('http://127.0.0.1:8000/api/override-objective', payload);
    console.log('[ViewE] cycleOverride API response:', resp.data);

    // Sync back to caseData so the watcher round-trip stays correct
    const scene = props.caseData?.scenes?.[sIdx];
    const objRows = scene?.trigger_question_learning_objectives;
    const targetRow = Array.isArray(objRows) ? objRows[qIdx] : null;

    if (targetRow) {
      if (!targetRow.objective_overrides || typeof targetRow.objective_overrides !== 'object') {
        targetRow.objective_overrides = {};
      }
      const objText = Array.isArray(targetRow.learning_objectives) ? targetRow.learning_objectives[idx] : null;
      if (objText != null) {
        if (next === null) delete targetRow.objective_overrides[String(objText)];
        else targetRow.objective_overrides[String(objText)] = next;
      }
    }

    // 【新增】如果标记为achieved，检查是否所有目标都已achieved
    if (next === 'achieved') {
      const allRows = objectiveRows.value;
      const allAchieved = allRows.every(r => r.achieved === true);
      if (allAchieved) {
        console.log('[ViewE] All objectives achieved by manual override');
        // 尝试调用 forceResume 触发后端路由（因为后端现在会在路由时检查状态）
        if (typeof forceResume === 'function') {
          console.log('[ViewE] Triggering forceResume to end discussion.');
          forceResume();
        }
      }
    }

    // 如果标记为 'in_progress'，且讨论曾被自动结束，则恢复讨论（但要防止快速重复调用）
    if (next === 'in_progress') {
      const sIdx = activeQuestionInfo?.sceneIndex;
      const qIdx = activeQuestionInfo?.questionIndex;
      const qKey = `${sIdx}_${qIdx}`;
      const endEntry = props.discussionEndMap?.[qKey];
      // 只在讨论因为达成目标而结束时才恢复，避免频繁的forceResume调用
      if (endEntry?.reason === 'learning_objectives_achieved') {
        console.log('[ViewE] Goal marked In Progress; queuing discussion resume...');
        // 确保使用注入的 forceResume
        if (typeof forceResume === 'function') {
          forceResume();
        }
      }
    }
  } catch (err) {
    console.error('Failed to save objective override:', err);
    // Revert on failure
    objectiveOverrides.value = { ...objectiveOverrides.value, [key]: currentManual };
    objectiveOverrideTouchedAt.value = { ...objectiveOverrideTouchedAt.value, [key]: Date.now() };
  }
};

const onSaveObjective = async () => {
  const idx = Number(editingObjectiveIndex.value);
  const text = String(editingObjectiveText.value || '').trim();
  if (idx < 0 || !text || kpLoading.value || !hasActiveQuestion.value) return;
  kpLoading.value = true;
  try {
    await axios.post('http://127.0.0.1:8000/api/update-objective', {
      caseName: getCaseName(),
      sceneIndex: activeQuestionInfo.value.sceneIndex,
      questionIndex: activeQuestionInfo.value.questionIndex,
      objectiveIndex: idx,
      objectiveText: text
    });
    const listRef = getObjectiveListRef();
    if (listRef && idx < listRef.length) {
      listRef[idx] = text;
    }
    cancelEditObjective();
  } catch (err) {
    console.error('Failed to update objective:', err);
    alert(`Failed to update objective: ${err?.response?.data?.detail || err.message}`);
  } finally {
    kpLoading.value = false;
  }
};

const normalizeText = (text) => {
  return String(text || '')
    .trim()
    .replace(/[\u3000\s]+/g, ' ')
    .replace(/[；;。！？!?,，]/g, '')
    .toLowerCase();
};

const lastValidCoverage = ref(null);

const activeCoveragePayload = computed(() => {
  const sceneIndex = activeQuestionInfo?.value?.sceneIndex;
  const questionIndex = activeQuestionInfo?.value?.questionIndex;
  if (!Number.isFinite(sceneIndex) || !Number.isFinite(questionIndex)) return lastValidCoverage.value;

  const key = `${sceneIndex}_${questionIndex}`;
  const byLeaf = knowledgeCoverageByQuestion?.value?.[key] || {};
  
  // 1. 优先尝试使用选中的节点或当前活跃消息的 ID
  const preferredLeafId = selectedNodeLeafId?.value || activeMessageId?.value;
  let result = null;
  if (preferredLeafId && byLeaf[preferredLeafId]) {
    result = byLeaf[preferredLeafId];
  } else {
    // 2. 如果当前活跃 ID 还没结果，或者正在由后端异步评估中，
    // 我们从该场景的所有历史评估中找寻“最新”且“非空”的作为占位。
    const candidates = Object.values(byLeaf || {})
      .filter(Boolean)
      .filter(c => Array.isArray(c.point_scores) && c.point_scores.length > 0);
    
    if (candidates.length) {
      // 按时间戳降序排列，取最新的一个有效评估结果
      candidates.sort((a, b) => Number(b?.updatedAt || 0) - Number(a?.updatedAt || 0));
      result = candidates[0] || null;
    }
  }

  // 【新增】Stale-While-Revalidating 模式：如果新计算的结果为空，则保留上一个非空状态
  if (result && Array.isArray(result.point_scores) && result.point_scores.length > 0) {
    lastValidCoverage.value = result;
    return result;
  }
  
  return lastValidCoverage.value;
});

const knowledgePointScoreMap = computed(() => {
  const map = new Map();
  const rows = activeCoveragePayload.value?.point_scores;
  if (!Array.isArray(rows)) return map;

  rows.forEach((row) => {
    const id = String(row?.id || '').trim();
    const point = String(row?.point || '').trim();
    const score = Number(row?.coverage_score || 0);
    const evidence = String(row?.evidence || '').trim();

    if (id) map.set(`id:${id}`, { score, evidence });
    if (point) map.set(`point:${normalizeText(point)}`, { score, evidence });
  });
  return map;
});

const getKnowledgePointScore = (item) => {
  const byId = knowledgePointScoreMap.value.get(`id:${String(item?.id || '').trim()}`);
  if (byId) return byId;
  return knowledgePointScoreMap.value.get(`point:${normalizeText(item?.point || '')}`) || { score: 0, evidence: '' };
};

const scoreClassName = (score) => {
  const v = Number(score || 0);
  if (v >= 0.99) return 'kp-score-full';
  if (v >= 0.59) return 'kp-score-mid';
  if (v >= 0.29) return 'kp-score-low';
  return 'kp-score-none';
};

const hasActiveQuestion = computed(() => {
  const info = activeQuestionInfo?.value;
  return !!info && info.sceneIndex >= 0 && info.questionIndex >= 0;
});

const getOverrideKey = (idx) => {
  if (!hasActiveQuestion.value) return null;
  return `${activeQuestionInfo.value.sceneIndex}_${activeQuestionInfo.value.questionIndex}_${idx}`;
};

// 【修改】刷新页面时清空所有override状态，不加载缓存
// 这样刷新就是干净的新开始，所有目标回到自动评估模式
watch(
  () => [activeQuestionInfo?.value?.sceneIndex, activeQuestionInfo?.value?.questionIndex],
  () => {
    if (!hasActiveQuestion.value) return;
    const sIdx = activeQuestionInfo.value.sceneIndex;
    const qIdx = activeQuestionInfo.value.questionIndex;

    // Reset only when the question actually CHANGES, not on every caseData update
    const next = {};
    const objectives = Array.isArray(
      props.caseData?.scenes?.[sIdx]?.trigger_question_learning_objectives?.[qIdx]?.learning_objectives
    ) ? props.caseData.scenes[sIdx].trigger_question_learning_objectives[qIdx].learning_objectives : [];
    
    objectives.forEach((objText, idx) => {
      const key = `${sIdx}_${qIdx}_${idx}`;
      next[key] = null;
    });
    console.debug(`[ViewE] Question changed: Resetting local overrides for ${sIdx}_${qIdx}`);
    objectiveOverrides.value = next;
  },
  { immediate: true }
);

const latestObjectiveEvalUpdatedAt = computed(() => {
  if (!hasActiveQuestion.value) return 0;
  const key = `${activeQuestionInfo.value.sceneIndex}_${activeQuestionInfo.value.questionIndex}`;
  return Number(props.objectiveEvaluationMap?.[key]?.updatedAt || 0);
});

watch(latestObjectiveEvalUpdatedAt, async (newTs) => {
  if (!hasActiveQuestion.value || !newTs) return;
  const prefix = `${activeQuestionInfo.value.sceneIndex}_${activeQuestionInfo.value.questionIndex}_`;
  
  // Only target overrides that were boolean (old logic) OR specific string values we want to auto-clear
  // However, the user wants manual overrides to PERSIST until they click again.
  // The current logic clears ANY override that was touched before the latest evaluation.
  // We should remove this auto-clearing logic to allow manual states to stick.
  /*
  const targets = Object.entries(objectiveOverrides.value)
    ...
  */
});

watch(() => [
  hasActiveQuestion.value,
  activeQuestionInfo?.value?.sceneIndex,
  activeQuestionInfo?.value?.questionIndex,
  props.caseData?.case_title
], () => {
  fetchKnowledgePoints();
}, { immediate: true });

const currentScene = computed(() => {
  if (!props.caseData || !hasActiveQuestion.value) return null;
  return props.caseData?.scenes?.[activeQuestionInfo.value.sceneIndex] || null;
});

const currentTriggerQuestion = computed(() => {
  const scene = currentScene.value;
  if (!scene) return '';
  return scene?.trigger_questions?.[activeQuestionInfo.value.questionIndex]?.question || '';
});

const configuredObjectives = computed(() => {
  const scene = currentScene.value;
  if (!scene) return [];
  const rows = scene.trigger_question_learning_objectives || [];
  const qIdx = activeQuestionInfo.value.questionIndex;

  const currentQNorm = normalizeText(currentTriggerQuestion.value);
  const byQuestion = rows.find((r) => normalizeText(r?.trigger_question) === currentQNorm);
  if (byQuestion && Array.isArray(byQuestion.learning_objectives)) {
    return byQuestion.learning_objectives.filter(Boolean);
  }

  const rowByIndex = rows[qIdx];
  if (rowByIndex && Array.isArray(rowByIndex.learning_objectives)) {
    return rowByIndex.learning_objectives.filter(Boolean);
  }

  return [];
});

const getEvaluationRowsForActiveQuestion = () => {
  if (!hasActiveQuestion.value) return [];
  const key = `${activeQuestionInfo.value.sceneIndex}_${activeQuestionInfo.value.questionIndex}`;

  const live = props.objectiveEvaluationMap?.[key] || {};
  const fromLive = Array.isArray(live.objectiveEvaluations)
    ? live.objectiveEvaluations
    : (Array.isArray(live.objective_evaluations) ? live.objective_evaluations : []);
  if (fromLive.length) return fromLive;

  const ended = props.discussionEndMap?.[key] || {};
  const fromEnd = Array.isArray(ended.objectiveEvaluations)
    ? ended.objectiveEvaluations
    : (Array.isArray(ended.objective_evaluations) ? ended.objective_evaluations : []);
  if (fromEnd.length) return fromEnd;

  // Fallback: if active key has no data, use latest available update across all keys.
  const pickRows = (entry) => {
    if (!entry || typeof entry !== 'object') return [];
    if (Array.isArray(entry.objectiveEvaluations)) return entry.objectiveEvaluations;
    if (Array.isArray(entry.objective_evaluations)) return entry.objective_evaluations;
    return [];
  };

  const candidates = [
    ...Object.entries(props.objectiveEvaluationMap || {}).map(([k, v]) => ({
      key: k,
      updatedAt: Number(v?.updatedAt || 0),
      rows: pickRows(v)
    })),
    ...Object.entries(props.discussionEndMap || {}).map(([k, v]) => ({
      key: k,
      updatedAt: Number(v?.updatedAt || 0),
      rows: pickRows(v)
    }))
  ].filter((item) => item.rows.length > 0);

  if (!candidates.length) return [];
  candidates.sort((a, b) => b.updatedAt - a.updatedAt);
  return candidates[0].rows;
};

const hasSummarizationStarted = computed(() => {
  if (!hasActiveQuestion.value) return false;
  const key = `${activeQuestionInfo.value.sceneIndex}_${activeQuestionInfo.value.questionIndex}`;
  const rounds = props.objectiveEvaluationMap?.[key]?.rounds || [];
  if (Array.isArray(rounds) && rounds.length > 0) return true;
  return getEvaluationRowsForActiveQuestion().length > 0;
});

const objectiveRows = computed(() => {
  if (!hasActiveQuestion.value) return [];
  const wsRows = getEvaluationRowsForActiveQuestion();
  const resultMap = new Map(
    wsRows.map((item) => [normalizeText(item.objective), item])
  );

  const base = configuredObjectives.value;
  if (!base.length) {
    return wsRows.map((item) => {
      const achieved = Boolean(item?.achieved);
      const evidence = String(item?.evidence || '').trim();
      const rawStatus = String(item?.status || '').trim().toLowerCase();
      const status = ['achieved', 'in_progress', 'not_discussed'].includes(rawStatus)
        ? rawStatus
        : (achieved ? 'achieved' : (evidence ? 'in_progress' : 'not_discussed'));
      const pendingLabel = hasSummarizationStarted.value ? 'Not Discussed Yet' : 'Not Discussed Yet';
      return {
        objective: String(item?.objective || 'Unnamed objective').trim(),
        achieved,
        statusLabel: status === 'achieved' ? 'Achieved' : (status === 'in_progress' ? 'In Discussion' : pendingLabel),
        statusClass: status === 'achieved' ? 'achieved' : (status === 'in_progress' ? 'in-progress' : 'pending'),
        evidence
      };
    });
  }

  return base.map((obj, idx) => {
    const objectiveKey = String(obj || '').trim();
    // LLM occasionally paraphrases objective text; fallback to index keeps UI aligned.
    const byText = resultMap.get(normalizeText(objectiveKey));
    const byIndex = wsRows[idx];
    const hit = byText || byIndex || null;
    const evidence = String(hit?.evidence || '').trim();
    const llmAchieved = Boolean(hit?.achieved);
    const rawStatus = String(hit?.status || '').trim().toLowerCase();

    // 【修改】支持新的override状态值：'in_progress' 和 'achieved'
    const overrideKey = `${activeQuestionInfo.value.sceneIndex}_${activeQuestionInfo.value.questionIndex}_${idx}`;
    const override = objectiveOverrides.value[overrideKey] ?? null;
    
    // 根据override决定最终状态
    let normalizedStatus;
    let achieved; // 用于兼容旧逻辑的boolean，表示是否在系统评估中achieved
    
    if (override === 'achieved') {
      // 手动设置为achieved
      normalizedStatus = 'achieved';
      achieved = true;
    } else if (override === 'in_progress') {
      // 手动设置为in_progress
      normalizedStatus = 'in_progress';
      achieved = false;  // 虽然手动标记为进行中，但achieved仍然是系统评估的结果
    } else if (override === null) {
      // 自动评估
      achieved = llmAchieved;
      normalizedStatus = (['achieved', 'in_progress', 'not_discussed'].includes(rawStatus)
        ? rawStatus
        : (llmAchieved ? 'achieved' : (evidence ? 'in_progress' : 'not_discussed')));
    }

    const statusLabelMap = {
      achieved: 'Achieved',
      in_progress: 'In Discussion',
      not_discussed: hasSummarizationStarted.value ? 'Not Discussed Yet' : 'Not Discussed Yet'
    };

    const statusClassMap = {
      achieved: 'achieved',
      in_progress: 'in-progress',
      not_discussed: 'pending'
    };
    
    // 【新增】UI颜色规则与状态显示
    const isManualOverride = override !== null;
    const statusClass = statusClassMap[normalizedStatus];

    return {
      objective: objectiveKey,
      achieved,
      override,
      statusLabel: statusLabelMap[normalizedStatus],
      statusClass: statusClassMap[normalizedStatus],
      evidence
    };
  });
});

const achievedCount = computed(() => objectiveRows.value.filter((row) => row.achieved).length);

const progressPercent = computed(() => {
  if (!objectiveRows.value.length) return 0;
  return Math.round((achievedCount.value / objectiveRows.value.length) * 100);
});
</script>

<style scoped>
.view-e-header {
  background: #000000;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.view-title {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
}

.objective-scroll::-webkit-scrollbar {
  width: 4px;
}

.objective-scroll::-webkit-scrollbar-thumb {
  background: rgba(107, 114, 128, 0.35);
  border-radius: 10px;
}

.context-card,
.progress-card,
.knowledge-card {
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  padding: 10px 12px;
  margin-bottom: 10px;
}

.knowledge-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.collapse-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: transparent;
  border: none;
  padding: 0;
  margin-bottom: 8px;
  cursor: pointer;
}

.collapse-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.collapse-icon {
  font-size: 11px;
  color: #6b7280;
  font-weight: 700;
}

.knowledge-count {
  font-size: 11px;
  font-weight: 700;
  color: #1f2937;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 9999px;
  padding: 1px 8px;
}

.knowledge-add-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.knowledge-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.knowledge-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
  padding: 8px;
}

.knowledge-main-row,
.knowledge-edit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.knowledge-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.knowledge-text {
  font-size: 12px;
  color: #111827;
  line-height: 1.35;
  word-break: break-word;
}

.kp-score {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 9999px;
  border: 1px solid transparent;
  white-space: nowrap;
}

.kp-score-none {
  color: #6b7280;
  background: #f3f4f6;
  border-color: #d1d5db;
}

.kp-score-low {
  color: #9a3412;
  background: #ffedd5;
  border-color: #fdba74;
}

.kp-score-mid {
  color: #1d4ed8;
  background: #eff6ff;
  border-color: #93c5fd;
}

.kp-score-full {
  color: #166534;
  background: #ecfdf5;
  border-color: #86efac;
}

.knowledge-actions {
  display: flex;
  gap: 6px;
}

.kp-input {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 12px;
  color: #111827;
  background: #ffffff;
}

.kp-btn,
.kp-action {
  border: 1px solid #9ca3af;
  background: #ffffff;
  color: #111827;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  padding: 5px 8px;
  cursor: pointer;
}

.kp-action.danger {
  border-color: #fca5a5;
  color: #b91c1c;
}

.kp-empty {
  font-size: 12px;
  color: #6b7280;
  padding: 6px 0;
}

.context-title,
.progress-label {
  font-size: 11px;
  font-weight: 700;
  color: #4b5563;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.context-text {
  margin-top: 4px;
  font-size: 13px;
  color: #111827;
  line-height: 1.4;
}

.progress-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.progress-value {
  font-size: 12px;
  font-weight: 700;
  color: #111827;
}

.progress-track {
  margin-top: 8px;
  width: 100%;
  height: 8px;
  background: #e5e7eb;
  border-radius: 9999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #16a34a 0%, #22c55e 100%);
}

.objective-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.objective-item {
  border-radius: 12px;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  background: #ffffff;
}

.objective-item.achieved {
  border-color: #86efac;
  background: #f0fdf4;
}

.objective-item.pending {
  border-color: #fca5a5;
  background: #fff1f2;
}

.objective-item.in-progress {
  border-color: #93c5fd;
  background: #eff6ff;
}

.objective-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.objective-top-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.override-btn {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 9999px;
  border: 1px solid transparent;
  cursor: pointer;
  white-space: nowrap;
  line-height: 1.4;
}

.override-auto {
  color: #6b7280;
  background: #f3f4f6;
  border-color: #d1d5db;
}

.override-achieved {
  color: #166534;
  background: #dcfce7;
  border-color: #86efac;
}

.override-in-progress {
  color: #1e40af;
  background: #dbeafe;
  border-color: #93c5fd;
}

.override-not {
  color: #991b1b;
  background: #fee2e2;
  border-color: #fca5a5;
}

.objective-index {
  font-size: 11px;
  font-weight: 700;
  color: #374151;
}

.objective-status {
  font-size: 11px;
  font-weight: 700;
}

.objective-item.achieved .objective-status {
  color: #15803d;
}

.objective-item.pending .objective-status {
  color: #b91c1c;
}

.objective-item.in-progress .objective-status {
  color: #1d4ed8;
}

.objective-text {
  font-size: 13px;
  color: #111827;
  line-height: 1.4;
}

.objective-edit-row,
.objective-add-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.objective-add-row {
  margin-top: 8px;
}

.objective-evidence {
  margin-top: 6px;
  font-size: 12px;
  color: #4b5563;
  line-height: 1.35;
}

.empty-state {
  margin-top: 12px;
  border: 1px dashed #9ca3af;
  border-radius: 12px;
  padding: 16px;
  text-align: center;
  color: #6b7280;
  background: #f9fafb;
  font-size: 13px;
}
</style>