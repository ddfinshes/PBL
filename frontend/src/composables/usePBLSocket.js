import { ref, onUnmounted, nextTick } from 'vue';

/**
 * @description 管理 PBL 讨论的 WebSocket 连接的组合式函数。
 * @param {string} sessionId - 讨论会话的唯一标识符。
 * @param {function} onScrollToBottom - 在接收到新消息后用于滚动聊天视图的回调函数。
 */
export function usePBLSocket(sessionId, onScrollToBottom) {
  // --- 响应式状态 ---
  const messages = ref([]);
  const currentTopic = ref('待识别');
  const isConnected = ref(false);
  const isPaused = ref(false); // 新增：记录是否处于持续暂停状态
  const discussionStage = ref('等待开始'); // 初始阶段
  const activeMessageId = ref(null); // 当前活跃的消息节点 ID
  const selectedTopic = ref(null); // 当前选中的主题（用于过滤）

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

      if (data.type === 'agent_output' && (data.node || data.agent) && data.content) {
        const newMsg = {
          id: data.id || (sessionId + Math.random()),
          parent_id: data.parent_id,
          branch_id: data.branch_id || 'main',
          agent: data.agent || data.node,
          text: data.content,
          summary: data.summary || data.content,
          topic: data.topic || currentTopic.value,
          timestamp: Date.now()
        };
        messages.value.push(newMsg);
        activeMessageId.value = newMsg.id;

        // DOM 更新后自动滚动到底部
        nextTick(() => {
          onScrollToBottom();
        });
      }

      if (data.type === 'rollback_ack') {
        activeMessageId.value = data.target_id;
        console.log('Rollback successful, activeId set to:', data.target_id);
      }

      if (data.type === 'teacher_intervention_ack') {
        console.log('Teacher intervention ack received, resetting topic.');
        currentTopic.value = '待识别';
        selectedTopic.value = null; // 教师干预后取消选中，以便看到最新的分支动态
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
          if (msg.topic === '待识别' || msg.topic === '开始讨论' || !msg.topic) {
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

      // 如果后端发送了阶段更新，也可以在这里处理
      // 例如: if (data.stage) { discussionStage.value = data.stage; }
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
   */
  const startDiscussion = (initialCase) => {
    if (socket && isConnected.value) {
      selectedTopic.value = null; // 开始新讨论时清空选中状态
      messages.value = [
        {
          id: 'case-intro-' + Date.now(),
          agent: 'case_introduction',
          text: initialCase,
          topic: '待识别'
        }
      ]; // 初始化并加入病例
      discussionStage.value = '初步诊断与鉴别诊断';
      socket.send(JSON.stringify({
        action: 'start_discussion',
        initial_case: initialCase,
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

      let parentId = activeMessageId.value;
      // 如果当前选中了某个主题，则从该主题对应的最新一条消息后进行教师干预/分支
      if (selectedTopic.value) {
        const topicMsgs = messages.value.filter(m => {
          let tName = m.topic || (m.agent === 'teacher' ? '教师干预' : '待识别');
          return `${m.branch_id || 'main'}_${tName}` === selectedTopic.value;
        });
        if (topicMsgs.length > 0) {
          parentId = topicMsgs[topicMsgs.length - 1].id;
        }
      }

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
      activeMessageId.value = messageId;
      socket.send(JSON.stringify({
        action: 'rollback_to',
        target_id: messageId
      }));
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

  // 返回暴露给组件的状态和方法
  return {
    messages,
    currentTopic,
    isConnected,
    isPaused,
    discussionStage,
    activeMessageId,
    selectedTopic,
    startDiscussion,
    togglePause,
    sendTeacherIntervention,
    rollbackTo
  };
}

