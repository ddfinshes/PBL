<template>
  <div class="view-container view-e">
    <div class="view-header">
      <h3 class="view-title">{{ title }}</h3>
      <div class="header-actions">
        <button v-if="!currentTopic" @click="showStartDialog = true" class="start-button">
          开始讨论
        </button>
        <div v-else class="topic-display">
          <span class="topic-label">主题：</span>
          <span class="topic-text">{{ currentTopic }}</span>
        </div>
        <div class="connection-status" :class="{ connected: isConnected }">
          <span class="status-dot"></span>
          <span class="status-text">{{ isConnected ? '已连接' : '未连接' }}</span>
        </div>
      </div>
    </div>

    <!-- 开始讨论对话框 -->
    <div v-if="showStartDialog" class="dialog-overlay" @click="showStartDialog = false">
      <div class="dialog-content" @click.stop>
        <h4>开始新讨论</h4>
        <input
          v-model="newTopic"
          @keyup.enter="handleStartDiscussion"
          type="text"
          placeholder="输入讨论主题..."
          class="topic-input"
        />
        <div class="dialog-actions">
          <button @click="showStartDialog = false" class="cancel-button">取消</button>
          <button @click="handleStartDiscussion" :disabled="!newTopic.trim()" class="confirm-button">
            开始
          </button>
        </div>
      </div>
    </div>

    <!-- 消息显示区域 -->
    <div class="messages-container" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-state">
        <div class="empty-icon">💬</div>
        <div class="empty-text">暂无消息，开始讨论吧</div>
      </div>
      <div v-else class="messages-list">
        <div
          v-for="(message, index) in messages"
          :key="index"
          class="message-item"
          :class="{
            'user-message': message.agent === '用户',
            [`agent-${getAgentClass(message.agent)}`]: message.agent !== '用户'
          }"
        >
          <div class="message-header">
            <span class="agent-name">{{ message.agent }}</span>
            <span class="message-time">{{ formatTime(message.timestamp) }}</span>
            <span v-if="message.type" class="message-type">{{ getTypeLabel(message.type) }}</span>
          </div>
          <div class="message-content">{{ message.content }}</div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-container">
      <div class="input-wrapper">
        <input
          v-model="inputMessage"
          @keyup.enter="sendMessage"
          :disabled="!isConnected || sending"
          type="text"
          placeholder="输入消息并按回车发送..."
          class="message-input"
        />
        <button
          @click="sendMessage"
          :disabled="!isConnected || sending || !inputMessage.trim()"
          class="send-button"
        >
          <span v-if="sending" class="sending-spinner"></span>
          <span v-else>发送</span>
        </button>
      </div>
      <div v-if="sendStatus" class="send-status" :class="sendStatus.type">
        {{ sendStatus.message }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useDiscussionStore } from '../../stores/discussion'

const title = ref('View E - 讨论交互区')
const discussionStore = useDiscussionStore()

const messages = ref([])
const inputMessage = ref('')
const sending = ref(false)
const isConnected = ref(false)
const sendStatus = ref(null)
const messagesContainer = ref(null)
const currentTopic = ref('')
const showStartDialog = ref(false)
const newTopic = ref('')

// Agent 名称到 CSS 类的映射
const getAgentClass = (agentName) => {
  const map = {
    '小明': 'ming',
    '小红': 'hong',
    '小李': 'li',
    '小张': 'zhang'
  }
  return map[agentName] || 'default'
}

// 消息类型标签
const getTypeLabel = (type) => {
  const map = {
    'statement': '陈述',
    'question': '提问',
    'suggestion': '建议',
    'reply': '回复'
  }
  return map[type] || type
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 发送消息
const sendMessage = async () => {
  if (!inputMessage.value.trim() || sending.value || !isConnected.value) return

  const messageText = inputMessage.value.trim()
  inputMessage.value = ''
  sending.value = true
  sendStatus.value = null

  try {
    // 添加用户消息到本地显示
    const userMessage = {
      agent: '用户',
      content: messageText,
      timestamp: Date.now(),
      type: 'statement'
    }
    messages.value.push(userMessage)
    scrollToBottom()

    // 发送到后端
    await discussionStore.sendUserMessage(messageText, currentTopic.value, messages.value)

    // 更新消息列表
    messages.value = discussionStore.conversationHistory

    sendStatus.value = { type: 'success', message: '消息发送成功' }
    setTimeout(() => {
      sendStatus.value = null
    }, 2000)

    scrollToBottom()
  } catch (error) {
    console.error('发送消息失败:', error)
    sendStatus.value = { type: 'error', message: '发送失败，请重试' }
    setTimeout(() => {
      sendStatus.value = null
    }, 3000)
  } finally {
    sending.value = false
  }
}

// 开始讨论
const startDiscussion = async (topic) => {
  if (!topic) return

  currentTopic.value = topic
  isConnected.value = true
  messages.value = []
  sending.value = true
  sendStatus.value = { type: 'info', message: '正在开始讨论，请稍候...（这可能需要几分钟）' }

  try {
    // 使用较少的轮次以减少等待时间（默认5轮）
    await discussionStore.startDiscussion(topic, 5)
    messages.value = discussionStore.conversationHistory
    scrollToBottom()
    sendStatus.value = { type: 'success', message: '讨论已开始' }
    setTimeout(() => {
      sendStatus.value = null
    }, 2000)
  } catch (error) {
    console.error('开始讨论失败:', error)
    isConnected.value = false
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      sendStatus.value = { type: 'error', message: '请求超时，讨论可能需要更长时间。请减少讨论轮次或稍后重试。' }
    } else {
      sendStatus.value = { type: 'error', message: '开始讨论失败，请检查后端连接' }
    }
    setTimeout(() => {
      sendStatus.value = null
    }, 5000)
  } finally {
    sending.value = false
  }
}

