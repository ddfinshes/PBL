<template>
  <div class="view-d-container h-full w-full relative overflow-hidden bg-[#ECECEC] rounded-xl border border-gray-300">
    <div class="view-d-header">
      <h2 class="view-title">Topic Evolution Path</h2>
      <button 
        @click="isHighlightingFlags = !isHighlightingFlags"
        class="px-3 py-1 text-xs rounded-full border transition-all duration-300"
        :class="isHighlightingFlags ? 'bg-[#EF4444] text-white border-[#EF4444]' : 'text-gray-600 border-gray-400 hover:bg-gray-200'"
      >
        {{ isHighlightingFlags ? 'Cancel' : 'Review' }}
      </button>
    </div>
    <div ref="svgWrapper" class="w-full h-full">
      <svg ref="svgRef" class="w-full h-full"></svg>
    </div>

    <!-- Summary Modal -->
    <div v-if="showSummaryModal" class="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-8">
      <div class="bg-white border border-gray-300 rounded-2xl w-full max-w-2xl max-h-[80%] flex flex-col shadow-2xl">
        <div class="p-4 border-b border-gray-200 flex justify-between items-center">
          <h4 class="text-gray-800 font-bold">In-Depth Analysis of Instructor Intervention Points</h4>
          <button @click="showSummaryModal = false" class="text-gray-400 hover:text-white">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        
        <div class="flex-1 overflow-y-auto p-6 space-y-4">
          <div v-if="summaryLoading" class="flex flex-col items-center justify-center py-12 space-y-4">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            <p class="text-gray-600 text-sm italic">Waiting for Analysis...</p>
          </div>
          <div v-else-if="currentSummaryParts.context || currentSummaryParts.action || currentSummaryParts.consequence" class="space-y-4">
            <div class="space-y-2">
              <label class="text-xs text-blue-600 font-medium uppercase tracking-wider">Before Intervention: Discussion Status Summary</label>
              <textarea 
                v-model="currentSummaryParts.context"
                class="w-full h-24 bg-gray-50 text-gray-800 p-3 rounded-xl border border-blue-200 focus:border-blue-400 outline-none text-sm leading-relaxed"
              ></textarea>
            </div>
            
            <div class="space-y-2">
              <label class="text-xs text-[#EF4444] font-medium uppercase tracking-wider">Intervention: Instructor Action Description</label>
              <textarea 
                v-model="currentSummaryParts.action"
                class="w-full h-24 bg-gray-50 text-gray-800 p-3 rounded-xl border border-red-200 focus:border-red-400 outline-none text-sm leading-relaxed"
              ></textarea>
            </div>

            <div class="space-y-2">
              <label class="text-xs text-green-600 font-medium uppercase tracking-wider">After Intervention: Immediate Interaction Changes</label>
              <textarea 
                v-model="currentSummaryParts.consequence"
                class="w-full h-24 bg-gray-50 text-gray-800 p-3 rounded-xl border border-green-200 focus:border-green-400 outline-none text-sm leading-relaxed"
              ></textarea>
            </div>
          </div>
          <div v-else class="flex flex-col items-center justify-center py-12">
             <p class="text-gray-600 text-sm italic">Waiting for data to load...</p>
          </div>
        </div>

        <div class="p-4 border-t border-gray-200 flex justify-end gap-3">
          <button @click="showSummaryModal = false" class="px-4 py-2 text-sm text-gray-500 hover:text-gray-800">Cancel</button>
          <button 
            v-if="currentSummaryParts.context"
            @click="saveSummary" 
            class="px-6 py-2 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600 transition-colors"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject, watch, computed } from 'vue';
import * as d3 from 'd3';
import axios from 'axios';

const { 
  messages, 
  selectedTopic, 
  activeMessageId,
  activeQuestionInfo,
  selectedNodeLeafId,
  interventionSummaries,
  knowledgeCoverageByQuestion,
  getAgentColor,
  isPaused,
  switchNodeFocus
} = inject('pblSocket', {});
const sessionId = inject('sessionId');
const svgRef = ref(null);
const svgWrapper = ref(null);

// Store knowledge coverage data
const knowledgeCoverageMap = ref(new Map()); // nodeId -> { totalPoints, coveredPoints, ratio, score, details, pointScores }

// 追踪节点的前驱关系，用于累积覆盖率
const nodeAncestorMap = ref(new Map()); // nodeId -> parentNodeId

// 【修复】避免直接清空覆盖率导致UI闪烁，改为延迟清空或保留
// 当问题真的改变时，在下一次覆盖率数据到达时再进行合并
watch(activeQuestionInfo, () => {
  // 不直接清空，而是标记需要重新映射
  // remapCoverageFromQuestionCache 会自动处理新旧数据的合并
  nodeAncestorMap.value = new Map();
  
  // 【新增】当切换问题时，重置已评估的节点跟踪，这样新问题的所有节点都会重新计算覆盖率
  lastEvaluatedNodeIds.value = new Set();
  console.debug('[ViewD] activeQuestionInfo changed, reset coverage evaluation state');
}, { deep: true });

// --- 总结功能相关状态 ---
const showSummaryModal = ref(false);
const summaryLoading = ref(false);
const currentSummaryParts = ref({
  context: '',
  action: '',
  consequence: ''
});
const summaryInterventionId = ref('');
const isHighlightingFlags = ref(false);

