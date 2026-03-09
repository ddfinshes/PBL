<template>
  <div class="view-e-container h-full flex flex-col bg-[#ECECEC] rounded-xl border border-gray-300 overflow-hidden">
    <div class="view-e-header">
      <h2 class="view-title">Learning Objectives</h2>
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
              <div class="objective-status">{{ row.statusLabel }}</div>
            </div>
            <div class="objective-text">{{ row.objective }}</div>
            <div v-if="row.evidence" class="objective-evidence">{{ row.evidence }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject, computed } from 'vue';

const props = defineProps({
  caseData: { type: Object, default: null },
  objectiveEvaluationMap: { type: Object, default: () => ({}) },
  discussionEndMap: { type: Object, default: () => ({}) }
});

const { activeQuestionInfo } = inject('pblSocket', {});

const normalizeText = (text) => {
  return String(text || '')
    .trim()
    .replace(/[\u3000\s]+/g, ' ')
    .replace(/[；;。！？!?,，]/g, '')
    .toLowerCase();
};

const hasActiveQuestion = computed(() => {
  const info = activeQuestionInfo?.value;
  return !!info && info.sceneIndex >= 0 && info.questionIndex >= 0;
});

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
      const pendingLabel = hasSummarizationStarted.value ? '总结中' : 'Not Discussed Yet';
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
    const achieved = Boolean(hit?.achieved);
    const rawStatus = String(hit?.status || '').trim().toLowerCase();
    const normalizedStatus = ['achieved', 'in_progress', 'not_discussed'].includes(rawStatus)
      ? rawStatus
      : (achieved ? 'achieved' : (evidence ? 'in_progress' : 'not_discussed'));

    const statusLabelMap = {
      achieved: 'Achieved',
      in_progress: 'In Discussion',
      not_discussed: hasSummarizationStarted.value ? '总结中' : 'Not Discussed Yet'
    };

    const statusClassMap = {
      achieved: 'achieved',
      in_progress: 'in-progress',
      not_discussed: 'pending'
    };

    return {
      objective: objectiveKey,
      achieved,
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
.progress-card {
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  padding: 10px 12px;
  margin-bottom: 10px;
}

.summary-card {
  background: #f8fafc;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  padding: 10px 12px;
  margin-bottom: 10px;
}

.summary-title {
  font-size: 12px;
  font-weight: 700;
  color: #1e3a8a;
}

.summary-subtitle {
  margin-top: 2px;
  font-size: 11px;
  color: #334155;
}

.summary-round-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.summary-round {
  background: #ffffff;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  padding: 8px;
}

.summary-round-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: #1f2937;
  font-weight: 600;
}

.summary-round-track {
  margin-top: 6px;
  width: 100%;
  height: 6px;
  border-radius: 9999px;
  background: #e2e8f0;
  overflow: hidden;
}

.summary-round-fill {
  height: 100%;
  background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%);
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