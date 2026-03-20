<template>
	<div class="view-g-container h-full flex flex-col bg-[#ECECEC] rounded-xl border border-gray-300 overflow-hidden">
		<div class="view-g-header">
			<h2 class="view-title">Agent Knowledge Graphs</h2>
		</div>

		<div class="flex-1 overflow-y-auto p-3 json-scroll">
			<div v-if="!hasActiveQuestion" class="empty-state">
				Select a trigger question to inspect per-agent state.
			</div>

			<div v-else-if="!hasAnyPayload" class="empty-state">
				Waiting for `agent_state_snapshot` payload.
			</div>

			<div v-else class="graphs-grid">
				<div
					v-for="agent in agentGraphCards"
					:key="agent.agent_id"
					class="graph-card"
				>
					<KnowledgeGraphMini
						:title="agent.display_name"
						:accent-color="agent.color"
						:graph="agent.knowledge_graph"
						:mastered-points="agent.mastered_points"
						:agent-names="allAgentNames"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject } from 'vue';
import KnowledgeGraphMini from '../components/KnowledgeGraphMini.vue';

defineProps({
	objectiveEvaluationMap: { type: Object, default: () => ({}) },
	discussionEndMap: { type: Object, default: () => ({}) }
});

const { activeQuestionInfo, agentStateByQuestion, getAgentColor, getAgentName, personas } = inject('pblSocket', {});

const hasActiveQuestion = computed(() => {
	const info = activeQuestionInfo?.value;
	return !!info && info.sceneIndex >= 0 && info.questionIndex >= 0;
});

const activeKey = computed(() => {
	if (!hasActiveQuestion.value) return null;
	return `${activeQuestionInfo.value.sceneIndex}_${activeQuestionInfo.value.questionIndex}`;
});

// 仅用于展示每个 agent 的 knowledge_graph 与 mastered_points
const agentStatePayload = computed(() => {
	if (!activeKey.value) return null;
	const state = agentStateByQuestion?.value?.[activeKey.value];
	if (!state || typeof state !== 'object') return null;

	const knowledgeState = (state.knowledge_state && typeof state.knowledge_state === 'object')
		? state.knowledge_state
		: {};
	// 获取所有有效的 agent IDs：只保留那些在 personas 中存在的 ID
	const personasObj = (typeof personas?.value === 'object') ? personas.value : {};
	const validAgentIds = Object.keys(personasObj);
	const agentIds = Object.keys(knowledgeState)
		.filter((k) => k !== '__shared_domains__' && validAgentIds.includes(k))
		.sort();

	return {
		scene_index: activeQuestionInfo.value.sceneIndex,
		question_index: activeQuestionInfo.value.questionIndex,
		agents: agentIds.map((agentId) => {
			const agentKnowledge = knowledgeState?.[agentId] || {};
			const masteredPoints = Array.isArray(agentKnowledge.mastered_points)
				? agentKnowledge.mastered_points
				: [];
			const knowledgeGraph = (agentKnowledge.knowledge_graph && typeof agentKnowledge.knowledge_graph === 'object')
				? agentKnowledge.knowledge_graph
				: { nodes: {}, edges: [] };

			return {
				agent_id: agentId,
				mastered_points: masteredPoints,
				knowledge_graph: knowledgeGraph
			};
		})
	};
});

const agentGraphCards = computed(() => {
	const payload = agentStatePayload.value;
	if (!payload || !Array.isArray(payload.agents)) return [];
	return payload.agents.map((a) => {
		const agentId = String(a.agent_id || '').trim();
		const displayName = typeof getAgentName === 'function' ? getAgentName(agentId) : (agentId || 'Agent');
		const color = typeof getAgentColor === 'function' ? getAgentColor(agentId) : '#8095CA';
		return {
			agent_id: agentId,
			display_name: displayName,
			color,
			mastered_points: Array.isArray(a.mastered_points) ? a.mastered_points : [],
			knowledge_graph: (a.knowledge_graph && typeof a.knowledge_graph === 'object') ? a.knowledge_graph : { nodes: {}, edges: [] }
		};
	});
});

const allAgentNames = computed(() => {
	return agentGraphCards.value.map((a) => a.display_name);
});

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

.graphs-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 10px;
	align-content: start;
}

.graph-card {
	min-height: 220px;
}

@media (max-width: 1600px) {
	.graphs-grid {
		grid-template-columns: 1fr;
	}
	.graph-card {
		min-height: 240px;
	}
}
</style>
