import { ref, onUnmounted, nextTick, watch } from 'vue';
import axios from 'axios';

/**
 * @description 管理 PBL 讨论的 WebSocket 连接的组合式函数。
 * @param {string} sessionId - 讨论会话的唯一标识符。
 * @param {function} onScrollToBottom - 在接收到新消息后用于滚动聊天视图的回调函数。
 */
export function usePBLSocket(sessionId, onScrollToBottom) {
  // --- 响应式状态 ---
  const messages = ref([]);
  const currentTopic = ref('Undefined');
  const isConnected = ref(false);
  const isPaused = ref(false); // 新增：记录是否处于持续暂停状态
  const discussionStage = ref('Waiting to Start'); // 初始阶段
  const activeMessageId = ref(null); // 当前活跃的消息节点 ID
  const selectedTopic = ref(null); // 当前选中的主题（用于过滤）
  const selectedNodeLeafId = ref(null); // 当前选中主题节点的最新一条消息 ID
  const activeQuestionInfo = ref({ sceneIndex: -1, questionIndex: -1 });
  const interventionSummaries = ref({}); // 新增：离线/归档的总结分析数据 (intervention_id -> {parts, timestamp})
  const personas = ref({}); // 新增：Agent 配置数据
  const objectiveEvaluationMap = ref({}); // key: "scene_question" -> latest + rounds
  const discussionEndByQuestion = ref({}); // key: "scene_question" -> end payload
  const agentStateByQuestion = ref({}); // key: "scene_question" -> latest runtime snapshot
  const knowledgeCoverageByQuestion = ref({}); // key: "scene_question" -> { nodeLeafId -> coverage }

  const applyAgentStateSnapshot = (sceneIndex, questionIndex, snapshot) => {
    if (!Number.isFinite(sceneIndex) || !Number.isFinite(questionIndex)) return;
    if (!snapshot || typeof snapshot !== 'object') return;
    const key = `${sceneIndex}_${questionIndex}`;
    agentStateByQuestion.value = {
      ...agentStateByQuestion.value,
      [key]: {
        ...snapshot,
        updatedAt: Date.now()
      }
    };
  };

  // 加载 Agent 配置
  const fetchPersonas = async () => {
    try {
      const resp = await axios.get('http://127.0.0.1:8000/get_personas');
      personas.value = resp.data;
    } catch (err) {
      console.error('Failed to fetch personas:', err);
    }
  };

  // 通过名称或 Key 获取 Agent 配置的通用方法
  const getAgentConfig = (agentKey) => {
    if (!agentKey || !personas.value) return {};
    if (personas.value[agentKey]) return personas.value[agentKey];
    const found = Object.values(personas.value).find(p => p.name === agentKey);
    return found || {};
  };

  const getAgentColor = (agentKey) => {
    if (agentKey === 'teacher' || agentKey === 'teacher_handler') return '#E0E7FF';
    if (agentKey === 'case_introduction') return '#E5E7EB';
    const config = getAgentConfig(agentKey);
    return config.cardColor || config.color || '#8095CA';
  };

  const getAgentName = (agentKey) => {
    if (agentKey === 'teacher' || agentKey === 'teacher_handler') return 'Teacher';
    if (agentKey === 'case_introduction') return 'Case Introduction';
    const config = getAgentConfig(agentKey);
    return config.name || agentKey;
  };

  const getAgentAvatar = (agentKey) => {
    if (agentKey === 'teacher' || agentKey === 'teacher_handler') return '/avatar/teacher.png';
    const config = getAgentConfig(agentKey);
    const avatar = config.avatar || 'avatar1.png';
    // 兼容性处理：如果是完整的 URL 或以 / 开头则直接返回，否则由于 vite/public 结构补全路径
    return avatar.startsWith('http') || avatar.startsWith('/') ? avatar : `/avatar/${avatar}`;
  };
  watch(activeQuestionInfo, (newVal) => {
    if (socket && isConnected.value && newVal.sceneIndex !== -1) {
      console.log('Switching socket context to:', newVal);
      isPaused.value = true; // 切换查看时，默认进入暂停状态，由教师决定何时开始/恢复
      socket.send(JSON.stringify({
        action: 'switch_context',
        scene_index: newVal.sceneIndex,
        question_index: newVal.questionIndex
      }));
    }
  }, { deep: true });

  let socket = null;
  let reconnectTimer = null;
  const reconnectInterval = 5000; // 5秒

  // --- 私有方法 ---
  const connect = () => {
    const url = `ws://127.0.0.1:8000/ws/pbl/${sessionId}`;
    socket = new WebSocket(url);

    socket.onopen = () => {
      console.log('WebSocket 已连接');
      isConnected.value = true;
      clearTimeout(reconnectTimer);
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'history_sync' && data.messages) {
        console.log('Synchronizing history from server:', data.messages.length);

        // 1. 同步总结分析
        if (data.intervention_summaries) {
          interventionSummaries.value = { ...interventionSummaries.value, ...data.intervention_summaries };
          console.log('Synchronized summaries:', Object.keys(data.intervention_summaries).length);
        }

        // 2. 合并历史消息，避免重复
        const existingIds = new Set(messages.value.map(m => m.id));
        const newMsgs = data.messages.filter(m => !existingIds.has(m.id)).map(m => ({
          id: m.id,
          parent_id: m.parent_id,
          branch_id: m.branch_id || 'main',
          agent: m.agent,
          text: m.content,
          summary: m.summary || m.content,
          topic: m.topic || '历史记录',
          timestamp: m.timestamp || Date.now(),
          sceneIndex: m.scene_index,
          questionIndex: m.question_index,
          stateSnapshot: m.state_snapshot || null
        }));

        if (newMsgs.length > 0) {
          messages.value = [...messages.value, ...newMsgs].sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
          newMsgs.forEach((m) => {
            applyAgentStateSnapshot(Number(m.sceneIndex), Number(m.questionIndex), m.stateSnapshot);
          });
          // 如果没有活跃 ID，则设为最后一条
          if (!activeMessageId.value && messages.value.length > 0) {
            activeMessageId.value = messages.value[messages.value.length - 1].id;
          }
        }
      }

      if (data.type === 'agent_output' && (data.node || data.agent) && data.content) {
        const newMsg = {
          id: data.id || (sessionId + Math.random()),
          parent_id: data.parent_id,
          branch_id: data.branch_id || 'main',
          agent: data.agent || data.node,
          text: data.content,
          summary: data.summary || data.content,
          topic: data.topic || currentTopic.value,
          timestamp: Date.now(),
          sceneIndex: data.scene_index,
          questionIndex: data.question_index,
          stateSnapshot: data.state_snapshot || null
        };
        messages.value.push(newMsg);
        activeMessageId.value = newMsg.id;
        applyAgentStateSnapshot(Number(newMsg.sceneIndex), Number(newMsg.questionIndex), newMsg.stateSnapshot);

        // 即时消费后端同包返回的知识覆盖评估（与 summary 同步到达）
        if (data.knowledge_coverage && typeof data.knowledge_coverage === 'object') {
          const sceneIndex = Number(data.scene_index ?? -1);
          const questionIndex = Number(data.question_index ?? -1);
          const key = `${sceneIndex}_${questionIndex}`;
          const leafId = String(data.id || '').trim();
          if (leafId) {
            const prevByLeaf = knowledgeCoverageByQuestion.value[key] || {};
            knowledgeCoverageByQuestion.value = {
              ...knowledgeCoverageByQuestion.value,
              [key]: {
                ...prevByLeaf,
                [leafId]: {
                  ...data.knowledge_coverage,
                  updatedAt: Date.now(),
                },
              },
            };
          }
        }

        // DOM 更新后自动滚动到底部
        nextTick(() => {
          onScrollToBottom();
        });
      }

      // 【新增】处理异步消息更新（简化版本和知识覆盖）
      if (data.type === 'message_update' && data.id) {
        const msgIdx = messages.value.findIndex(m => m.id === data.id);
        if (msgIdx !== -1) {
          // 更新消息的summary和知识覆盖
          if (data.summary) {
            messages.value[msgIdx].summary = data.summary;
          }
          if (data.knowledge_coverage && typeof data.knowledge_coverage === 'object') {
            const msg = messages.value[msgIdx];
            const sceneIndex = Number(msg.sceneIndex ?? -1);
            const questionIndex = Number(msg.questionIndex ?? -1);
            const key = `${sceneIndex}_${questionIndex}`;
            const leafId = String(msg.id || '').trim();
            if (leafId) {
              const prevByLeaf = knowledgeCoverageByQuestion.value[key] || {};
              knowledgeCoverageByQuestion.value = {
                ...knowledgeCoverageByQuestion.value,
                [key]: {
                  ...prevByLeaf,
                  [leafId]: {
                    ...data.knowledge_coverage,
                    updatedAt: Date.now(),
                  },
                },
              };
            }
          }
        }
      }

      if (data.type === 'rollback_ack') {
        activeMessageId.value = data.target_id;
        console.log('Rollback successful, activeId set to:', data.target_id);
      }

      if (data.type === 'teacher_intervention_ack') {
        console.log('Teacher intervention ack received, resetting topic.');
        currentTopic.value = 'Undefined';
        selectedTopic.value = null; // 教师干预后取消选中，以便看到最新的分支动态
        selectedNodeLeafId.value = null;
      }

      if (data.type === 'topic_update' && data.topic) {
        console.log('Topic updated:', data.topic);
        currentTopic.value = data.topic;

        // 【分支关联】关联到当前最新的消息
        if (data.id) {
          const targetMsg = messages.value.find(m => m.id === data.id);
          if (targetMsg) targetMsg.topic = data.topic;
        }

        let hasChanged = false;
        messages.value.forEach(msg => {
          if (msg.topic === 'Undefined' || msg.topic === 'start_discussion' || !msg.topic) {
            msg.topic = data.topic;
            hasChanged = true;
          }
        });
        if (hasChanged) {
          messages.value = [...messages.value];
        }
      }

      if (data.type === 'discussion_paused') {
        isPaused.value = true;
      } else if (data.type === 'discussion_resumed') {
        isPaused.value = false;
      }

      if (data.type === 'objective_update') {
        const sceneIndex = Number(data.scene_index ?? -1);
        const questionIndex = Number(data.question_index ?? -1);
        const key = `${sceneIndex}_${questionIndex}`;
        const incomingRows = Array.isArray(data.objective_evaluations) ? data.objective_evaluations : [];
        console.log('[objective_update] recv', {
          key,
          rowCount: incomingRows.length,
          triggerQuestion: data.trigger_question || '',
          activeKey: `${activeQuestionInfo.value.sceneIndex}_${activeQuestionInfo.value.questionIndex}`
        });
        const prev = objectiveEvaluationMap.value[key] || { rounds: [] };
        const round = {
          id: `round-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`,
          triggerQuestion: data.trigger_question || prev.triggerQuestion || '',
          objectiveEvaluations: incomingRows,
          achievedAll: incomingRows.length > 0 && incomingRows.every((item) => Boolean(item?.achieved)),
          updatedAt: Date.now()
        };

        objectiveEvaluationMap.value = {
          ...objectiveEvaluationMap.value,
          [key]: {
            triggerQuestion: round.triggerQuestion,
            objectiveEvaluations: round.objectiveEvaluations,
            achievedAll: round.achievedAll,
            updatedAt: round.updatedAt,
            rounds: [...(Array.isArray(prev.rounds) ? prev.rounds : []), round]
          }
        };
        console.log('[objective_update] map keys', Object.keys(objectiveEvaluationMap.value));
      }

      if (data.type === 'objective_evaluation_update') {
        const sceneIndex = Number(data.scene_index ?? -1);
        const questionIndex = Number(data.question_index ?? -1);
        const key = `${sceneIndex}_${questionIndex}`;
        const incomingRows = Array.isArray(data.objective_evaluations) ? data.objective_evaluations : [];
        const prev = objectiveEvaluationMap.value[key] || { rounds: [] };

        objectiveEvaluationMap.value = {
          ...objectiveEvaluationMap.value,
          [key]: {
            ...prev,
            objectiveEvaluations: incomingRows,
            achievedAll: Boolean(data.achieved_all),
            updatedAt: Date.now()
          }
        };
        console.log('[objective_evaluation_update] updated map', key);
      }

      if (data.type === 'discussion_end') {
        const sceneIndex = Number(data.scene_index ?? -1);
        const questionIndex = Number(data.question_index ?? -1);
        const key = `${sceneIndex}_${questionIndex}`;
        console.log('[discussion_end] recv', {
          key,
          achievedAll: Boolean(data.achieved_all),
          objectiveCount: Array.isArray(data.objective_evaluations) ? data.objective_evaluations.length : 0
        });
        discussionEndByQuestion.value = {
          ...discussionEndByQuestion.value,
          [key]: {
            reason: data.reason || 'unknown',
            achievedAll: Boolean(data.achieved_all),
            triggerQuestion: data.trigger_question || '',
            objectiveEvaluations: Array.isArray(data.objective_evaluations) ? data.objective_evaluations : [],
            updatedAt: Date.now()
          }
        };
      }

      if (data.type === 'state_restored') {
        const sceneIndex = Number(data.scene_index ?? -1);
        const questionIndex = Number(data.question_index ?? -1);
        const key = `${sceneIndex}_${questionIndex}`;
        const restoredRows = Array.isArray(data.objective_evaluations) ? data.objective_evaluations : [];
        const restoredAt = Date.now();

        // 【新增】恢复该快照点对应的知识覆盖评估数据
        if (data.knowledge_coverage && typeof data.knowledge_coverage === 'object') {
          const leafId = activeMessageId.value;
          if (leafId) {
            const prevByLeaf = knowledgeCoverageByQuestion.value[key] || {};
            knowledgeCoverageByQuestion.value = {
              ...knowledgeCoverageByQuestion.value,
              [key]: {
                ...prevByLeaf,
                [leafId]: {
                  ...data.knowledge_coverage,
                  updatedAt: Date.now()
                }
              }
            };
          }
        }

        objectiveEvaluationMap.value = {
          ...objectiveEvaluationMap.value,
          [key]: {
            triggerQuestion: data.trigger_question || '',
            objectiveEvaluations: restoredRows,
            achievedAll: Boolean(data.achieved_all),
            updatedAt: restoredAt,
            rounds: restoredRows.length > 0
              ? [{
                id: `restore-${restoredAt}`,
                triggerQuestion: data.trigger_question || '',
                objectiveEvaluations: restoredRows,
                achievedAll: Boolean(data.achieved_all),
                updatedAt: restoredAt
              }]
              : []
          }
        };

        if (String(data.end_reason || '').trim()) {
          discussionEndByQuestion.value = {
            ...discussionEndByQuestion.value,
            [key]: {
              reason: data.end_reason,
              achievedAll: Boolean(data.achieved_all),
              triggerQuestion: data.trigger_question || '',
              objectiveEvaluations: restoredRows,
              updatedAt: restoredAt
            }
          };
        } else {
          // Restored state is not ended: clear stale end-state for this question.
          const nextEndMap = { ...discussionEndByQuestion.value };
          delete nextEndMap[key];
          discussionEndByQuestion.value = nextEndMap;
        }

        applyAgentStateSnapshot(sceneIndex, questionIndex, data.state_snapshot || null);

        console.log('[state_restored] applied', {
          key,
          rowCount: restoredRows.length,
          achievedAll: Boolean(data.achieved_all),
          endReason: data.end_reason || ''
        });
      }

      if (data.type === 'state_snapshot_update') {
        const sceneIndex = Number(data.scene_index ?? -1);
        const questionIndex = Number(data.question_index ?? -1);
        applyAgentStateSnapshot(sceneIndex, questionIndex, data.state_snapshot || null);
      }

      if (data.type === 'knowledge_coverage_update') {
        const sceneIndex = Number(data.scene_index ?? -1);
        const questionIndex = Number(data.question_index ?? -1);
        const key = `${sceneIndex}_${questionIndex}`;
        const leafId = String(data.node_id || '').trim();
        const coverage = data.coverage || {};
        if (leafId) {
          const prev = knowledgeCoverageByQuestion.value[key] || {};
          knowledgeCoverageByQuestion.value = {
            ...knowledgeCoverageByQuestion.value,
            [key]: {
              ...prev,
              [leafId]: {
                ...coverage,
                updatedAt: Date.now()
              }
            }
          };
        }
      }

      if (data.type === 'stage_update' && data.stage_name) {
        // 翻译中文阶段名到英文
        const stageNameCn = data.stage_name.split('】')[0].replace('【', '');
        const stageMap = {
          '问题识别': 'Problem Identification',
          '知识激活': 'Knowledge Activation',
          '诊断推理': 'Diagnostic Reasoning',
          '治疗计划': 'Treatment Plan',
          '总结反思': 'Summary & Reflection'
        };
        discussionStage.value = stageMap[stageNameCn] || stageNameCn;
        console.log('Stage updated:', data.stage_name);
      }
    };

    socket.onclose = () => {
      console.log('WebSocket 已断开。正在尝试重新连接...');
      isConnected.value = false;
      reconnectTimer = setTimeout(connect, reconnectInterval);
    };

    socket.onerror = (error) => {
      console.error('WebSocket 错误:', error);
      socket.close(); // 这将触发 onclose 事件和重连逻辑
    };
  };

  // --- 公共方法 ---

  /**
   * 通过向后端发送初始案例来开始 PBL 讨论。
   * @param {string} initialCase - 病例介绍文本。
   * @param {number} sceneIndex - 场景索引。
   * @param {number} questionIndex - 问题索引。
   */
  const startDiscussion = (initialCase, sceneIndex = 0, questionIndex = 0) => {
    if (socket && isConnected.value) {
      selectedTopic.value = null; // 开始新讨论时清空选中状态
      selectedNodeLeafId.value = null;
      // Preserve caseName (and any other fields) set by handleInspectQuestion in App.vue.
      activeQuestionInfo.value = { ...activeQuestionInfo.value, sceneIndex, questionIndex };

      // 使用 nextTick 确保在 watch(activeQuestionInfo) 之后执行，防止被 watch 覆盖为暂停状态
      nextTick(() => {
        isPaused.value = false;
      });

      const introMsg = {
        id: 'case-intro-' + Date.now(),
        agent: 'case_introduction',
        text: initialCase,
        topic: 'Undefined',
        sceneIndex,
        questionIndex
      };
      messages.value.push(introMsg);

      discussionStage.value = 'Phase 1: Problem Identification';
      socket.send(JSON.stringify({
        action: 'start_discussion',
        initial_case: initialCase,
        scene_index: sceneIndex,
        question_index: questionIndex
      }));

      nextTick(() => onScrollToBottom());
    } else {
      console.error('WebSocket 未连接。');
    }
  };

  /**
   * 切换讨论的暂停/继续状态。
   */
  const togglePause = () => {
    if (!socket || !isConnected.value) return;

    if (isPaused.value) {
      // 如果当前是暂停的，发送继续指令
      socket.send(JSON.stringify({ action: 'resume_discussion' }));
      isPaused.value = false;
    } else {
      // 如果当前是运行的，发送暂停指令
      socket.send(JSON.stringify({ action: 'pause_discussion' }));
      isPaused.value = true;
    }
  };

  /**
   * 向后端发送老师的干预消息。
   * @param {string} interventionText - 来自老师的消息。
   */
  const sendTeacherIntervention = (interventionText) => {
    console.log('sendTeacherIntervention', socket, isConnected.value)
    if (socket && isConnected.value) {
      // 干预后，自动取消暂停状态
      isPaused.value = false;

      // 优先从选中的节点叶子开始干预，否则从当前最活跃的消息开始
      let parentId = selectedNodeLeafId.value || activeMessageId.value;

      socket.send(JSON.stringify({
        action: 'teacher_intervention',
        content: interventionText,
        parent_id: parentId
      }));
    } else {
      console.error('WebSocket 未连接。');
    }
  };

  /**
   * 回退到特定消息
   */
  const rollbackTo = (messageId) => {
    if (socket && isConnected.value) {
      // 执行回退操作时，自动取消当前的主题选中状态，
      // 并乐观更新活跃消息 ID，以确保视图（尤其是 ViewF）能够立即显示回退后的对话状态。
      selectedTopic.value = null;
      selectedNodeLeafId.value = null;
      activeMessageId.value = messageId;
      socket.send(JSON.stringify({
        action: 'rollback_to',
        target_id: messageId
      }));
    }
  };

  /**
   * 在暂停时切换节点焦点（用于切换分支后恢复讨论）
   * @param {string} targetId - 目标消息 ID
   * @param {string} branchId - 目标分支 ID
   */
  const switchNodeFocus = (targetId, branchId = 'main') => {
    if (socket && isConnected.value && isPaused.value) {
      console.log('Switching node focus to:', targetId, 'on branch:', branchId);
      socket.send(JSON.stringify({
        action: 'switch_node_focus',
        target_id: targetId,
        branch_id: branchId
      }));
    }
  };

  /**
   * 强制恢复讨论（不受 isPaused 限制），用于教师 Override 触发后需要继续讨论的场景
   */
  const forceResume = () => {
    if (socket && isConnected.value) {
      socket.send(JSON.stringify({ action: 'force_resume' }));
      isPaused.value = false;
    }
  };

  // --- 生命周期钩子 ---
  onUnmounted(() => {
    if (socket) {
      clearTimeout(reconnectTimer); // 清除重连计时器
      socket.close();
    }
  });

  // 初始连接
  connect();
  fetchPersonas();

  // 返回暴露给组件的状态 and 方法
  return {
    messages,
    currentTopic,
    isConnected,
    isPaused,
    discussionStage,
    activeMessageId,
    selectedTopic,
    selectedNodeLeafId,
    activeQuestionInfo,
    interventionSummaries,
    personas,
    objectiveEvaluationMap,
    discussionEndByQuestion,
    agentStateByQuestion,
    knowledgeCoverageByQuestion,
    fetchPersonas,
    getAgentConfig,
    getAgentColor,
    getAgentName,
    getAgentAvatar,
    startDiscussion,
    togglePause,
    sendTeacherIntervention,
    rollbackTo,
    switchNodeFocus,
    forceResume
  };
}

