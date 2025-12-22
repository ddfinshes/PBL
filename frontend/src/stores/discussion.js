import { defineStore } from 'pinia'
import { ref } from 'vue'
import { discussionApi } from '../api/discussion'

export const useDiscussionStore = defineStore('discussion', () => {
  const conversationHistory = ref([])
  const currentTopic = ref('')
  const isConnected = ref(false)
  const agents = ref([])

  // 检查连接状态
  const checkConnection = async () => {
    try {
      const response = await discussionApi.healthCheck()
      isConnected.value = response.status === 'ok'
      return isConnected.value
    } catch (error) {
      isConnected.value = false
      return false
    }
  }

  // 获取所有 agents
  const fetchAgents = async () => {
    try {
      const response = await discussionApi.getAgents()
      agents.value = response.agents || []
      return agents.value
    } catch (error) {
      console.error('获取 agents 失败:', error)
      return []
    }
  }

  // 开始讨论
  const startDiscussion = async (topic, maxTurns = 10) => {
    try {
      currentTopic.value = topic
      const response = await discussionApi.startDiscussion(topic, maxTurns)
      
      if (response.success) {
        conversationHistory.value = response.messages || []
        isConnected.value = true
        return conversationHistory.value
      } else {
        throw new Error(response.message || '开始讨论失败')
      }
    } catch (error) {
      console.error('开始讨论失败:', error)
      isConnected.value = false
      throw error
    }
  }

  // 发送用户消息
  const sendUserMessage = async (message, topic, currentHistory) => {
    try {
      const response = await discussionApi.sendUserMessage(message, topic, currentHistory)
      
      if (response.success) {
        conversationHistory.value = response.conversation_history || []
        return conversationHistory.value
      } else {
        throw new Error(response.message || '发送消息失败')
      }
    } catch (error) {
      console.error('发送消息失败:', error)
      throw error
    }
  }

  // 获取 agent 回复
  const getAgentResponse = async (agentName, topic, currentHistory) => {
    try {
      const response = await discussionApi.getAgentResponse(agentName, topic, currentHistory)
      
      if (response.success) {
        const newMessage = response.response
        conversationHistory.value = [...currentHistory, newMessage]
        return newMessage
      } else {
        throw new Error(response.message || '获取回复失败')
      }
    } catch (error) {
      console.error('获取 agent 回复失败:', error)
      throw error
    }
  }

  // 重置讨论
  const resetDiscussion = async () => {
    try {
      await discussionApi.resetDiscussion()
      conversationHistory.value = []
      currentTopic.value = ''
      return true
    } catch (error) {
      console.error('重置讨论失败:', error)
      throw error
    }
  }

  return {
    conversationHistory,
    currentTopic,
    isConnected,
    agents,
    checkConnection,
    fetchAgents,
    startDiscussion,
    sendUserMessage,
    getAgentResponse,
    resetDiscussion
  }
})