const openSummaryModal = async (node) => {
  // 1. 优先从本地/归档缓存中获取
  const targetId = node.interventionId || node.turnsList?.[0]?.id || node.id;
  summaryInterventionId.value = targetId;

  if (interventionSummaries.value[targetId]) {
    console.log('Loading summary from archive/cache:', targetId);
    currentSummaryParts.value = interventionSummaries.value[targetId].parts;
    showSummaryModal.value = true;
    summaryLoading.value = false;
    return;
  }

  // 2. 如果没有缓存，则清空并调用后端接口
  currentSummaryParts.value = { context: '', action: '', consequence: '' };
  showSummaryModal.value = true;
  summaryLoading.value = true;
  
  try {
    const resp = await axios.post('http://127.0.0.1:8000/api/generate-intervention-summary', {
      session_id: sessionId,
      intervention_id: summaryInterventionId.value,
      scene_index: activeQuestionInfo.value.sceneIndex,
      question_index: activeQuestionInfo.value.questionIndex
    });
    if (resp.data.status === 'success' && resp.data.summary_parts) {
      currentSummaryParts.value = resp.data.summary_parts;
    }
  } catch (err) {
    console.error('Failed to generate summary:', err);
    currentSummaryParts.value = { context: '生成失败', action: '生成失败', consequence: '生成失败' };
  } finally {
    summaryLoading.value = false;
  }
};

const saveSummary = async () => {
  try {
    const summaryData = {
      parts: currentSummaryParts.value,
      timestamp: Date.now()
    };
    await axios.post('http://127.0.0.1:8000/api/save-intervention-summary', {
      session_id: sessionId,
      scene_index: activeQuestionInfo.value.sceneIndex,
      question_index: activeQuestionInfo.value.questionIndex,
      intervention_id: summaryInterventionId.value,
      summary_data: summaryData
    });
    // 更新本地缓存以便即时回显
    interventionSummaries.value[summaryInterventionId.value] = summaryData;

    alert('Save successful!');
    showSummaryModal.value = false;
  } catch (err) {
    alert('Failed to save: ' + err.message);
  }
};

// 评估知识覆盖度
const evaluateKnowledgeCoverage = async (caseInfo, discussionContent, nodeId) => {
  try {
    const response = await axios.post(
      'http://127.0.0.1:8000/api/evaluate-knowledge-coverage',
      {
        case_name: caseInfo.caseName || 'unknown',
        scene_index: caseInfo.sceneIndex || 0,
        question_index: caseInfo.questionIndex || 0,
        discussion_content: discussionContent
      }
    );

    if (response.data.status === 'success') {
      const coverageData = {
        totalPoints: Number(response.data.total_points || 0),
        coveredPoints: Array.isArray(response.data.covered_points) ? response.data.covered_points : [],
        pointScores: Array.isArray(response.data.point_scores) ? response.data.point_scores : [],
        score: Number(response.data.coverage_score || 0),
        ratio: Number(response.data.coverage_ratio || 0),
        details: response.data.covered_point_details,
        updatedAt: Date.now()
      };
      
      // 存储到本地的 knowledgeCoverageMap
      knowledgeCoverageMap.value.set(nodeId, coverageData);
      
      // 同时尝试更新全局的 knowledgeCoverageByQuestion（用于与 ViewE 同步）
      if (knowledgeCoverageByQuestion !== undefined && knowledgeCoverageByQuestion !== null) {
        const key = `${caseInfo.sceneIndex}_${caseInfo.questionIndex}`;
        const node = graphData.value?.nodes?.find(n => n.id === nodeId);
        const leafId = node?.turnsList?.[node.turnsList.length - 1]?.id;
        
        if (leafId && typeof knowledgeCoverageByQuestion === 'object') {
          if (!knowledgeCoverageByQuestion[key]) {
            knowledgeCoverageByQuestion[key] = {};
          }
          knowledgeCoverageByQuestion[key][leafId] = coverageData;
          console.debug('[ViewD] ✓ Coverage evaluated for node', { nodeId: nodeId.substring(0, 20), points: coverageData.pointScores.length, ratio: Math.round(coverageData.ratio * 100) + '%' });
        }
      }
      
      return response.data.coverage_ratio;
    }
  } catch (err) {
    console.error('Failed to evaluate knowledge coverage:', err);
  }
  return 0;
};

// 为某个节点评估知识覆盖度
const evaluateCoverageForNode = async (nodeId) => {
  try {
    const node = graphData.value.nodes.find(n => n.id === nodeId);
    if (!node || !node.turnsList.length) {
      return;
    }

    // 收集该节点关联的所有消息的讨论内容
    const nodeMsgIds = new Set(node.turnsList.map(t => t.id));
    const questionMessages = messages.value.filter(m => 
      m.sceneIndex === activeQuestionInfo.value.sceneIndex && 
      m.questionIndex === activeQuestionInfo.value.questionIndex
    );
    
    // 从节点的最后一条消息开始，向上溯源到根，收集完整的讨论路径
    let leafMsg = null;
    for (let i = questionMessages.length - 1; i >= 0; i--) {
      const msg = questionMessages[i];
      if (nodeMsgIds.has(msg.id)) {
        leafMsg = msg;
        break;
      }
    }

    if (!leafMsg) {
      return;
    }

    // 收集从根到当前节点的所有讨论内容
    const discussionParts = [];
    let curr = leafMsg;
    let safety = 0;
    const msgMap = new Map(questionMessages.map(m => [m.id, m]));

    while (curr && safety < 1000) {
      if (curr.text && curr.agent !== 'case_introduction' && curr.agent !== 'Start Discussion') {
        discussionParts.unshift(`[${curr.agent}]: ${curr.text}`);
      }
      curr = msgMap.get(curr.parent_id);
      safety++;
    }

    const discussionContent = discussionParts.join('\n\n');

    if (!discussionContent.trim()) {
      console.warn('[coverage] empty discussion content for node', nodeId);
      return;
    }

    // 调用评估函数
    await evaluateKnowledgeCoverage(
      {
        caseName: activeQuestionInfo.value.caseName,
        sceneIndex: activeQuestionInfo.value.sceneIndex,
        questionIndex: activeQuestionInfo.value.questionIndex
      },
      discussionContent,
      nodeId
    );
  } catch (err) {
    console.error('Failed to evaluate coverage for node:', err);
  }
};

