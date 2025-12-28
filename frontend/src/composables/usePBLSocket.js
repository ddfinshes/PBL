import { ref, onUnmounted, nextTick } from 'vue';

/**
 * @description 管理 PBL 讨论的 WebSocket 连接的组合式函数。
 * @param {string} sessionId - 讨论会话的唯一标识符。
 * @param {function} onScrollToBottom - 在接收到新消息后用于滚动聊天视图的回调函数。
 */
export function usePBLSocket(sessionId, onScrollToBottom) {
  // --- 响应式状态 ---
  const messages = ref([]);
  const isConnected = ref(false);
  const discussionStage = ref('等待开始'); // 初始阶段

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
      
      if (data.node && data.content) {
        messages.value.push({
          id: Date.now() + Math.random(), // 简单的唯一ID
          agent: data.node,
          text: data.content,
        });

        // DOM 更新后自动滚动到底部
        nextTick(() => {
          onScrollToBottom();
        });
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
      messages.value = []; // 清空之前的消息
      discussionStage.value = '初步诊断与鉴别诊断';
      socket.send(JSON.stringify({
        action: 'start_discussion',
        initial_case: initialCase,
      }));
    } else {
      console.error('WebSocket 未连接。');
    }
  };

  /**
   * 向后端发送老师的干预消息。
   * @param {string} interventionText - 来自老师的消息。
   */
  const sendTeacherIntervention = (interventionText) => {
    if (socket && isConnected.value) {
      // 为即时反馈，直接将老师的消息添加到聊天中
      messages.value.push({
        id: Date.now(),
        agent: 'teacher',
        text: interventionText,
      });
      nextTick(() => onScrollToBottom());

      socket.send(JSON.stringify({
        action: 'teacher_intervention',
        content: interventionText,
      }));
    } else {
      console.error('WebSocket 未连接。');
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
    isConnected,
    discussionStage,
    startDiscussion,
    sendTeacherIntervention,
  };
}

