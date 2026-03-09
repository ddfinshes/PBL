<template>
	<div class="view-g-container h-full flex flex-col bg-[#ECECEC] rounded-xl border border-gray-300 overflow-hidden">
		<div class="view-g-header">
			<h2 class="view-title">Reflection</h2>
		</div>

		<div class="flex-1 overflow-y-auto p-3 json-scroll">
			<div v-if="!hasActiveQuestion" class="empty-state">
				Select a trigger question to inspect per-agent state.
			</div>

			<div v-else-if="!hasAnyPayload" class="empty-state">
				Waiting for `agent_state_snapshot` payload.
			</div>

			<div v-else class="json-sections">
				<div class="json-card" v-if="agentStatePayload">
					<div class="json-title">agent_state_snapshot</div>
					<pre class="json-code">{{ agentStatePayloadText }}</pre>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject } from 'vue';

defineProps({
	objectiveEvaluationMap: { type: Object, default: () => ({}) },
	discussionEndMap: { type: Object, default: () => ({}) }
});

const { activeQuestionInfo, agentStateByQuestion } = inject('pblSocket', {});

const hasActiveQuestion = computed(() => {
	const info = activeQuestionInfo?.value;
	return !!info && info.sceneIndex >= 0 && info.questionIndex >= 0;
});

const activeKey = computed(() => {
	if (!hasActiveQuestion.value) return null;
	return `${activeQuestionInfo.value.sceneIndex}_${activeQuestionInfo.value.questionIndex}`;
});

const agentStatePayload = computed(() => {
	if (!activeKey.value) return null;
	const state = agentStateByQuestion?.value?.[activeKey.value];
	if (!state || typeof state !== 'object') return null;

	const knowledgeState = (state.knowledge_state && typeof state.knowledge_state === 'object')
		? state.knowledge_state
		: {};
	const privateMemory = (state.private_memory && typeof state.private_memory === 'object')
		? state.private_memory
		: {};

	const knowledgeAgentIds = Object.keys(knowledgeState).filter((k) => k !== '__shared_domains__');
	const memoryAgentIds = Object.keys(privateMemory);
	const agentIds = Array.from(new Set([...knowledgeAgentIds, ...memoryAgentIds])).sort();

	return {
		scene_index: activeQuestionInfo.value.sceneIndex,
		question_index: activeQuestionInfo.value.questionIndex,
		agents: agentIds.map((agentId) => {
			const agentKnowledge = knowledgeState?.[agentId] || {};
			const masteredPoints = Array.isArray(agentKnowledge.mastered_points)
				? agentKnowledge.mastered_points
				: [];
			const memoryRows = Array.isArray(privateMemory?.[agentId]) ? privateMemory[agentId] : [];
			const internalizedMessages = memoryRows
				.filter((item) => String(item?.action || '') === 'internalize_message')
				.map((item) => String(item?.internalized_note || '').trim())
				.filter(Boolean);

			return {
				agent_id: agentId,
				mastered_points: masteredPoints,
				internalized_messages: internalizedMessages
			};
		}),
		updated_at: state.updatedAt || null,
		note: 'Contains per-agent mastered_points and internalized_messages in current restored/running branch state.'
	};
});
const agentStatePayloadText = computed(() => JSON.stringify(agentStatePayload.value, null, 2));
const hasAnyPayload = computed(() => Boolean(agentStatePayload.value));
</script>

<style scoped>
.view-g-header {
	background: #000000;
	padding: 8px 12px;
}

.view-title {
	margin: 0;
	font-size: 14px;
	font-weight: 600;
	color: #ffffff;
}

.json-scroll::-webkit-scrollbar {
	width: 4px;
}

.json-scroll::-webkit-scrollbar-thumb {
	background: rgba(107, 114, 128, 0.35);
	border-radius: 10px;
}

.json-sections {
	display: flex;
	flex-direction: column;
	gap: 10px;
}

.json-card {
	background: #ffffff;
	border: 1px solid #d1d5db;
	border-radius: 10px;
	padding: 8px;
}

.json-title {
	font-size: 11px;
	font-weight: 700;
	color: #374151;
	margin-bottom: 6px;
}

.json-code {
	margin: 0;
	font-size: 11px;
	line-height: 1.45;
	color: #111827;
	background: #f9fafb;
	border: 1px solid #e5e7eb;
	border-radius: 8px;
	padding: 8px;
	white-space: pre-wrap;
	word-break: break-word;
}

.empty-state {
	border: 1px dashed #9ca3af;
	border-radius: 10px;
	padding: 12px;
	text-align: center;
	color: #6b7280;
	background: #f9fafb;
	font-size: 12px;
}
</style>