const evaluateCoverageForAllNodes = async () => {
  if (!activeQuestionInfo.value?.caseName) {
    console.warn('[coverage] skip evaluate: activeQuestionInfo.caseName is empty');
    return;
  }

  const pending = graphData.value.nodes
    .filter(n => n.turnsList?.length > 0)
    .filter(n => !knowledgeCoverageMap.value.has(n.id))
    .map(n => n.id);

  for (const nodeId of pending) {
    await evaluateCoverageForNode(nodeId);
  }
};

// 计算基于选中节点或活跃节点的“主路径” (包含祖先和后代)
const mainPathSet = computed(() => {
  const path = new Set();
  const graphLinks = graphData.value?.links;
  if (!messages?.value?.length || !graphLinks) return path;

  // Filter messages by active question
  const questionMessages = messages.value.filter(m => 
    m.sceneIndex === activeQuestionInfo.value.sceneIndex && 
    m.questionIndex === activeQuestionInfo.value.questionIndex
  );

  // 1. 建立节点之间的父子关系逻辑
  const nodeParentMap = {};
  graphLinks.forEach(l => {
    const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
    const targetId = typeof l.target === 'object' ? l.target.id : l.target;
    nodeParentMap[targetId] = sourceId;
  });

  // 2. 查找当前活跃消息所在的 nodeId
  const findNodeForMsg = (msgId) => {
     const foundNode = graphData.value.nodes.find(n => n.turnsList.some(t => t.id === msgId));
     return foundNode ? foundNode.id : null;
  };

  let anchorNodeKey = null;
  if (selectedTopic.value) {
    anchorNodeKey = selectedTopic.value;
  } else if (activeMessageId.value) {
    // 确保 activeMessageId 在当前问题的消息列表中
    if (questionMessages.find(m => m.id === activeMessageId.value)) {
      anchorNodeKey = findNodeForMsg(activeMessageId.value);
    }
  }

  if (!anchorNodeKey) return path;

  // 3. 向上溯源祖先
  let curr = anchorNodeKey;
  let safety = 0;
  while (curr && safety < 1000) {
    path.add(curr);
    const next = nodeParentMap[curr];
    if (!next || next === curr) break;
    curr = next;
    safety++;
  }

  // 4. 向下递归寻找所有后代 (展示完整的演化分支)
  const findDescendants = (startNode) => {
    for (const child in nodeParentMap) {
      if (nodeParentMap[child] === startNode && !path.has(child)) {
        path.add(child);
        findDescendants(child);
      }
    }
  };
  findDescendants(anchorNodeKey);

  return path;
});