// 处理开始讨论
const handleStartDiscussion = async () => {
  if (!newTopic.value.trim()) return
  
  const topic = newTopic.value.trim()
  newTopic.value = ''
  showStartDialog.value = false
  
  await startDiscussion(topic)
}

// 监听 store 中的消息变化
watch(() => discussionStore.conversationHistory, (newMessages) => {
  messages.value = newMessages
  scrollToBottom()
}, { deep: true })

onMounted(() => {
  // 检查连接状态
  discussionStore.checkConnection().then(connected => {
    isConnected.value = connected
  })
})

onUnmounted(() => {
  // 清理
})
</script>

<style scoped>
.view-container {
  background: linear-gradient(135deg, #1a1f3a 0%, #16213e 100%);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 15px;
  display: flex;
  flex-direction: column;
  height: 100%;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

.view-e {
  flex: 1;
  min-height: 0;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.view-title {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #999;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #666;
  transition: background 0.3s;
}

.connection-status.connected .status-dot {
  background: #4ade80;
  box-shadow: 0 0 8px rgba(74, 222, 128, 0.5);
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 15px;
  padding: 10px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  min-height: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

.empty-text {
  font-size: 14px;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-item {
  padding: 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-left: 4px solid #60a5fa;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-item.user-message {
  border-left-color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
}

.message-item.agent-ming {
  border-left-color: #4ade80;
}

.message-item.agent-hong {
  border-left-color: #f87171;
}

.message-item.agent-li {
  border-left-color: #60a5fa;
}

.message-item.agent-zhang {
  border-left-color: #a78bfa;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.agent-name {
  font-weight: 600;
  color: #fff;
  font-size: 14px;
}

.message-time {
  font-size: 11px;
  color: #999;
}

.message-type {
  font-size: 11px;
  padding: 2px 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  color: #ccc;
}

.message-content {
  color: #e0e0e0;
  line-height: 1.6;
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
}

.input-container {
  margin-top: auto;
}

.input-wrapper {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
}

.message-input {
  flex: 1;
  padding: 10px 15px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  color: #fff;
  font-size: 14px;
  outline: none;
  transition: all 0.3s;
}

.message-input:focus {
  background: rgba(255, 255, 255, 0.15);
  border-color: #4ade80;
}

.message-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.message-input::placeholder {
  color: #666;
}

.send-button {
  padding: 10px 20px;
  background: linear-gradient(135deg, #4ade80, #22c55e);
  border: none;
  border-radius: 6px;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  min-width: 80px;
}

.send-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(74, 222, 128, 0.4);
}

.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sending-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.send-status {
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 4px;
  text-align: center;
}

.send-status.success {
  background: rgba(74, 222, 128, 0.2);
  color: #4ade80;
}

.send-status.error {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
}

.send-status.info {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.start-button {
  padding: 6px 12px;
  background: linear-gradient(135deg, #4ade80, #22c55e);
  border: none;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.start-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(74, 222, 128, 0.4);
}

.topic-display {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.topic-label {
  color: #999;
}

.topic-text {
  color: #4ade80;
  font-weight: 500;
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog-content {
  background: linear-gradient(135deg, #1a1f3a 0%, #16213e 100%);
  border-radius: 8px;
  padding: 24px;
  min-width: 400px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
}

.dialog-content h4 {
  margin-bottom: 16px;
  color: #fff;
  font-size: 18px;
}

.topic-input {
  width: 100%;
  padding: 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  color: #fff;
  font-size: 14px;
  margin-bottom: 16px;
  outline: none;
}

.topic-input:focus {
  background: rgba(255, 255, 255, 0.15);
  border-color: #4ade80;
}

.topic-input::placeholder {
  color: #666;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.cancel-button,
.confirm-button {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.cancel-button {
  background: rgba(255, 255, 255, 0.1);
  color: #ccc;
}

.cancel-button:hover {
  background: rgba(255, 255, 255, 0.15);
}

.confirm-button {
  background: linear-gradient(135deg, #4ade80, #22c55e);
  color: #fff;
}

.confirm-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(74, 222, 128, 0.4);
}

.confirm-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