// 数据处理：支持树状演化路径与干预标识
const graphData = computed(() => {
  const nodes = [];
  const links = [];
  const msgToNodeIdMap = new Map(); // msg_id -> nodeId
  const nodeMap = new Map(); // nodeId -> nodeObject

  // Filter messages by active question
  const questionMessages = messages.value.filter(m => 
    m.sceneIndex === activeQuestionInfo.value.sceneIndex && 
    m.questionIndex === activeQuestionInfo.value.questionIndex
  );

  // 1. 预处理：构建消息树结构，识别分叉点和分支路径
  const childCountMap = new Map(); // parent_id -> 子消息数
  const childrenMap = new Map(); // parent_id -> [children]
  const msgMap = new Map(); // msg_id -> msg
  
  questionMessages.forEach(m => {
    msgMap.set(m.id, m);
    if (m.parent_id) {
      childCountMap.set(m.parent_id, (childCountMap.get(m.parent_id) || 0) + 1);
      if (!childrenMap.has(m.parent_id)) {
        childrenMap.set(m.parent_id, []);
      }
      childrenMap.get(m.parent_id).push(m);
    }
  });

  // 2. 识别每条消息链的"当前活跃路径"（最新的分支）
  const getActivePathMsgIds = () => {
    const pathSet = new Set();
    if (questionMessages.length === 0) return pathSet;
    
    let curr = questionMessages[questionMessages.length - 1];
    let safety = 0;
    while (curr && safety < 1000) {
      pathSet.add(curr.id);
      curr = msgMap.get(curr.parent_id);
      safety++;
    }
    return pathSet;
  };
  const activePath = getActivePathMsgIds();

  // 3. 映射消息到节点
  questionMessages.forEach((msg) => {
    let topicName = (msg.topic || (msg.agent === 'teacher' ? 'Convention' : 'Unrecognized')).trim();
    // 过滤掉所有变体的开始讨论话题
    const skipTopics = ['unrecognized', 'start discussion', 'start_discussion', '开始讨论'];
    if (!topicName || skipTopics.includes(topicName.toLowerCase())) return;

    const branch = msg.branch_id || 'main';
    let shouldStartNewNode = false;
    let pNodeId = null;

    if (!msg.parent_id) {
      // 根消息：创建新节点
      shouldStartNewNode = true;
    } else {
      const pMsg = msgMap.get(msg.parent_id);
      if (!pMsg) {
        shouldStartNewNode = true;
      } else {
        const ptName = pMsg.topic || (pMsg.agent === 'teacher' ? 'Convention' : 'Unrecognized');
        pNodeId = msgToNodeIdMap.get(msg.parent_id);

        // 判断是否应该创建新节点：
        // 1. 话题改变 -> 新节点
        // 2. 分支改变 -> 新节点
        // 3. 父消息是分叉点（有多个子消息）且当前消息不在活跃路径上 -> 新节点（用于标记"老话题"）
        if (ptName !== topicName || pMsg.branch_id !== branch) {
          shouldStartNewNode = true;
        } else if (childCountMap.get(msg.parent_id) > 1 && !activePath.has(msg.id)) {
          // 这是分叉点的旧分支，需要创建"老话题"节点
          shouldStartNewNode = true;
        }
      }
    }

    let nodeId;
    if (shouldStartNewNode) {
      // 确定是否为“old topic”
      const isOldTopic = childCountMap.get(msg.parent_id) > 1 && !activePath.has(msg.id);
      const nodeLabelPrefix = isOldTopic ? 'Old Topic-' : '';
      const nodeLabel = nodeLabelPrefix + topicName;
      
      // 生成唯一的节点 ID：对于旧话题，使用第一条消息的 ID 以聚合同一分叉的旧消息
      if (isOldTopic) {
        const existingOldNode = nodes.find(n => n.label === nodeLabel && n.branch === branch && n.isOldTopic);
        if (existingOldNode) {
          nodeId = existingOldNode.id;
          shouldStartNewNode = false;
        } else {
          nodeId = `${branch}_old_${topicName}_${msg.id}`;
        }
      } else {
        // 特殊处理：对于初始消息（没有有效父节点），尝试复用同话题的已存在节点
        const pMsg = msgMap.get(msg.parent_id);
        const isInitialMsg = !msg.parent_id || !pMsg;
        
        if (isInitialMsg) {
          const existingNode = nodes.find(n => n.label === nodeLabel && n.branch === branch && !n.isOldTopic);
          if (existingNode) {
            nodeId = existingNode.id;
            shouldStartNewNode = false;
          } else {
            nodeId = `${branch}_${topicName}_${msg.id}`;
          }
        } else {
          nodeId = `${branch}_${topicName}_${msg.id}`;
        }
      }

      if (shouldStartNewNode) {
        // 计算 depth
        // 获取父节点对象
        const pNode = nodeMap.get(pNodeId);
        // 如果有父节点，深度+1，否则为0（根节点）
        const nodeDepth = pNode ? (pNode.depth + 1) : 0; 
        const newNode = {
          id: nodeId,
          label: nodeLabel,
          branch: branch,
          turns: 0,
          turnsList: [],
          hasTeacherFlag: msg.agent === 'teacher',
          interventionId: msg.agent === 'teacher' ? msg.id : null,
          isOldTopic: isOldTopic,
          order: nodes.length,
          depth: nodeDepth
        };
        nodes.push(newNode);
        nodeMap.set(nodeId, newNode);

        // 建立连线：连向父消息所在的节点
        if (pNodeId && pNodeId !== nodeId) {
          links.push({ source: pNodeId, target: nodeId });
        }
      }
    } else {
      nodeId = pNodeId;
    }

    const node = nodeMap.get(nodeId);
    if (node) {
      msgToNodeIdMap.set(msg.id, nodeId);

      // 更新节点数据
      if (msg.agent === 'teacher') {
        node.hasTeacherFlag = true;
        if (!node.interventionId) node.interventionId = msg.id;
      } else if (msg.agent !== 'case_introduction') {
        node.turns += 1;
        let color = getAgentColor(msg.agent);
        node.turnsList.push({
          id: msg.id,
          agent: msg.agent,
          color: color,
          tokens: msg.text?.length || 0
        });
      }
    }
  });

  return { nodes, links };
});

// D3 渲染逻辑
let simulation = null;

const initGraph = () => {
  if (!svgRef.value || !svgWrapper.value) return;

  const width = svgWrapper.value.clientWidth || 400;
  const height = svgWrapper.value.clientHeight || 400;

  const svg = d3.select(svgRef.value);
  svg.selectAll('*').remove();

  // 点击背景取消选中
  svg.on('click', (event) => {
    if (event.target === svgRef.value) {
      selectedTopic.value = null;
      selectedNodeLeafId.value = null;
    }
  });

  // 定义渐变阴影
  const defs = svg.append('defs');
  
  // 普通发光
  const filter = defs.append('filter')
    .attr('id', 'glow')
    .attr('x', '-50%')
    .attr('y', '-50%')
    .attr('width', '200%')
    .attr('height', '200%');
  filter.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'blur');
  filter.append('feComposite').attr('in', 'SourceGraphic').attr('in2', 'blur').attr('operator', 'over');

  // 红色高亮发光 (用于教师干预)
  const redFilter = defs.append('filter')
    .attr('id', 'glow-red')
    .attr('x', '-50%')
    .attr('y', '-50%')
    .attr('width', '200%')
    .attr('height', '200%');
  redFilter.append('feGaussianBlur').attr('stdDeviation', '5').attr('result', 'blur');
  redFilter.append('feFlood').attr('flood-color', '#EF4444').attr('flood-opacity', '0.7').attr('result', 'color');
  redFilter.append('feComposite').attr('in', 'color').attr('in2', 'blur').attr('operator', 'in').attr('result', 'glow');
  redFilter.append('feComposite').attr('in', 'SourceGraphic').attr('in2', 'glow').attr('operator', 'over');

  // 定义箭头
  defs.append('marker')
    .attr('id', 'arrowhead')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 22) // 略微增加，防止遮挡节点
    .attr('refY', 0)
    .attr('orient', 'auto')
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('markerUnits', 'userSpaceOnUse') // 关键：不随线宽缩放
    .append('path')
    .attr('d', 'M 0,-3 L 7,0 L 0,3') // 更尖锐的箭头
    .attr('fill', '#374151');

  // 定义高亮箭头
  defs.append('marker')
    .attr('id', 'arrowhead-active')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 22)
    .attr('refY', 0)
    .attr('orient', 'auto')
    .attr('markerWidth', 8)
    .attr('markerHeight', 8)
    .attr('markerUnits', 'userSpaceOnUse') // 关键：固定大小
    .append('path')
    .attr('d', 'M 0,-4 L 9,0 L 0,4')
    .attr('fill', '#2563EB');

  // 定义老师干预的红旗图标
  const flagMarker = defs.append('g').attr('id', 'teacher-flag');
  flagMarker.append('path')
    .attr('d', 'M10 2 L10 20 M10 4 L25 8 L10 12')
    .attr('stroke', '#EF4444')
    .attr('stroke-width', 2)
    .attr('fill', '#EF4444');

  const container = svg.append('g').attr('class', 'main-container');

  // 背景透明矩形，确保画布任何地方都能响应拖拽和点击
  svg.insert('rect', '.main-container')
    .attr('class', 'zoom-background')
    .attr('width', '100%')
    .attr('height', '100%')
    .attr('fill', 'transparent')
    .attr('pointer-events', 'all')
    .on('click', (event) => {
        if (event.target.classList.contains('zoom-background')) {
            selectedTopic.value = null;
            selectedNodeLeafId.value = null;
        }
    });

  // 添加缩放与平移功能
  const zoom = d3.zoom()
    .scaleExtent([0.1, 8]) // 增加缩放范围
    .on('zoom', (event) => {
      container.attr('transform', event.transform);
    });
  svg.call(zoom);

  // 使用力导向图，给平衡演化感和层级感
  simulation = d3.forceSimulation()
    // 1. 调整连线距离以匹配 depth 间距 (原 40 -> 100)
    .force('link', d3.forceLink().id(d => d.id).distance(100)) 
    // 2. 稍微增加斥力，防止缩短距离后节点重叠 (原 -200 -> -300)
    .force('charge', d3.forceManyBody().strength(-300)) 
    // 移除 forceCenter，改用强力的 X/Y 约束来保持平衡
    
    // 3. 修改 X 轴力：主路径保持在中心，分支根据名称偏移
    .force('x', d3.forceX(d => {
      // 如果是主路径，居中
      if (mainPathSet.value.has(d.id)) return width / 2;
      
      // 分支处理
      if (!d.branch || d.branch === 'main') return width / 2;
      
      // 为不同分支计算一个固定的 X 偏移 (简单的字符串哈希)
      let hash = 0;
      for (let i = 0; i < d.branch.length; i++) {
        hash = d.branch.charCodeAt(i) + ((hash << 5) - hash);
      }
      const offset = (hash % 3 === 0 ? -1 : 1) * (150 + (Math.abs(hash) % 100));
      return width / 2 + offset;
    }).strength(3.0))
    
    // 4. 修改 Y 轴力：完全按照 depth 确定位置，strength 设为最高
    .force('y', d3.forceY(d => (d.depth * 100 + 50)).strength(4.0))
    
    .force('collision', d3.forceCollide().radius(50))
    .alphaDecay(0.05);

  updateGraph();
};

const updateGraph = () => {
  if (!svgRef.value || !simulation) return;

  const { nodes, links } = graphData.value;
  const svg = d3.select(svgRef.value).select('.main-container');

  // 1. 连线
  const link = svg.selectAll('.topic-link')
    .data(links, d => `${d.source.id || d.source}-${d.target.id || d.target}`);

  link.exit().remove();
  const linkEnter = link.enter()
    .append('path')
    .attr('class', 'topic-link')
    .attr('fill', 'none')
    .attr('stroke', '#6B7280')
    .attr('stroke-width', 2)
    .attr('stroke-dasharray', '5,5')
    .attr('marker-end', 'url(#arrowhead)');

  // 2. 节点组
  const node = svg.selectAll('.node-group')
    .data(nodes, d => d.id);

  node.exit().remove();
  const nodeEnter = node.enter()
    .append('g')
    .attr('class', 'node-group')
    .on('click', (event, d) => {
      event.stopPropagation(); // 防止触发背景点击

      // 判断是否点击在红旗图标上
      const target = event.target;
      const isClickOnFlag = target.classList.contains('teacher-flag-icon') || 
                           (target.parentElement && target.parentElement.classList.contains('teacher-flag-icon')) ||
                           target.closest('.teacher-flag-icon');

      // 如果处于复盘模式或者是直接点击红旗，且节点包含教师干预，则打开总结弹窗
      if (d.hasTeacherFlag && (isHighlightingFlags.value || isClickOnFlag)) {
        openSummaryModal(d);
        return;
      }

      selectedTopic.value = d.id;
      
      // 更新该节点关联的最末端消息 ID，用于 ViewE/ViewF 过滤和下次教师干预
      let leafId = d.id;
      if (d.turnsList && d.turnsList.length > 0) {
        leafId = d.turnsList[d.turnsList.length - 1].id;
        selectedNodeLeafId.value = leafId;
      } else {
        // 如果是教师干预节点或其他特殊节点，优先使用存储的 interventionId
        leafId = d.interventionId || d.id;
        selectedNodeLeafId.value = leafId;
      }

      // 【新增】当暂停时，点击节点需要切换后端的焦点，使其能从该节点恢复讨论
      if (isPaused && leafId) {
        console.log('Switching focus to node leaf:', leafId, 'branch:', d.branch);
        switchNodeFocus(leafId, d.branch || 'main');
      }
    })
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended));

  // 呼吸高亮环
  nodeEnter.append('circle')
    .attr('class', 'pulse-ring')
    .attr('r', 40)
    .attr('fill', 'none')
    .attr('stroke', '#3B82F6')
    .attr('stroke-width', 2)
    .attr('opacity', 0)
    .attr('pointer-events', 'none');

  // 节点主体 (核心圆)
  nodeEnter.append('circle')
    .attr('class', 'core-circle')
    .attr('fill', '#FFFFFF')
    .attr('stroke', '#3B82F6')
    .attr('stroke-width', 3)
    .style('filter', 'url(#glow)');

  // 添加 hover tooltip (知识点详情)
  nodeEnter.append('title')
    .text(d => {
      const coverage = knowledgeCoverageMap.value.get(d.id);
      if (!coverage || !Array.isArray(coverage.pointScores) || coverage.pointScores.length === 0) {
        return 'No knowledge points covered yet';
      }
      const pointsList = coverage.pointScores
        .map(pt => `• ${pt.point}: ${Math.round((Number(pt.coverage_score || 0)) * 100)}%`)
        .join('\n');
      return `Knowledge Coverage: ${Math.round((coverage.ratio || 0) * 100)}%\n\nCovered Points:\n${pointsList}`;
    });

  // 主题名称标签
  const labelGroup = nodeEnter.append('g').attr('class', 'label-group');
  
  labelGroup.append('rect')
    .attr('rx', 4)
    .attr('ry', 4)
    .attr('fill', '#F3F4F6')
    .attr('stroke', '#9CA3AF')
    .attr('stroke-width', 1);

  labelGroup.append('text')
    .attr('text-anchor', 'middle')
    .attr('fill', '#1F2937')
    .attr('font-size', '12px')
    .attr('font-weight', 'bold');

  const allNodes = nodeEnter.merge(node);
  const allLinks = linkEnter.merge(link);

  // 3. 更新视觉属性
  allNodes.select('.core-circle')
    .transition().duration(500)
    .attr('r', d => 14 + Math.sqrt(d.turns) * 3);

  // 【新增】为新创建的节点初始化覆盖率：继承父节点的覆盖率
  /*
  const parentMap = new Map(); // nodeId -> parentNodeId
  links.forEach(link => {
    const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
    const targetId = typeof link.target === 'object' ? link.target.id : link.target;
    parentMap.set(targetId, sourceId);
  });

  allNodes.each(function(d) {
    const nodeId = d.id;
    const parentId = parentMap.get(nodeId);

    // 如果节点没有覆盖率数据，且有父节点，则继承父节点的覆盖率
    if (!knowledgeCoverageMap.value.has(nodeId) && parentId && knowledgeCoverageMap.value.has(parentId)) {
      const parentCoverage = knowledgeCoverageMap.value.get(parentId);
      knowledgeCoverageMap.value.set(nodeId, {
        ...parentCoverage,
        ratio: parentCoverage.ratio
      });
    }
  });
  */

  // 更新 tooltip 内容
  allNodes.select('title')
    .text(d => {
      let coverage = knowledgeCoverageMap.value.get(d.id);
      
      if (!coverage || !Array.isArray(coverage.pointScores) || coverage.pointScores.length === 0) {
        return 'No knowledge points covered yet';
      }
      const pointsList = coverage.pointScores
        .map(pt => `• ${pt.point}: ${Math.round((Number(pt.coverage_score || 0)) * 100)}%`)
        .join('\n');
      return `Knowledge Coverage: ${Math.round((coverage.ratio || 0) * 100)}%\n\nCovered Points:\n${pointsList}`;
    });

  // 动态调整标签位置和大小
  allNodes.each(function(d) {
    const nodeG = d3.select(this);
    const radius = 14 + Math.sqrt(d.turns) * 3;
    const label = d.label;
    
    const text = nodeG.select('text').text(label);
    const textWidth = text.node().getBBox().width + 12;
    
    nodeG.select('.label-group')
      .attr('transform', `translate(0, ${-radius - 25})`);
    
    nodeG.select('rect')
      .attr('x', -textWidth / 2)
      .attr('y', -10)
      .attr('width', textWidth)
      .attr('height', 20);
    
    nodeG.select('text')
      .attr('y', 4);

    // 绘制外圈刻度线 (Radial Turn Ticks)
    const tickInnerRadius = radius + 5;
    const tickOuterRadius = radius + 16; 
    
    // 直接显示所有 turns，不做过滤
    const displayTurns = d.turnsList;
    const totalTurns = displayTurns.length;

    const totalTokens = displayTurns.reduce((sum, t) => sum + (t.tokens || 0), 0);
    const fallbackWeight = totalTokens === 0 ? 1 : 0;
    const weights = displayTurns.map(t => (t.tokens && t.tokens > 0) ? t.tokens : fallbackWeight);
    const weightSum = weights.reduce((sum, w) => sum + w, 0) || 1;

    const gapAngle = totalTurns > 1 ? Math.min(0.08, (Math.PI * 2) * 0.01) : 0;
    const totalGap = gapAngle * totalTurns;
    const availableAngle = Math.max(0, (Math.PI * 2) - totalGap);

    let cursor = 0;
    const ticks = nodeG.selectAll('.turn-tick')
      .data(displayTurns, (v) => v.id);

    ticks.exit().remove();
    
    ticks.enter().append('path')
      .attr('class', 'turn-tick')
      .merge(ticks)
      .attr('d', (v, i) => {
        const fraction = weights[i] / weightSum;
        const arcLen = availableAngle * fraction;
        const startA = cursor;
        const endA = cursor + arcLen;
        cursor = endA + gapAngle;
        return d3.arc()
          .innerRadius(tickInnerRadius)
          .outerRadius(tickOuterRadius)
          .startAngle(startA)
          .endAngle(endA)();
      })
      .transition().duration(300) 
      .attr('fill', v => v.color)
      .attr('stroke', 'none');

    // 12 点钟方向引导竖线
    const marker = nodeG.selectAll('.clock-marker')
      .data([null]);
    marker.enter().append('line')
      .attr('class', 'clock-marker')
      .merge(marker)
      .attr('x1', 0)
      .attr('y1', -tickInnerRadius + 2)
      .attr('x2', 0)
      .attr('y2', -tickOuterRadius - 4)
      .attr('stroke', '#6B7280')
      .attr('stroke-width', 4)
      .attr('stroke-linecap', 'round');

    // 绘制教师干预红旗
    const flag = nodeG.selectAll('.teacher-flag-icon')
      .data(d.hasTeacherFlag ? [null] : []);
    flag.exit().remove();
    flag.enter().append('use')
      .attr('class', 'teacher-flag-icon')
      .attr('xlink:href', '#teacher-flag')
      .merge(flag)
      .attr('transform', `translate(${-radius - 12}, ${-radius - 20}) scale(1.5)`)
      .style('cursor', 'help');

    // 绘制知识覆盖度 - 灌水进度条 (圆形进度条)
    let coverageData = knowledgeCoverageMap.value.get(d.id) || { ratio: 0 };
    
    const waterRadius = radius - 2;
    const waterAngle = (coverageData.ratio || 0) * Math.PI * 2;
    
    const waterPath = nodeG.selectAll('.knowledge-water')
      .data([null]);
    
    waterPath.enter().append('path')
      .attr('class', 'knowledge-water')
      .merge(waterPath)
      .attr('d', d3.arc()
        .innerRadius(waterRadius - 4)
        .outerRadius(waterRadius)
        .startAngle(-Math.PI / 2)
        .endAngle(-Math.PI / 2 + waterAngle))
      .attr('fill', (() => {
        const ratio = coverageData.ratio || 0;
        if (ratio < 0.5) {
          const t = ratio * 2;
          return d3.interpolate('#EF4444', '#FBBF24')(t);
        }
        const t = (ratio - 0.5) * 2;
        return d3.interpolate('#FBBF24', '#10B981')(t);
      })())
      .attr('opacity', 0.8)
      .attr('stroke', 'white')
      .attr('stroke-width', 1);
    
    // 添加覆盖度百分比标签
    const coverageLabel = nodeG.selectAll('.coverage-label')
      .data([null]);
    
    coverageLabel.exit().remove();
    coverageLabel.enter().append('text')
      .attr('class', 'coverage-label')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.3em')
      .attr('font-size', '10px')
      .attr('font-weight', 'bold')
      .attr('fill', '#1F2937')
      .attr('pointer-events', 'none')
      .merge(coverageLabel)
      .text(() => `${Math.round(coverageData.ratio * 100)}%`)
        .attr('y', 3);
  });

  // 4. 重启模拟
  simulation.nodes(nodes);
  simulation.force('link').links(links);
  simulation.alpha(1).restart();

  simulation.on('tick', () => {
    // 贝塞尔曲线连线，从源节点中心连向目标节点的 label 中心
    allLinks.attr('d', d => {
      // 目标节点的半径需实时计算以匹配 label 偏移
      const targetRadius = 14 + Math.sqrt(d.target.turns) * 3;
      const targetY = d.target.y - targetRadius - 25; // Label 组的偏移中心
      
      return `M${d.source.x},${d.source.y}L${d.target.x},${targetY}`;
    });

    allNodes.attr('transform', d => `translate(${d.x},${d.y})`);
  });
};

function dragstarted(event, d) {
  if (!event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x; d.fy = d.y;
}
function dragged(event, d) {
  d.fx = event.x; d.fy = event.y;
}
function dragended(event, d) {
  if (!event.active) simulation.alphaTarget(0);
  d.fx = null; d.fy = null;
}

// 监听选中状态、主路径或复盘模式的变化，更新视觉效果
watch([selectedTopic, mainPathSet, isHighlightingFlags], ([newTopic, newPath, isReviving]) => {
  if (!svgRef.value || !simulation) return;
  const svg = d3.select(svgRef.value);
  const { links } = graphData.value;

  // 1. 节点视觉效果更新
  svg.selectAll('.node-group')
    .transition().duration(600).ease(d3.easeCubicInOut)
    .style('opacity', d => {
        if (isReviving) {
            return d.hasTeacherFlag ? 1 : 0.2;
        }
        return (newPath.has(d.id)) ? 1 : 0.2;
    })
    .style('cursor', d => (isReviving && d.hasTeacherFlag) ? 'help' : 'pointer');

  // 2. 节点主体环更新
  svg.selectAll('.core-circle')
    .transition().duration(600).ease(d3.easeCubicInOut)
    .attr('stroke', d => {
        if (isReviving && d.hasTeacherFlag) return '#EF4444';
        return (d.id === newTopic) ? '#F59E0B' : '#3B82F6';
    })
    .attr('stroke-width', d => {
        if (isReviving && d.hasTeacherFlag) return 6;
        return (d.id === newTopic) ? 8 : 3;
    })
    .style('filter', d => (isReviving && d.hasTeacherFlag) ? 'url(#glow-red)' : 'url(#glow)');

  // 3. 连线视觉效果更新
  svg.selectAll('.topic-link')
    .transition().duration(600).ease(d3.easeCubicInOut)
    .style('opacity', d => isReviving ? 0.1 : (newPath.has(d.source.id || d.source) && newPath.has(d.target.id || d.target) ? 1 : 0.15));

  // 4. 重热力导向 (复盘模式下如果不需要移动可以不调用)
  if (!isReviving) {
      const width = svgWrapper.value?.clientWidth || 400;
      simulation.force('x', d3.forceX(d => {
        if (newPath.has(d.id)) return width / 2;
        if (!d.branch || d.branch === 'main') return width / 2;
        
        let hash = 0;
        for (let i = 0; i < d.branch.length; i++) {
          hash = d.branch.charCodeAt(i) + ((hash << 5) - hash);
        }
        const offset = (hash % 3 === 0 ? -1 : 1) * (150 + (Math.abs(hash) % 100));
        return width / 2 + offset;
      }).strength(3.0));
      // 复盘模式切换时，也重新应用基于 depth 的 Y 轴约束，防止错位
      simulation.force('y', d3.forceY(d => (d.depth * 100 + 50)).strength(4.0));
      simulation.alpha(0.15).restart();
  }
}, { deep: true });

// 【新增】追踪覆盖率评估状态，防止频繁重复计算
const isCoverageEvaluating = ref(false);
const lastEvaluatedNodeIds = ref(new Set()); // 记录已评估过的节点
const lastMessageCount = ref(0); // 追踪上一轮的消息数量

// 【新增】直接监听消息到达，仅在必要时补充漏掉的覆盖率
// 绝大多数覆盖率现在由后端推送到 knowledgeCoverageByQuestion 缓存中，ViewD 自动同步
watch(() => messages?.value?.length, async (newLength) => {
  if (!newLength || !activeQuestionInfo.value?.caseName) return;
  
  if (newLength > (lastMessageCount.value || 0)) {
    lastMessageCount.value = newLength;
    
    // 延迟检查是否有缺失评估的节点
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // 检查是否有后端没推过来的节点（例如切换旧分支时）
    const key = `${activeQuestionInfo.value.sceneIndex}_${activeQuestionInfo.value.questionIndex}`;
    const coverageCache = knowledgeCoverageByQuestion?.value?.[key] || {};
    
    const pendingNodes = graphData.value?.nodes?.filter(n => 
      n.turnsList?.length > 0 && 
      !knowledgeCoverageMap.value.has(n.id) &&
      !Object.keys(coverageCache).some(leafId => n.turnsList.some(t => t.id === leafId))
    ) || [];

    if (pendingNodes.length > 0 && !isCoverageEvaluating.value) {
      isCoverageEvaluating.value = true;
      try {
        console.debug('[ViewD] 补充评估缺失节点:', pendingNodes.length);
        for (const node of pendingNodes) {
          await evaluateCoverageForNode(node.id);
        }
      } finally {
        isCoverageEvaluating.value = false;
      }
    }
  }
}, { immediate: false });

// 监听数据变化并重新渲染
watch(graphData, () => {
  updateGraph();
}, { deep: true });

// 监听知识覆盖度数据变化，更新可视化
watch(knowledgeCoverageMap, () => {
  updateGraph();
}, { deep: true });

// 追踪当前问题，用于检测问题变化
const previousQuestionKey = ref(null);

const remapCoverageFromQuestionCache = () => {
  if (!activeQuestionInfo?.value) return;
  const key = `${activeQuestionInfo.value.sceneIndex}_${activeQuestionInfo.value.questionIndex}`;
  const incoming = knowledgeCoverageByQuestion?.value?.[key] || {};
  
  // 【优化】只在问题真正改变时清空旧问题的覆盖率
  if (previousQuestionKey.value !== null && previousQuestionKey.value !== key) {
    // 问题已改变，清空旧问题的覆盖率
    knowledgeCoverageMap.value = new Map();
  }
  previousQuestionKey.value = key;
  
  // 从现有的map读取（如果问题相同）或从空开始
  const nextMap = new Map(knowledgeCoverageMap.value);

  // 建立节点的前驱关系映射
  const { links } = graphData.value;
  const parentMap = new Map(); // nodeId -> parentNodeId
  links.forEach(link => {
    const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
    const targetId = typeof link.target === 'object' ? link.target.id : link.target;
    parentMap.set(targetId, sourceId);
  });
  nodeAncestorMap.value = parentMap;

  const findNodeForLeafId = (leafId) => {
    const found = graphData.value.nodes.find(n => n.turnsList?.some(t => t.id === leafId));
    return found ? found.id : null;
  };

  // 【增量更新】只更新传入的新数据，保留未变更的数据
  Object.entries(incoming).forEach(([leafId, payload]) => {
    const nodeId = findNodeForLeafId(leafId);
    if (!nodeId) return;
    
    // 只更新新数据，保留未变更的字段
    const existing = nextMap.get(nodeId) || {};
    nextMap.set(nodeId, {
      totalPoints: Number(payload.total_points ?? existing.totalPoints ?? 0),
      coveredPoints: Array.isArray(payload.covered_points) ? payload.covered_points : (existing.coveredPoints || []),
      pointScores: Array.isArray(payload.point_scores) ? payload.point_scores : (existing.pointScores || []),
      score: Number(payload.coverage_score ?? existing.score ?? 0),
      ratio: Number(payload.coverage_ratio ?? existing.ratio ?? 0),
      details: Array.isArray(payload.covered_point_details) ? payload.covered_point_details : (existing.details || [])
    });
  });

  // 【单调性约束】确保覆盖率单调递增（累积特性）
  const ensureMonotonicCoverage = () => {
    // 移除单调性检查，因为在回滚或分支切换时，节点 ID 的重用可能导致父子关系发生变化
    // 且知识覆盖率应严格遵循后端返回的针对各节点的评估结果
    return;
  };

  ensureMonotonicCoverage();
  knowledgeCoverageMap.value = nextMap;
};

watch(knowledgeCoverageByQuestion, () => {
  remapCoverageFromQuestionCache();
}, { deep: true });

// topic_update 会触发图重分组并导致 nodeId 变化；这里强制按 leafId 重新映射，避免覆盖率掉回 0
watch(graphData, () => {
  remapCoverageFromQuestionCache();
}, { deep: true });

onMounted(async () => {
  initGraph();
});
</script>

<style scoped>
.view-d-container{background-color: #ECECEC;}
.view-d-header {
  background: #000000;
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  z-index: 10;
}
.view-title {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
  text-align: left;
}
.node-group { cursor: grab; }
.node-group:active { cursor: grabbing; }
.topic-link { transition: stroke-dashoffset 0.5s; }

/* Knowledge Coverage Styles */
.knowledge-water {
  transition: fill 0.3s ease, stroke 0.3s ease;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1));
}

.coverage-label {
  font-family: 'Courier New', monospace;
  font-weight: bold;
  text-shadow: 0 1px 2px rgba(255, 255, 255, 0.8);
}

</style>